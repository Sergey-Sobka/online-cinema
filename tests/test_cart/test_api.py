import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.cart import router
from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import Cart, CartItem, User

pytestmark = pytest.mark.asyncio


@pytest.fixture
def app_with_route(db_session: AsyncSession):
    test_app = FastAPI()
    test_app.include_router(router)

    test_user = User(id=100, email="test@example.com")

    test_app.dependency_overrides[get_db_session] = lambda: db_session
    test_app.dependency_overrides[get_current_user] = lambda: test_user

    return test_app


class TestCartAPI:

    async def test_view_cart_success(
            self,
            app_with_route: FastAPI,
            db_session: AsyncSession
    ):
        cart = Cart(user_id=100)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        transport = ASGITransport(app=app_with_route)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/cart/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == cart.id

    async def test_view_cart_not_found(self, app_with_route: FastAPI):
        transport = ASGITransport(app=app_with_route)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/cart/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Cart is not found"

    async def test_remove_item_from_cart_success(
            self,
            app_with_route: FastAPI,
            db_session: AsyncSession
    ):
        cart = Cart(user_id=100)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        cart_item = CartItem(cart_id=cart.id, movie_id=50)
        db_session.add(cart_item)
        await db_session.commit()
        await db_session.refresh(cart_item)

        transport = ASGITransport(app=app_with_route)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.delete(f"/cart/items/{cart_item.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_remove_item_from_cart_not_in_cart(
            self,
            app_with_route: FastAPI,
            db_session: AsyncSession
    ):
        cart = Cart(user_id=100)
        db_session.add(cart)
        await db_session.commit()

        transport = ASGITransport(app=app_with_route)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.delete("/cart/items/9999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Movie is not in the cart"

    async def test_clear_cart_success(
            self,
            app_with_route: FastAPI,
            db_session: AsyncSession
    ):
        cart = Cart(user_id=100)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        cart_item = CartItem(cart_id=cart.id, movie_id=12)
        db_session.add(cart_item)
        await db_session.commit()

        transport = ASGITransport(app=app_with_route)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.delete("/cart/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
