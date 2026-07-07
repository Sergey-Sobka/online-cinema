import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import cart as crud_cart
from app.models import Cart

pytestmark = pytest.mark.asyncio


class TestCartCRUD:
    async def test_add_item_to_cart_success(self, db_session: AsyncSession):
        cart_id = 1
        movie_id = 42

        cart_item = await crud_cart.add_item_to_cart(
            db=db_session, cart_id=cart_id, movie_id=movie_id
        )

        assert cart_item is not None
        assert cart_item.movie_id == movie_id
        assert cart_item.id is not None

    async def test_add_duplicate_item_raises_integrity_error(
        self, db_session: AsyncSession
    ):
        cart_id = 1
        movie_id = 42

        await crud_cart.add_item_to_cart(
            db=db_session, cart_id=cart_id, movie_id=movie_id
        )

        with pytest.raises(IntegrityError):
            await crud_cart.add_item_to_cart(
                db=db_session, cart_id=cart_id, movie_id=movie_id
            )

    async def test_get_user_cart_exists(self, db_session: AsyncSession):
        user_id = 2
        movie_id = 10

        cart = Cart(user_id=user_id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        await crud_cart.add_item_to_cart(
            db=db_session, cart_id=cart.id, movie_id=movie_id
        )

        fetched_cart = await crud_cart.get_cart_by_user_id(
            db=db_session, user_id=user_id
        )

        assert fetched_cart is not None
        assert len(fetched_cart.cart_items) == 1
        assert fetched_cart.cart_items[0].movie_id == movie_id

    async def test_get_user_cart_empty(self, db_session: AsyncSession):
        non_existent_user_id = 999

        cart = await crud_cart.get_cart_by_user_id(
            db=db_session, user_id=non_existent_user_id
        )

        assert cart is None

    async def test_remove_item_from_cart_success(self, db_session: AsyncSession):
        cart_id = 4
        movie_id = 12

        item = await crud_cart.add_item_to_cart(
            db=db_session, cart_id=cart_id, movie_id=movie_id
        )

        result = await crud_cart.delete_item_from_cart(db=db_session, item_id=item.id)
        assert result is None

        cart = await crud_cart.get_cart_by_user_id(db=db_session, user_id=cart_id)
        assert cart is None or len(cart.cart_items) == 0

    async def test_remove_item_from_cart_not_found(self, db_session: AsyncSession):
        invalid_item_id = 9999

        result = await crud_cart.delete_item_from_cart(
            db=db_session, item_id=invalid_item_id
        )
        assert result is None
