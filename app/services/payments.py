from datetime import UTC, datetime, timedelta
from typing import Any

import stripe
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import delete
from stripe import APIConnectionError, SignatureVerificationError, StripeError

from app.core.config import Settings
from app.core.uow_abstraction import IUnitOfWork
from app.db.session import AsyncSessionLocal
from app.models import (
    OrderStatus,
    Payment,
    PaymentItems,
    PaymentStatus,
    User,
    UserGroupEnum,
)
from app.services.email import EmailService


class PaymentService:
    def __init__(
        self, uow: IUnitOfWork, settings: Settings, notificator: EmailService
    ) -> None:
        self.uow = uow
        self._settings = settings
        self._notificator = notificator
        stripe.api_key = self._settings.stripe_secret_key

    async def create_payment_intent(self, order_id: int, user_id: int) -> Any:
        async with self.uow:
            order = await self.uow.orders.get_order_by_id(order_id)
            if not order or order.user_id != user_id:
                raise HTTPException(status_code=404, detail="Order not found")
            if order.status != OrderStatus.PENDING:
                raise HTTPException(
                    status_code=400, detail="Order already paid or cancelled"
                )

            calculated_total = sum(item.price_at_order for item in order.order_items)
            if calculated_total != order.total_amount:
                raise HTTPException(
                    status_code=400, detail="Price changed, remake order"
                )

            payments_with_order_id = await self.uow.payments.get_payments_by_order_id(
                order.id
            )
            if payments_with_order_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Payments {payments_with_order_id} "
                    "with this order already exists or paid",
                )
            new_payment = await self.uow.payments.create_payment(
                user_id, order.id, calculated_total
            )
            for item in order.order_items:
                new_payment.payment_items.append(
                    PaymentItems(
                        order_item_id=item.id,
                        price_at_payment=item.price_at_order,
                    )
                )

            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(calculated_total * 100),
                    currency="usd",
                    metadata={
                        "order_id": str(order.id),
                        "payment_id": str(new_payment.id),
                    },
                    automatic_payment_methods={
                        "enabled": True,
                        "allow_redirects": "never",
                    },
                )
            except (APIConnectionError, StripeError) as err:
                raise HTTPException(
                    status_code=503,
                    detail="Payment gateway is currently unavailable. "
                    "Please try again later.",
                ) from err
            except Exception as err:
                raise HTTPException(
                    status_code=500, detail="Internal server error"
                ) from err
            new_payment.external_payment_id = intent.id
            return await self.uow.payments.get_payment_by_id(
                new_payment.id
            ), intent.client_secret

    async def handle_webhook(
        self, payload: bytes, sig_header: str, background_tasks: BackgroundTasks
    ) -> dict[str, Any]:
        async with self.uow:
            try:
                event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
                    payload, sig_header, self._settings.stripe_webhook_secret
                )
            except (ValueError, SignatureVerificationError) as err:
                raise HTTPException(
                    status_code=400, detail="Invalid signature"
                ) from err

            event_type = event["type"]
            data_object = event["data"]["object"]
            payment_intent_id = (
                data_object.get("id")
                if event_type.startswith("payment_intent")
                else data_object.get("payment_intent")
            )

            payment = await self.uow.payments.get_payment_by_external_id(
                payment_intent_id
            )
            if not payment:
                return {"status": "ignored", "reason": "payment not found"}

            order = await self.uow.orders.get_order_by_id(payment.order_id)
            if not order:
                return {"status": "ignored", "reason": "order not found"}
            user = await self.uow.users.get_user_by_id(payment.user_id)

            if not user:
                return {"status": "ignored", "reason": "user not found"}
            if (
                event_type == "payment_intent.succeeded"
                and payment.status != PaymentStatus.SUCCESSFUL
            ):
                payment.status, order.status = (
                    PaymentStatus.SUCCESSFUL,
                    OrderStatus.PAID,
                )
                msg = "Your order is paid"
            elif (
                event_type
                in ["payment_intent.payment_failed", "payment_intent.canceled"]
                and payment.status != PaymentStatus.CANCELED
            ):
                payment.status = PaymentStatus.CANCELED
                order.status = OrderStatus.CANCELED
                msg = "Your order is canceled"
            elif (
                event_type == "charge.refunded"
                and payment.status != PaymentStatus.REFUNDED
            ):
                payment.status = PaymentStatus.REFUNDED
                order.status = OrderStatus.CANCELED
                msg = "Your money is refunded"
            else:
                return {"status": "already processed"}
            if user:
                background_tasks.add_task(
                    self._notificator.send_payment_status, str(user.email), msg
                )
            return {"status": "success"}

    async def get_history(
        self, current_user: User, filters: dict[str, Any]
    ) -> list[Payment] | None:
        async with self.uow:
            return await self.uow.payments.get_filtered_payments(current_user, filters)  # type: ignore

    async def refund(self, payment_id: int, user: User) -> str | None:
        async with self.uow:
            if user.group.name not in (UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR):
                raise HTTPException(status_code=403, detail="Forbidden")
            payment = await self.uow.payments.get_payment_by_id(payment_id)
            if not payment or payment.status != PaymentStatus.SUCCESSFUL:
                raise HTTPException(status_code=400, detail="Invalid payment state")
            if not payment.external_payment_id:
                raise HTTPException(status_code=400, detail="Payment ID not found")
            try:
                refund = stripe.Refund.create(
                    payment_intent=payment.external_payment_id
                )
            except StripeError as err:
                raise HTTPException(
                    status_code=400, detail="Stripe not available"
                ) from err
            return refund.id


async def delete_old_pending_payments() -> int:
    cutoff_time = datetime.now(UTC) - timedelta(hours=24)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Payment)
            .where(Payment.status == PaymentStatus.PENDING)
            .where(Payment.created_at <= cutoff_time)
        )
        await session.commit()
        return int(getattr(result, "rowcount", 0))
