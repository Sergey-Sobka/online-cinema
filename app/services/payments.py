from decimal import Decimal
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
from stripe import SignatureVerificationError

from app.models import Payment, Order, User, PaymentItems, PaymentStatus, OrderStatus, UserGroupEnum
from app.services.email import EmailService
from app.core.config import Settings


class PaymentService:
    def __init__(self, session: AsyncSession, settings: Settings, notificator: EmailService):
        self._session = session
        self._settings = settings
        self._notificator = notificator
        stripe.api_key = self._settings.stripe_secret_key

    async def create_payment_intent(self, order_id: int, user_id: int):
        order = await self._session.scalar(
            select(Order).where(Order.id == order_id).options(selectinload(Order.order_items))
        )
        if not order or order.user_id != user_id:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=400, detail="Order already paid or cancelled")

        calculated_total = sum(item.price_at_order for item in order.order_items)
        if calculated_total != order.total_amount:
            raise HTTPException(status_code=400, detail="Price changed, remake order")

        new_payment = Payment(user_id=user_id, order_id=order.id, amount=calculated_total, status=PaymentStatus.PENDING)
        self._session.add(new_payment)
        await self._session.flush()

        for item in order.order_items:
            self._session.add(
                PaymentItems(payment_id=new_payment.id, order_item_id=item.id, price_at_payment=item.price_at_order))

        intent = stripe.PaymentIntent.create(
            amount=int(calculated_total * 100), currency="usd",
            metadata={"order_id": order.id, "payment_id": new_payment.id},
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"}
        )
        new_payment.external_payment_id = intent.id
        await self._session.commit()
        return await self._session.scalar(select(Payment).options(selectinload(Payment.payment_items)).where(
            Payment.id == new_payment.id)), intent.client_secret

    async def handle_webhook(self, payload: bytes, sig_header: str, background_tasks: BackgroundTasks):
        # 1. Верифікація підпису
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self._settings.stripe_webhook_secret
            )
        except (ValueError, SignatureVerificationError) as e:
            raise HTTPException(status_code=400, detail="Invalid signature")

        event_type = event["type"]
        data_object = event["data"]["object"]
        payment_intent_id = data_object.get("id") if event_type.startswith("payment_intent") else data_object.get(
            "payment_intent")

        payment = await self._session.scalar(
            select(Payment).where(Payment.external_payment_id == payment_intent_id).with_for_update()
        )
        if not payment:
            return {"status": "ignored", "reason": "payment not found"}
        order = await self._session.scalar(select(Order).where(Order.id == payment.order_id))
        user = await self._session.scalar(select(User).where(User.id == payment.user_id))
        if event_type == "payment_intent.succeeded" and payment.status != PaymentStatus.SUCCESSFUL:
            payment.status, order.status = PaymentStatus.SUCCESSFUL, OrderStatus.PAID
            msg = "Your order is paid"
        elif event_type in ["payment_intent.payment_failed",
                            "payment_intent.canceled"] and payment.status != PaymentStatus.CANCELED:
            payment.status, order.status = PaymentStatus.CANCELED, OrderStatus.CANCELED
            msg = "Your order is canceled"
        elif event_type == "charge.refunded" and payment.status != PaymentStatus.REFUNDED:
            payment.status, order.status = PaymentStatus.REFUNDED, OrderStatus.CANCELED
            msg = "Your money is refunded"
        else:
            return {"status": "already processed"}
        await self._session.commit()
        if user:
            background_tasks.add_task(self._notificator.send_payment_status, str(user.email), msg)

        return {"status": "success"}

    async def get_history(self, current_user, filters: dict):
        query = select(Payment).options(selectinload(Payment.payment_items)).order_by(Payment.created_at.desc())
        if current_user.group.name != UserGroupEnum.ADMIN:
            query = query.where(Payment.user_id == current_user.id)
        else:
            if filters.get("user_id"): query = query.where(Payment.user_id == filters["user_id"])
            if filters.get("status"): query = query.where(Payment.status == filters["status"])

        result = await self._session.execute(query)
        return result.scalars().all()

    async def refund(self, payment_id: int, user: User):
        # if user.group.name != UserGroupEnum.ADMIN:
        #     raise HTTPException(status_code=403, detail="Forbidden")
        payment = await self._session.scalar(select(Payment).where(Payment.id == payment_id))
        if not payment or payment.status != PaymentStatus.SUCCESSFUL:
            raise HTTPException(status_code=400, detail="Invalid payment state")

        refund = stripe.Refund.create(payment_intent=payment.external_payment_id)
        return refund.id