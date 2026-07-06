from fastapi import HTTPException, status
from models import CartItem
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud


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

    is_purchased = False  # Placeholder

    if is_purchased:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already purchased this movie.",
        )

    return await crud.cart.add_item_to_cart(db, cart_id=cart.id, movie_id=movie_id)
