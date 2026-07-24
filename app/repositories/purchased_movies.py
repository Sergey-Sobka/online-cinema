from typing import Any

from sqlalchemy import select

from app.models.purchased_movies import PurchasedMovie


class PurchasedMovieRepository:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def get_purchased_movies_by_user_id(self, current_user) -> list[PurchasedMovie]:
        result = await self._session.scalars(
            select(PurchasedMovie).where(PurchasedMovie.user_id == current_user.id)
        )
        return list(result.all())