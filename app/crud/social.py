from fastapi import HTTPException, status
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.movie import Movie
from app.models.social import (
    CommentLike,
    FavoriteMovie,
    MovieComment,
    MovieLike,
    MovieRating,
)
from app.schemas.movie import CommentCreate


async def _ensure_movie_exists(db: AsyncSession, movie_id: int) -> None:
    movie_exists = await db.scalar(
        select(select(1).where(Movie.id == movie_id).exists())
    )
    if not movie_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found.",
        )


async def toggle_favorite(
    db: AsyncSession, user_id: int, movie_id: int, add: bool
) -> None:
    await _ensure_movie_exists(db, movie_id)

    if add:
        await db.merge(FavoriteMovie(user_id=user_id, movie_id=movie_id))
    else:
        await db.execute(
            delete(FavoriteMovie).where(
                and_(
                    FavoriteMovie.user_id == user_id, FavoriteMovie.movie_id == movie_id
                )
            )
        )
    await db.commit()


async def set_movie_like(
    db: AsyncSession, user_id: int, movie_id: int, is_like: bool
) -> None:
    await _ensure_movie_exists(db, movie_id)
    await db.merge(MovieLike(user_id=user_id, movie_id=movie_id, is_like=is_like))
    await db.commit()


async def set_movie_rating(
    db: AsyncSession, user_id: int, movie_id: int, score: int
) -> None:
    await _ensure_movie_exists(db, movie_id)
    await db.merge(MovieRating(user_id=user_id, movie_id=movie_id, rating=score))
    await db.commit()


async def add_movie_comment(
    db: AsyncSession, user_id: int, movie_id: int, payload: CommentCreate
) -> MovieComment:
    await _ensure_movie_exists(db, movie_id)

    if payload.parent_id is not None:
        parent = await db.get(MovieComment, payload.parent_id)
        if parent is None or parent.movie_id != movie_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found",
            )

    comment = MovieComment(
        user_id=user_id,
        movie_id=movie_id,
        text=payload.text,
        parent_id=payload.parent_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def get_comment_by_id(db: AsyncSession, comment_id: int) -> MovieComment | None:
    result = await db.execute(
        select(MovieComment)
        .options(selectinload(MovieComment.user))
        .where(MovieComment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def set_comment_like(
    db: AsyncSession, user_id: int, comment_id: int, is_like: bool
) -> None:
    await db.merge(CommentLike(user_id=user_id, comment_id=comment_id, is_like=is_like))
    await db.commit()
