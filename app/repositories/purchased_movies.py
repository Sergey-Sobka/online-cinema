from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.purchased_movies import PurchasedMovie


class PurchasedMovieRepository:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def get_purchased_movies_by_user_id(self, user_id) -> list[PurchasedMovie]:
        result = await self._session.scalars(
            select(PurchasedMovie)
            .options(selectinload(PurchasedMovie.movie))
            .where(PurchasedMovie.user_id == user_id)
        )
        if not result:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to "
                       "view other users' purchased movies.",
            )
        return list(result.all())

    async def add_purchased_movie(self, user_id, movie_id) -> None:
        purchased_movie = PurchasedMovie(user_id=user_id, movie_id=movie_id)
        self._session.add(purchased_movie)
        await self._session.flush()
