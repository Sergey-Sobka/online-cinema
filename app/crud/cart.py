from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Cart, CartItem


async def get_cart_by_user_id(db: AsyncSession, user_id: int) -> Cart | None:
    query = (
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.cart_items).selectinload(CartItem.movie))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def add_item_to_cart(db: AsyncSession, cart_id: int, movie_id: int) -> CartItem:
    cart_item = CartItem(cart_id=cart_id, movie_id=movie_id)

    db.add(cart_item)
    await db.commit()
    await db.refresh(cart_item)
    return cart_item


async def delete_item_from_cart(db: AsyncSession, item_id: int) -> None:
    query = delete(CartItem).where(CartItem.id == item_id)
    await db.execute(query)
    await db.commit()


async def clear_cart(db: AsyncSession, cart_id: int) -> None:
    query = delete(CartItem).where(CartItem.cart_id == cart_id)
    await db.execute(query)
    await db.commit()
