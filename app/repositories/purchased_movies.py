from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.purchased_movies import PurchasedMovie


class PurchasedMovieRepository:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def get_purchased_movies_by_user_id(
        self, user_id: int
    ) -> list[PurchasedMovie]:
        result = await self._session.scalars(
            select(PurchasedMovie)
            .options(selectinload(PurchasedMovie.movie))
            .where(PurchasedMovie.user_id == user_id)
        )
        purchased_movies: list[PurchasedMovie] = list(result.all())
        return purchased_movies

    async def add_purchased_movie(self, user_id: int, movie_id: int) -> None:
        purchased_movie = PurchasedMovie(user_id=user_id, movie_id=movie_id)
        self._session.add(purchased_movie)
        await self._session.flush()
