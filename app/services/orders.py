from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Movie, Order, OrderItem, OrderStatus, User, UserGroupEnum


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def place_order(self, current_user: User, movie_ids: list[int]) -> Order:
        movie_ids = set(movie_ids)
        movies = (
            await self._session.scalars(select(Movie).where(Movie.id.in_(movie_ids)))
        ).all()
        found_ids = [movie.id for movie in movies]
        missing_ids = [movie_id for movie_id in movie_ids if movie_id not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=400, detail=f"Some movies are unavailable: {missing_ids}"
            )
        items_data = [
            {"movie_id": movie.id, "price_at_order": movie.price} for movie in movies
        ]
        if not items_data:
            raise HTTPException(status_code=400, detail="Cart is empty")
        try:
            total = sum(Decimal(str(item["price_at_order"])) for item in items_data)
            new_order = Order(
                user_id=current_user.id,
                total_amount=Decimal(total),
                status=OrderStatus.PENDING,
            )
            self._session.add(new_order)
            await self._session.flush()
            for item in items_data:
                order_item = OrderItem(
                    order_id=new_order.id,
                    movie_id=item["movie_id"],
                    price_at_order=item["price_at_order"],
                )
                self._session.add(order_item)
        except SQLAlchemyError as err:
            await self._session.rollback()
            raise HTTPException(
                status_code=500,
                detail="We encountered an issue processing your order."
                " Please try again later.",
            ) from err
        await self._session.commit()
        await self._session.refresh(new_order, ["order_items"])
        return new_order

    async def get_history(self, current_user: User) -> list[Order]:
        query = (
            select(Order)
            .options(selectinload(Order.order_items))
            .order_by(Order.created_at.desc())
        )
        if current_user.group.name != UserGroupEnum.ADMIN:
            query = query.where(Order.user_id == current_user.id)
        result = await self._session.execute(query)
        return list(result.scalars().all())
