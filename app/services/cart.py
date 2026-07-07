from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.models import CartItem, Order, OrderItem, OrderStatus


async def is_movie_purchased(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    stmt = (
        select(exists())
        .where(Order.user_id == user_id)
        .where(Order.status == OrderStatus.PAID)
        .where(OrderItem.order_id == Order.id)
        .where(OrderItem.movie_id == movie_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def add_movie_to_cart(db: AsyncSession, user_id: int, movie_id: int) -> CartItem:
    cart = await crud.cart.get_cart_by_user_id(db, user_id=user_id)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart is not found"
        )

    for item in cart.cart_items:
        if item.movie_id == movie_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Movie is already in your cart.",
            )

    is_purchased = await is_movie_purchased(db, user_id=user_id, movie_id=movie_id)

    if is_purchased:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already purchased this movie.",
        )

    return await crud.cart.add_item_to_cart(db, cart_id=cart.id, movie_id=movie_id)
