from unittest.mock import MagicMock, patch

import pytest

from app.models import PaymentStatus
from app.services.payments import PaymentService


@pytest.mark.asyncio
async def test_purchased_movies_available_for_user(uow, db_session, paid_payment):
    paid_payment.status = PaymentStatus.PENDING
    await db_session.commit()
    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": paid_payment.external_payment_id}},
        }
        service = PaymentService(uow, MagicMock(), MagicMock())
        await service.handle_webhook(b"payload", "sig", MagicMock())
    async with uow:
        purchased_movies = await uow.purchased_movies.get_purchased_movies_by_user_id(
            paid_payment.user_id
        )
        assert len(purchased_movies) == 2
