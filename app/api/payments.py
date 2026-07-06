import os
from datetime import datetime
from typing import Annotated

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.dependecies import get_payment_service
from app.db.session import get_db_session
from app.models import User, UserGroup, UserGroupEnum
from app.schemas.payments import (
    PaymentCreateSchema,
    PaymentInitResponseSchema,
    PaymentReadSchema,
)
from app.services.payments import PaymentService

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
router = APIRouter(prefix="/payments", tags=["Payments"])


async def get_mock_current_user(db: AsyncSession = Depends(get_db_session)) -> User:
    user = await db.scalar(select(User).options(selectinload(User.group)).limit(1))

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
            group_id=int(group.id),
        )
        db.add(user)
        await db.commit()

        user = await db.scalar(
            select(User).options(selectinload(User.group)).where(User.id == user.id)
        )
    return user


@router.post("/", response_model=PaymentInitResponseSchema)
async def create_payment_intent(
    payload: PaymentCreateSchema,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    current_user: User = Depends(get_mock_current_user),
):
    payment, client_secret = await service.create_payment_intent(
        payload.order_id, current_user.id
    )
    return {"payment": payment, "client_secret": client_secret}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    service: Annotated[PaymentService, Depends(get_payment_service)],
):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    return await service.handle_webhook(payload, sig_header, background_tasks)


@router.get("/history", response_model=list[PaymentReadSchema])
async def get_payment_history(
    service: Annotated[PaymentService, Depends(get_payment_service)],
    current_user: User = Depends(get_mock_current_user),
    user_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    status: str | None = Query(
        None, description="successful, canceled, or refunded"
    ),
):
    filters = {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
    }
    return await service.get_history(current_user, filters)


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    current_user: User = Depends(get_mock_current_user),
):
    refund_id = await service.refund(payment_id, current_user)
    return {"status": "success", "refund_id": refund_id}
