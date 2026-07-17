from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    Cart,
    CartItem,
    Certification,
    Movie,
    Order,
    OrderStatus,
    User,
)
from app.services.orders import OrderService


@pytest.mark.asyncio
async def test_place_order_success(db_session, uow, create_user):
    user = await create_user()
    certification = Certification(name="PG-13")
    db_session.add(certification)
    await db_session.flush()

    movie_1 = Movie(
        name="Test Movie1",
        year=2023,
        time=120,
        imdb=8.0,
        votes=1000,
        description="desc",
        price=Decimal("10.50"),
        certification_id=certification.id,
    )
    movie_2 = Movie(
        name="Test Movie2",
        year=2023,
        time=120,
        imdb=8.0,
        votes=1000,
        description="desc",
        price=Decimal("10.50"),
        certification_id=certification.id,
    )
    db_session.add_all([movie_1, movie_2])
    await db_session.flush()

    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.flush()

    cart_item_1 = CartItem(cart_id=cart.id, movie_id=movie_1.id)
    cart_item_2 = CartItem(cart_id=cart.id, movie_id=movie_2.id)
    db_session.add_all([cart_item_1, cart_item_2])
    await db_session.commit()

    service = OrderService(uow)

    order = await service.place_order(user, cart.id)

    user_cart = await db_session.scalar(
        select(Cart).options(selectinload(Cart.cart_items)).where(Cart.id == cart.id)
    )
    assert order is not None
    assert order.user_id == user.id
    assert order.status == OrderStatus.PENDING
    assert len(order.order_items) == 2
    assert order.order_items[0].price_at_order == Decimal("10.50")
    assert order.total_amount == Decimal("21.00")
    assert user_cart.cart_items == []


@pytest.mark.asyncio
async def test_place_order_cart_not_found(create_user, uow):
    user = await create_user()
    service = OrderService(uow)

    with pytest.raises(HTTPException) as exc:
        await service.place_order(user, 999)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_order_history(db_session, uow, create_user, create_order):
    user = await create_user()
    await create_order(user=user)

    stmt = select(User).options(joinedload(User.group)).where(User.id == user.id)
    full_user = (await db_session.execute(stmt)).scalar_one()

    service = OrderService(uow)
    orders = await service.get_history(full_user, {})
    assert orders is not None
    assert len(orders) >= 1


@pytest.mark.asyncio
async def test_get_single_order_success(db_session, uow, create_user, create_order):
    user = await create_user()
    order = await create_order(user=user)

    stmt = select(User).options(joinedload(User.group)).where(User.id == user.id)
    full_user = (await db_session.execute(stmt)).scalar_one()

    service = OrderService(uow)
    fetched_order = await service.get_single_order(order.id, full_user)
    assert fetched_order is not None
    assert fetched_order.id == order.id


@pytest.mark.asyncio
async def test_cancel_order_success(db_session, uow, create_user, create_order):
    user = await create_user()
    order = await create_order(user=user)

    stmt = select(User).options(joinedload(User.group)).where(User.id == user.id)
    full_user = (await db_session.execute(stmt)).scalar_one()

    service = OrderService(uow)
    result = await service.cancel_order(order.id, full_user)
    assert result["status"] == "successful"

    fetched_order = await service.get_single_order(order.id, full_user)
    assert fetched_order.status == OrderStatus.CANCELED


@pytest.mark.asyncio
async def test_cancel_order_forbidden(db_session, uow, create_user, create_order):
    user1 = await create_user()
    user2 = await create_user()
    order = await create_order(user=user1)

    stmt = select(User).options(joinedload(User.group)).where(User.id == user2.id)
    full_user2 = (await db_session.execute(stmt)).scalar_one()

    service = OrderService(uow)
    with pytest.raises(HTTPException) as exc:
        await service.cancel_order(order.id, full_user2)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_place_order_empty_cart(db_session, uow, create_user):
    user = await create_user()
    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.commit()

    service = OrderService(uow)
    with pytest.raises(HTTPException) as exc:
        await service.place_order(user, cart.id)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Cart is empty"


@pytest.mark.asyncio
async def test_get_single_order_not_found(db_session, uow, create_user):
    user = await create_user()
    stmt = select(User).options(joinedload(User.group)).where(User.id == user.id)
    full_user = (await db_session.execute(stmt)).scalar_one()

    service = OrderService(uow)
    with pytest.raises(HTTPException) as exc:
        await service.get_single_order(999, full_user)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_cancel_order_invalid_state(db_session, uow, paid_payment):
    order = await db_session.get(Order, paid_payment.order_id)
    order.status = OrderStatus.PAID
    await db_session.commit()
    user = await db_session.scalar(
        select(User)
        .options(joinedload(User.group))
        .where(User.id == paid_payment.user_id)
    )
    service = OrderService(uow)
    with pytest.raises(HTTPException) as exc:
        await service.cancel_order(paid_payment.order_id, user)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_order_history_filters(db_session, uow, create_order):
    order = await create_order()
    mocked_time = datetime(2026, 7, 16, 17, 59, 18, tzinfo=UTC)
    order.created_at = mocked_time
    db_session.add(order)
    await db_session.flush()
    service = OrderService(uow)
    filters = {"start_date": mocked_time - timedelta(minutes=1)}
    user = await db_session.scalar(
        select(User).options(joinedload(User.group)).where(User.id == order.user_id)
    )
    success_orders = await service.get_history(user, filters)
    assert success_orders[0].id == order.id
    filters["start_date"] = mocked_time + timedelta(minutes=1)
    no_orders = await service.get_history(user, filters)
    assert no_orders == []
