import os
from datetime import datetime
from typing import Annotated

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.core.dependencies import get_current_user, get_payment_service
from app.models import Payment, PaymentStatus, User
from app.schemas.payments import (
    PaymentCreateSchema,
    PaymentInitResponseSchema,
    PaymentReadSchema,
)
from app.services.payments import PaymentService

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentInitResponseSchema)
async def create_payment_intent(
    payload: PaymentCreateSchema,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    payment, client_secret = await service.create_payment_intent(
        payload.order_id, current_user.id
    )
    return {"payment": payment, "client_secret": client_secret}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> dict[str, str] | None:
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature") or ""
    return await service.handle_webhook(payload, sig_header, background_tasks)


@router.get("/history", response_model=list[PaymentReadSchema])
async def get_payment_history(
    service: Annotated[PaymentService, Depends(get_payment_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    status: Annotated[
        PaymentStatus | None,
        Query(description="pending, successful, canceled, or refunded"),
    ] = None,
) -> list[Payment]:
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
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str] | None:
    refund_id = await service.refund(payment_id, current_user)
    if refund_id:
        return {"status": "success", "refund_id": refund_id}
    return {"status": "error"}
