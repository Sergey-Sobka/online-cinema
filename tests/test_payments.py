from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import stripe
from fastapi import HTTPException
from sqlalchemy import select
from stripe import APIConnectionError

from app.models import Payment, PaymentStatus
from app.services.payments import PaymentService


@pytest.mark.asyncio
async def test_create_payment_intent_success(db_session, create_order):
    order = await create_order()
    with patch("stripe.PaymentIntent.create") as mock_stripe:
        mock_stripe.return_value = MagicMock(
            id="pi_12345", client_secret="sk_test_secret"
        )
        service = PaymentService(db_session, MagicMock(), MagicMock())
        payment, client_secret = await service.create_payment_intent(
            order.id, order.user_id
        )
        assert payment.status == PaymentStatus.PENDING
        assert client_secret == "sk_test_secret"


@pytest.mark.asyncio
async def test_create_payment_intent_stripe_connection_error(db_session, create_order):
    order = await create_order()
    with patch("stripe.PaymentIntent.create") as mock_stripe:
        mock_stripe.side_effect = APIConnectionError("Connection lost")
        service = PaymentService(db_session, MagicMock(), MagicMock())
        with pytest.raises(HTTPException) as exc:
            await service.create_payment_intent(order.id, order.user_id)
        assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_create_payment_intent_order_not_found(db_session):
    service = PaymentService(db_session, MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        await service.create_payment_intent(999, 1)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_payment_intent_price_mismatch(db_session, create_order):
    order = await create_order()
    order.total_amount = Decimal("999.00")
    await db_session.commit()
    service = PaymentService(db_session, MagicMock(), MagicMock())
    with pytest.raises(HTTPException) as exc:
        await service.create_payment_intent(order.id, order.user_id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_handle_webhook_succeeded(db_session, paid_payment):
    paid_payment.status = PaymentStatus.PENDING
    await db_session.commit()

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": paid_payment.external_payment_id}},
        }
        service = PaymentService(db_session, MagicMock(), MagicMock())
        result = await service.handle_webhook(b"payload", "sig", MagicMock())
        assert result["status"] == "success"
        await db_session.refresh(paid_payment)
        assert paid_payment.status == PaymentStatus.SUCCESSFUL


@pytest.mark.asyncio
async def test_get_history(db_session, create_order):
    order = await create_order()
    for _ in range(5):
        db_session.add(
            Payment(
                user_id=order.user_id,
                order_id=order.id,
                amount=Decimal(100),
                status=PaymentStatus.PENDING,
            )
        )
    await db_session.commit()
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 5


@pytest.mark.asyncio
async def test_refund_success(db_session, admin_user, paid_payment):
    with patch("stripe.Refund.create") as mock_refund:
        mock_refund.return_value = MagicMock(id="re_987")
        service = PaymentService(db_session, MagicMock(), MagicMock())
        refund_id = await service.refund(paid_payment.id, admin_user)
        assert refund_id == "re_987"


@pytest.mark.asyncio
async def test_refund_stripe_error(db_session, admin_user, paid_payment):
    with patch("stripe.Refund.create") as mock_refund:
        mock_refund.side_effect = stripe.error.StripeError("Stripe is down")
        service = PaymentService(db_session, MagicMock(), MagicMock())
        with pytest.raises(HTTPException):
            await service.refund(paid_payment.id, admin_user)
