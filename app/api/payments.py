import os
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import stripe
from stripe import SignatureVerificationError, StripeError
from app.db.session import get_db_session
from app.schemas.payments import (
    PaymentCreateSchema,
    PaymentInitResponseSchema,
    PaymentReadSchema,
)
from app.core.dependecies import get_email_service
from app.models import User, Order, Payment, PaymentItems, PaymentStatus, UserGroup, UserGroupEnum, OrderStatus
from typing import Optional

from app.services.email import EmailService

router = APIRouter(prefix="/payments", tags=["Payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


async def get_mock_current_user(db: AsyncSession = Depends(get_db_session)) -> User:
    user = await db.scalar(
        select(User)
        .options(selectinload(User.group))
        .limit(1)
    )

    if not user:
        group = await db.scalar(
            select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
        )

        if not group:
            group = UserGroup(name=UserGroupEnum.USER)
            db.add(group)
            await db.flush()

        user = User(
            email="admin@example.com",
            hashed_password="Test@123456789",
            is_active=True,
            group_id=int(group.id)
        )
        db.add(user)
        await db.commit()

        user = await db.scalar(
            select(User)
            .options(selectinload(User.group))
            .where(User.id == user.id)
        )
        print(f"[MOCK AUTH] Created new user with ID: {user.id} and Group: {user.group.name}")
    return user


@router.post("/", response_model=PaymentInitResponseSchema)
async def create_payment_intent(
        payload: PaymentCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_mock_current_user)
):
    order = await db.scalar(
        select(Order)
        .where(Order.id == payload.order_id)
        .options(selectinload(Order.order_items))
    )

    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order already paid or cancelled")

    calculated_total = Decimal("0.00")
    for item in order.order_items:
        calculated_total += item.price_at_order

    if calculated_total != order.total_amount:
        raise HTTPException(
            status_code=400,
            detail="Price is changed, please remake order"
        )

    try:

        new_payment = Payment(
            user_id=current_user.id,
            order_id=order.id,
            amount=calculated_total,
            status=PaymentStatus.PENDING
        )
        db.add(new_payment)
        await db.flush()

        for item in order.order_items:
            new_payment_item = PaymentItems(
                payment_id=new_payment.id,
                order_item_id=item.id,
                price_at_payment=item.price_at_order
            )
            db.add(new_payment_item)

        intent = stripe.PaymentIntent.create(
            amount=int(calculated_total * 100),
            currency="usd",
            metadata={
                "order_id": order.id,
                "payment_id": new_payment.id
            },
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "never"
            }
        )
        new_payment.external_payment_id = intent.id

        await db.commit()
        result = await db.execute(
            select(Payment)
            .options(selectinload(Payment.payment_items))
            .where(Payment.id == new_payment.id)
        )
        payment_with_items = result.scalar_one()

        return {
            "payment": payment_with_items,
            "client_secret": intent.client_secret
        }


    except StripeError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db_session),
        notificator: EmailService = Depends(get_email_service)
):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )

    except SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]
    payment_intent_id = data_object.get("id") if event_type.startswith("payment_intent") else data_object.get(
        "payment_intent")

    event_id = event.get("id")
    print(f"[DEBUG] Отримано event ID: {event_id}, type: {event_type}")

    try:
        payment = await db.scalar(select(Payment).where(Payment.external_payment_id == payment_intent_id).with_for_update())

        if not payment:
            return {"status": "ignored", "reason": "payment not found"}

        order = await db.scalar(select(Order).where(Order.id == payment.order_id))
        if not order:
            return {"status": "ignored", "reason": "order not found"}
        user = await db.scalar(select(User).where(User.id == payment.user_id))
        if not user:
            return {"status": "ignored", "reason": "user not found"}

        if event_type == "payment_intent.succeeded":
            if payment.status == PaymentStatus.SUCCESSFUL:
                return {"status": "already processed"}
            payment.status = PaymentStatus.SUCCESSFUL
            order.status = OrderStatus.PAID
            await db.commit()
            background_tasks.add_task(
                notificator.send_payment_status,
                str(user.email),
                "Your order is paid"
            )

        elif event_type in ["payment_intent.payment_failed", "payment_intent.canceled"]:
            if payment.status == PaymentStatus.CANCELED:
                return {"status": "already processed"}
            payment.status = PaymentStatus.CANCELED
            order.status = OrderStatus.CANCELED
            await db.commit()

            background_tasks.add_task(
                notificator.send_payment_status,
                str(user.email),
                "Your order is canceled"
            )
            print(f"[WEBHOOK] Payment {payment_intent_id} canceled/failed.")

        elif event_type == "charge.refunded":
            if payment.status == PaymentStatus.REFUNDED:
                return {"status": "already processed"}
            payment.status = PaymentStatus.REFUNDED
            order.status = OrderStatus.CANCELED
            await db.commit()

            background_tasks.add_task(
                notificator.send_payment_status,
                str(user.email),
                "Your money is refunded"
            )
            print(f"[WEBHOOK] Payment {payment_intent_id} refunded.")


        return {"status": "success"}


    except Exception as e:
        await db.rollback()
        print(f"[WEBHOOK ERROR] Error processing event {event_type}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history", response_model=list[PaymentReadSchema])
async def get_payment_history(
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = Query(None, description="successful, canceled, or refunded"),
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_mock_current_user)
):
    query = (
        select(Payment)
        .options(selectinload(Payment.payment_items))
        .order_by(Payment.created_at.desc())
    )

    if current_user.group.name != UserGroupEnum.ADMIN:
        query = query.where(Payment.user_id == current_user.id)
    else:
        if user_id:
            query = query.where(Payment.user_id == user_id)
        if start_date:
            query = query.where(Payment.created_at >= start_date)
        if end_date:
            query = query.where(Payment.created_at <= end_date)
        if status:
            query = query.where(Payment.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{payment_id}/refund")
async def refund_payment(
        payment_id: int,
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(get_mock_current_user)
):
    if current_user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    payment = await db.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status != PaymentStatus.SUCCESSFUL:
        raise HTTPException(status_code=400, detail="Payment not paid")

    try:
        refund = stripe.Refund.create(
            payment_intent=payment.external_payment_id,
        )
        return {"status": "success", "refund_id": refund.id}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
