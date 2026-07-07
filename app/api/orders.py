from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user, get_order_service
from app.models import Order
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderRead
from app.services.orders import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order:
    order = await service.place_order(current_user, data.movie_ids)
    return order


@router.get("/", response_model=list[OrderRead])
async def get_my_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> list[Order]:
    return await service.get_history(current_user)
