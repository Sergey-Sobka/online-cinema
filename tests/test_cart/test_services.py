import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cart, CartItem
from app.services.cart import add_movie_to_cart


class DummyMovie:
    def __init__(self, id: int):
        self.id = id


@pytest.mark.asyncio
class TestAddMovieToCartService:
    async def test_add_movie_to_cart_success(self, db_session: AsyncSession):
        user_id = 11
        movie_id = 42

        cart = Cart(user_id=user_id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        cart_item = await add_movie_to_cart(
            db=db_session, user_id=user_id, movie_id=movie_id
        )

        assert cart_item is not None
        assert cart_item.cart_id == cart.id
        assert cart_item.movie_id == movie_id

    async def test_add_movie_to_cart_not_found(self, db_session: AsyncSession):
        non_existent_user_id = 999
        movie_id = 42

        with pytest.raises(HTTPException) as exc_info:
            await add_movie_to_cart(
                db=db_session, user_id=non_existent_user_id, movie_id=movie_id
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Cart is not found"

    async def test_add_movie_to_cart_already_exists(self, db_session: AsyncSession):
        user_id = 12
        movie_id = 42

        cart = Cart(user_id=user_id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        cart_item = CartItem(cart_id=cart.id, movie_id=movie_id)
        db_session.add(cart_item)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await add_movie_to_cart(db=db_session, user_id=user_id, movie_id=movie_id)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert exc_info.value.detail == "Movie is already in your cart."
