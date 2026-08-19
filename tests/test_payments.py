import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import stripe
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from stripe import APIConnectionError

from app.core.uow import SqlAlchemyUnitOfWork
from app.models import (
    Cart,
    CartItem,
    Certification,
    Movie,
    Payment,
    PaymentStatus,
    User,
)
from app.services.orders import OrderService
from app.services.payments import PaymentService, to_stripe_cents


@pytest.mark.parametrize(
    ("amount", "expected_cents"),
    [
        (Decimal("25.00"), 2500),
        (Decimal("10.235"), 1024),
        (Decimal("10.234"), 1023),
    ],
)
def test_to_stripe_cents_rounds_half_up(amount: Decimal, expected_cents: int) -> None:
    assert to_stripe_cents(amount) == expected_cents


@pytest.mark.asyncio
async def test_create_payment_intent_success(uow, create_order):
    order = await create_order()
    with patch("stripe.PaymentIntent.create") as mock_stripe:
        mock_stripe.return_value = MagicMock(
            id="pi_12345", client_secret="sk_test_secret"
        )
        service = PaymentService(uow, MagicMock(), MagicMock())
        payment, client_secret = await service.create_payment_intent(
            order.id, order.user_id
        )
        assert payment.status == PaymentStatus.PENDING
        assert client_secret == "sk_test_secret"


@pytest.mark.asyncio
async def test_create_payment_intent_stripe_connection_error(uow, create_order):
    order = await create_order()
    with patch("stripe.PaymentIntent.create") as mock_stripe:
        mock_stripe.side_effect = APIConnectionError("Connection lost")
        service = PaymentService(uow, MagicMock(), MagicMock())
        with pytest.raises(HTTPException) as exc:
            await service.create_payment_intent(order.id, order.user_id)
        assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_create_payment_intent_order_not_found(uow):
    service = PaymentService(uow, MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        await service.create_payment_intent(999, 1)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_payment_intent_price_mismatch(uow, db_session, create_order):
    order = await create_order()
    order.total_amount = Decimal("999.00")
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    service = PaymentService(uow, MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        await service.create_payment_intent(order.id, order.user_id)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Price changed, remake order"


@pytest.mark.asyncio
async def test_handle_webhook_succeeded(uow, db_session, paid_payment):
    paid_payment_id = paid_payment.id
    paid_payment.status = PaymentStatus.PENDING
    await db_session.commit()

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": paid_payment.external_payment_id}},
        }
        service = PaymentService(uow, MagicMock(), MagicMock())
        result = await service.handle_webhook(b"payload", "sig", MagicMock())
        assert result["status"] == "success"

        payment = await uow.payments.get_payment_by_id(paid_payment_id)
        assert payment.status == PaymentStatus.SUCCESSFUL


@pytest.mark.asyncio
async def test_handle_webhook_atomicity_on_error(uow, db_session, paid_payment):
    paid_payment.status = PaymentStatus.PENDING
    await db_session.commit()

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": paid_payment.external_payment_id}},
        }

        with patch.object(uow.users, "get_user_by_id", return_value=None):
            service = PaymentService(uow, MagicMock(), MagicMock())
            result = await service.handle_webhook(b"payload", "sig", MagicMock())
            assert result["status"] == "ignored"
            assert result["reason"] == "user not found"

        payment = await uow.payments.get_payment_by_id(paid_payment.id)
        assert payment.status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_get_history(uow_factory, db_session, create_user):
    user = await create_user(group_id=2)
    stmt = select(User).options(joinedload(User.group)).where(User.id == user.id)
    user = (await db_session.execute(stmt)).scalar_one()

    for _ in range(5):
        db_session.add(
            Payment(
                user_id=user.id,
                order_id=1,
                amount=Decimal(100),
                status=PaymentStatus.PENDING,
            )
        )
    await db_session.commit()
    uow = uow_factory()

    async with uow:
        payments = await uow.payments.get_filtered_payments(user, {})
        assert len(payments) == 5


@pytest.mark.asyncio
async def test_refund_success(uow_factory, db_session, admin_user, paid_payment):
    with patch("stripe.Refund.create") as mock_refund:
        mock_refund.return_value = MagicMock(id="re_987")
        uow = uow_factory()
        service = PaymentService(uow, MagicMock(), MagicMock())
        async with uow:
            refund_id = await service.refund(paid_payment.id, admin_user)
            assert refund_id == "re_987"


@pytest.mark.asyncio
async def test_refund_stripe_error(uow_factory, db_session, admin_user, paid_payment):
    with patch("stripe.Refund.create") as mock_refund:
        mock_refund.side_effect = stripe.error.StripeError("Stripe is down")
        uow = uow_factory()
        service = PaymentService(uow, MagicMock(), MagicMock())
        with pytest.raises(HTTPException):
            async with uow:
                await service.refund(paid_payment.id, admin_user)


@pytest.mark.asyncio
async def test_timezone_aware_created_at_values(postgres_session):
    """
    This test is used postgres session because sqlite not add timezone
    even if we use Datetime(timezone=True) in models. For avoid duplicate
    code, test for orders aware timezone in this test too.
    """
    certification = Certification(name="Name")
    postgres_session.add(certification)
    await postgres_session.flush()
    movie_1 = Movie(
        name="Movie",
        uuid=uuid.uuid4(),
        year=2020,
        time=90,
        imdb=4,
        votes=100,
        meta_score=6,
        description="d",
        price=Decimal("100"),
        certification_id=certification.id,
    )
    movie_2 = Movie(
        name="Movie2",
        uuid=uuid.uuid4(),
        year=2020,
        time=90,
        imdb=4,
        votes=100,
        meta_score=6,
        description="d",
        price=Decimal("100"),
        certification_id=certification.id,
    )
    postgres_session.add_all([movie_1, movie_2])
    await postgres_session.flush()
    user = User(
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="test123456789",
        is_active=True,
        group_id=1,
    )
    postgres_session.add(user)
    await postgres_session.commit()
    await postgres_session.refresh(user)
    cart = Cart(user_id=user.id)
    postgres_session.add(cart)
    await postgres_session.flush()

    cart_item_1 = CartItem(cart_id=cart.id, movie_id=movie_1.id)
    cart_item_2 = CartItem(cart_id=cart.id, movie_id=movie_2.id)
    postgres_session.add_all([cart_item_1, cart_item_2])
    await postgres_session.flush()
    uow = SqlAlchemyUnitOfWork(lambda: postgres_session)
    service = OrderService(uow)
    order = await service.place_order(current_user=user, cart_id=cart.id)
    payment = Payment(
        user_id=order.user_id,
        order_id=order.id,
        amount=Decimal(200),
        external_payment_id=f"pi_{uuid.uuid4().hex}",
        status=PaymentStatus.SUCCESSFUL,
    )
    postgres_session.add(payment)
    await postgres_session.commit()
    await postgres_session.refresh(payment)
    assert payment.created_at.tzinfo is not None
    assert order.created_at.tzinfo is not None
