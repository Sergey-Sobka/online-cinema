from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.orders import OrderStatus


class OrderItemRead(BaseModel):
    movie_id: int
    price_at_order: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_amount: Decimal | None
    status: OrderStatus
    created_at: datetime


class OrderDetail(OrderRead):
    order_items: list[OrderItemRead]
