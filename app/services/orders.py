from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import clear_cart
from app.models import Movie, Order, OrderItem, OrderStatus, User, UserGroupEnum, Cart
from app.services.cart import is_movie_purchased






class OrderService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def movies_purchased_by_user(self, current_user, movie_ids):
        query = select(OrderItem.movie_id).join(Order).where(
            Order.user_id == current_user.id,
            Order.status == OrderStatus.PAID,
            OrderItem.movie_id.in_(movie_ids)
        )
        return (await self._session.scalars(query)).all()


    async def place_order(self, current_user: User, cart_id: int) -> Order:
        cart = await self._session.scalar(select(Cart).options(selectinload(Cart.cart_items)).where(Cart.id == cart_id))
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
        movie_ids = list(dict.fromkeys([cart_item.movie_id
                                        for cart_item in cart.cart_items]))

        purchased_movies = await self.movies_purchased_by_user(current_user, movie_ids)
        if purchased_movies:
            raise HTTPException(
                status_code=400, detail=f"Some movies are purchased: {purchased_movies}"
            )
        movies = (
            await self._session.scalars(select(Movie).where(Movie.id.in_(movie_ids)))
        ).all()
        found_ids = [movie.id for movie in movies]
        missing_ids = [movie_id for movie_id in movie_ids if movie_id not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=400, detail=f"Some movies are unavailable: {missing_ids}"
            )

        stmt = (
            select(Order)
            .where(Order.user_id == current_user.id)
            .options(selectinload(Order.order_items))
        )
        orders = (await self._session.scalars(stmt)).all()
        for order in orders:
            order_item_movie_ids = []
            for order_item in order.order_items:
                order_item_movie_ids.append(order_item.movie_id)
            if set(order_item_movie_ids) == set(movie_ids) and order.status == OrderStatus.PENDING:
                raise HTTPException(
                    status_code=400, detail=f"Order {order.id} with movie_ids {movie_ids} already exists"
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
            await clear_cart(self._session, cart_id)

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
