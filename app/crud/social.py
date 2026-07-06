from sqlalchemy import and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import FavoriteMovie, MovieComment, MovieLike, MovieRating
from app.schemas.movie import CommentCreate


async def toggle_favorite(
    db: AsyncSession, user_id: int, movie_id: int, add: bool
) -> None:
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
    await db.merge(MovieLike(user_id=user_id, movie_id=movie_id, is_like=is_like))
    await db.commit()


async def set_movie_rating(
    db: AsyncSession, user_id: int, movie_id: int, score: int
) -> None:
    await db.merge(MovieRating(user_id=user_id, movie_id=movie_id, rating=score))
    await db.commit()


async def add_movie_comment(
    db: AsyncSession, user_id: int, movie_id: int, payload: CommentCreate
) -> MovieComment:
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
