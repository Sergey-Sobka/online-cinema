from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import movies as movies_crud
from app.db.session import get_db_session
from app.models import Movie
from app.schemas.movie import MovieCreate, MovieUpdate


class MovieService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_movies_catalog(
        self,
        page: int = 1,
        limit: int = 20,
        year: int | None = None,
        min_rating: float | None = None,
        genre_id: int | None = None,
        search: str | None = None,
        sort_by: str = "popularity",
        favorite_user_id: int | None = None,
    ) -> tuple[int, list[Movie]]:
        return await movies_crud.get_movies_catalog(
            self.db,
            page=page,
            limit=limit,
            year=year,
            min_rating=min_rating,
            genre_id=genre_id,
            search=search,
            sort_by=sort_by,
            favorite_user_id=favorite_user_id,
        )

    async def get_genres_list(self) -> list[dict[str, Any]]:
        return await movies_crud.get_genres_with_counts(self.db)

    async def get_movie_detail(self, movie_id: int) -> Movie:
        movie = await movies_crud.get_movie_by_id(self.db, movie_id)
        if not movie:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
            )
        return movie

    async def create_new_movie(self, payload: MovieCreate) -> Movie:
        return await movies_crud.create_movie(self.db, payload)

    async def update_existing_movie(self, movie_id: int, payload: MovieUpdate) -> Movie:
        updated_movie = await movies_crud.update_movie(self.db, movie_id, payload)
        if not updated_movie:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
            )
        return updated_movie

    async def delete_existing_movie(self, movie_id: int) -> None:
        is_purchased = await movies_crud.is_movie_purchased(self.db, movie_id)
        if is_purchased:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prevent deletion: "
                "This movie has been purchased by at least one user.",
            )

        deleted = await movies_crud.delete_movie(self.db, movie_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
            )


def get_movie_service(db: AsyncSession = Depends(get_db_session)) -> MovieService:
    return MovieService(db)
