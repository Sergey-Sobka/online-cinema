from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_order_service
from app.models import Order, OrderStatus
from app.models.user import User
from app.schemas.orders import OrderDetail, OrderRead
from app.services.orders import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=list[OrderRead])
async def get_orders_history(
    service: Annotated[OrderService, Depends(get_order_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    user_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    status: Annotated[
        OrderStatus | None, Query(description="successful, canceled, or refunded")
    ] = None,
) -> list[Order]:
    filters = {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
    }
    return await service.get_history(current_user, filters)


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order_detail(
    order_id: int,
    service: Annotated[OrderService, Depends(get_order_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Order:
    return await service.get_single_order(order_id, current_user)


@router.get("/{order_id}/cancel", status_code=200)
async def cancel_order_by_id(
    order_id: int,
    service: Annotated[OrderService, Depends(get_order_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    return await service.cancel_order(order_id, current_user)
