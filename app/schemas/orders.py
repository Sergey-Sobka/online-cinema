from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.orders import OrderStatus


class OrderCreate(BaseModel):
    movie_ids: list[int]


class OrderItemRead(BaseModel):
    movie_id: int
    price_at_order: Decimal


class OrderRead(BaseModel):
    id: int
    total_amount: Decimal | None
    status: OrderStatus
    created_at: datetime
    order_items: list[OrderItemRead]

    class Config:
        from_attributes = True
