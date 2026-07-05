from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models.payments import PaymentStatus


class PaymentCreateSchema(BaseModel):
    order_id: int


# class PaymentInitResponseSchema(BaseModel):
#
#     id: int
#     user_id: int
#     order_id: int
#     amount: Decimal
#     status: PaymentStatus
#     external_payment_id: str
#     client_secret: str


class PaymentItemReadSchema(BaseModel):
    order_item_id: int
    price_at_payment: Decimal

    class Config:
        from_attributes = True


class PaymentReadSchema(BaseModel):
    id: int
    user_id: int
    order_id: int
    amount: Decimal
    status: PaymentStatus
    external_payment_id: Optional[str] = None
    created_at: Optional[datetime] = None
    payment_items: list[PaymentItemReadSchema] = []

    model_config = ConfigDict(from_attributes=True)


class PaymentInitResponseSchema(BaseModel):
    payment: PaymentReadSchema  # Використовуємо вже існуючу схему читання
    client_secret: str
