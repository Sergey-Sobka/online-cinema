from datetime import UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Cart, Movie, Order, OrderItem, OrderStatus, User, UserGroupEnum


class OrderRepository:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def movies_purchased_by_user(
        self, current_user: User, movie_ids: list[int]
    ) -> list[int]:
        query = (
            select(OrderItem.movie_id)
            .join(Order)
            .where(
                Order.user_id == current_user.id,
                Order.status == OrderStatus.PAID,
                OrderItem.movie_id.in_(movie_ids),
            )
        )
        return list((await self._session.scalars(query)).all())

    async def get_cart_by_id(self, cart_id: int) -> Cart | None:
        stmt = (
            select(Cart)
            .options(selectinload(Cart.cart_items))
            .where(Cart.id == cart_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()  # type: ignore

    async def get_user_orders(self, current_user: User) -> list[Order] | None:
        stmt = (
            select(Order)
            .where(Order.user_id == current_user.id)
            .options(selectinload(Order.order_items))
        )
        return (await self._session.scalars(stmt)).all()  # type: ignore

    async def get_movies_from_ids(self, movie_ids: list[int]) -> list[Movie]:
        stmt = select(Movie).where(Movie.id.in_(movie_ids))
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def create_order(self, current_user: User, total: float) -> Order:
        order = Order(
            user_id=current_user.id,
            total_amount=Decimal(total),
            status=OrderStatus.PENDING,
        )
        self._session.add(order)
        return order

    async def get_filtered_orders(
        self, current_user: User, filters: dict[str, Any]
    ) -> list[Order]:
        query = (
            select(Order)
            .options(selectinload(Order.order_items))
            .order_by(Order.created_at.desc())
        )
        if current_user.group.name not in (
            UserGroupEnum.ADMIN,
            UserGroupEnum.MODERATOR,
        ):
            query = query.where(Order.user_id == current_user.id)
        else:
            if filters.get("user_id"):
                query = query.where(Order.user_id == filters["user_id"])
            if filters.get("status"):
                query = query.where(Order.status == filters["status"])

        if filters.get("start_date"):
            start_date = filters["start_date"]
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=UTC)
            else:
                start_date = start_date.astimezone(UTC)
            query = query.where(Order.created_at >= start_date)
        if filters.get("end_date"):
            end_date = filters["end_date"]
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=UTC)
            else:
                end_date = end_date.astimezone(UTC)
            query = query.where(Order.created_at <= end_date)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_order_by_id(self, order_id: int) -> Order | None:
        stmt = (
            select(Order)
            .options(selectinload(Order.order_items))
            .where(Order.id == order_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()  # type: ignore

    async def change_order_status(self, order_id: int, status: OrderStatus) -> None:
        order = await self.get_order_by_id(order_id)
        if order is not None:
            order.status = status
