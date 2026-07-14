from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import stripe
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from stripe import APIConnectionError

from app.models import Payment, PaymentStatus, User
from app.services.payments import PaymentService


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
