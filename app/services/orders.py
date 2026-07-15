from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from app.core.uow_abstraction import IUnitOfWork
from app.crud import clear_cart
from app.models import Order, OrderItem, OrderStatus, User, UserGroupEnum


class OrderService:
    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def place_order(self, current_user: User, cart_id: int) -> Order:
        async with self.uow:
            cart = await self.uow.orders.get_cart_by_id(cart_id)
            if not cart:
                raise HTTPException(status_code=404, detail="Cart not found")
            movie_ids = list(
                dict.fromkeys([cart_item.movie_id for cart_item in cart.cart_items])
            )

            purchased_movies = await self.uow.orders.movies_purchased_by_user(
                current_user, movie_ids
            )
            if purchased_movies:
                raise HTTPException(
                    status_code=400,
                    detail=f"Some movies are purchased: {purchased_movies}",
                )
            movies = await self.uow.orders.get_movies_from_ids(movie_ids)
            found_ids = [movie.id for movie in movies]
            missing_ids = [
                movie_id for movie_id in movie_ids if movie_id not in found_ids
            ]
            if missing_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Some movies are unavailable: {missing_ids}",
                )
            orders = await self.uow.orders.get_user_orders(current_user)
            for order in orders:
                order_item_movie_ids = []
                for order_item in order.order_items:
                    order_item_movie_ids.append(order_item.movie_id)
                if (
                    set(order_item_movie_ids) == set(movie_ids)
                    and order.status == OrderStatus.PENDING
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Order {order.id} with movie_ids "
                        f"{movie_ids} already exists",
                    )
            items_data = [
                {"movie_id": movie.id, "price_at_order": movie.price}
                for movie in movies
            ]
            if not items_data:
                raise HTTPException(status_code=400, detail="Cart is empty")

            total = sum(Decimal(str(item["price_at_order"])) for item in items_data)
            new_order = await self.uow.orders.create_order(current_user, Decimal(total))
            for item in items_data:
                order_item = OrderItem(
                    movie_id=item["movie_id"], price_at_order=item["price_at_order"]
                )
                new_order.order_items.append(order_item)
            await clear_cart(self.uow.session, cart_id)
            return new_order  # type: ignore

    async def get_history(
        self, current_user: User, filters: dict[str, Any]
    ) -> list[Order] | None:
        return await self.uow.orders.get_filtered_orders(current_user, filters)  # type: ignore

    async def get_single_order(self, order_id: int, current_user: User) -> Order | None:
        order: Order | None = await self.uow.orders.get_order_by_id(order_id)

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if (
            current_user.group.name != UserGroupEnum.ADMIN
            and order.user_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="You cannot view this order")

        return order

    async def cancel_order(self, order_id: int, current_user: User) -> dict[str, str]:
        async with self.uow:
            order = await self.uow.orders.get_order_by_id(order_id)
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            if order.status != OrderStatus.PENDING:
                raise HTTPException(
                    status_code=400, detail="Order already canceled or paid"
                )
            if (
                current_user.group.name != UserGroupEnum.ADMIN
                and order.user_id != current_user.id
            ):
                raise HTTPException(
                    status_code=403, detail="You cannot cancel this order"
                )
            await self.uow.orders.change_order_status(order_id, OrderStatus.CANCELED)
            return {"status": "successful", "detail": f"Order {order.id} canceled"}
