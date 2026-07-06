from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from app.services.orders import OrderService
from app.schemas.orders import OrderCreate, OrderRead
from app.models.user import User
from app.core.dependencies import get_current_user, get_order_service

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)]
):

    order = await service.place_order(current_user, data.movie_ids)
    return order

@router.get("/", response_model=list[OrderRead])
async def get_my_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)]
):
    return await service.get_history(current_user)