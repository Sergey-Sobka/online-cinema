from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import Order, OrderItem, OrderStatus
from app.models.movie import Director, Genre, Movie, MovieGenre, Star
from app.models.social import FavoriteMovie
from app.schemas.movie import MovieCreate, MovieUpdate


async def get_movies_catalog(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    year: int | None = None,
    min_rating: float | None = None,
    genre_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = "popularity",
    favorite_user_id: int | None = None,
) -> tuple[int, list[Movie]]:
    stmt = select(Movie).options(
        selectinload(Movie.genres),
        selectinload(Movie.directors),
        selectinload(Movie.stars),
        joinedload(Movie.certification),
    )

    if favorite_user_id:
        stmt = stmt.join(FavoriteMovie, Movie.id == FavoriteMovie.movie_id).where(
            FavoriteMovie.user_id == favorite_user_id
        )

    if search:
        stmt = stmt.where(
            or_(
                Movie.name.ilike(f"%{search}%"),
                Movie.description.ilike(f"%{search}%"),
                Movie.stars.any(Star.name.ilike(f"%{search}%")),
                Movie.directors.any(Director.name.ilike(f"%{search}%")),
            )
        )

    if year:
        stmt = stmt.where(Movie.year == year)
    if min_rating:
        stmt = stmt.where(Movie.imdb >= min_rating)
    if genre_id:
        stmt = stmt.where(Movie.genres.any(Genre.id == genre_id))

    if sort_by == "price":
        stmt = stmt.order_by(Movie.price.asc())
    elif sort_by == "release_date":
        stmt = stmt.order_by(Movie.year.desc())
    else:
        stmt = stmt.order_by(Movie.votes.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.scalars(stmt)
    return total, list(result.all())


async def get_movie_by_id(db: AsyncSession, movie_id: int) -> Movie | None:
    stmt = (
        select(Movie)
        .where(Movie.id == movie_id)
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars),
            joinedload(Movie.certification),
        )
    )
    return (await db.scalars(stmt)).first()


async def create_movie(db: AsyncSession, payload: MovieCreate) -> Movie:
    movie_data = payload.model_dump(exclude={"genre_ids", "director_ids", "star_ids"})
    movie = Movie(**movie_data)

    if payload.genre_ids:
        genres = await db.scalars(select(Genre).where(Genre.id.in_(payload.genre_ids)))
        movie.genres = list(genres.all())
    if payload.director_ids:
        directors = await db.scalars(
            select(Director).where(Director.id.in_(payload.director_ids))
        )
        movie.directors = list(directors.all())
    if payload.star_ids:
        stars = await db.scalars(select(Star).where(Star.id.in_(payload.star_ids)))
        movie.stars = list(stars.all())

    db.add(movie)
    await db.commit()
    await db.refresh(
        movie, attribute_names=["genres", "directors", "stars", "certification"]
    )
    return movie


async def update_movie(
    db: AsyncSession, movie_id: int, payload: MovieUpdate
) -> Movie | None:
    movie = await get_movie_by_id(db, movie_id)
    if not movie:
        return None

    update_data = payload.model_dump(
        exclude={"genre_ids", "director_ids", "star_ids"}, exclude_unset=True
    )
    for key, value in update_data.items():
        setattr(movie, key, value)

    if payload.genre_ids is not None:
        genres = await db.scalars(select(Genre).where(Genre.id.in_(payload.genre_ids)))
        movie.genres = list(genres.all())
    if payload.director_ids is not None:
        directors = await db.scalars(
            select(Director).where(Director.id.in_(payload.director_ids))
        )
        movie.directors = list(directors.all())
    if payload.star_ids is not None:
        stars = await db.scalars(select(Star).where(Star.id.in_(payload.star_ids)))
        movie.stars = list(stars.all())

    await db.commit()
    await db.refresh(
        movie, attribute_names=["genres", "directors", "stars", "certification"]
    )
    return movie


async def is_movie_purchased(db: AsyncSession, movie_id: int) -> bool:
    stmt = select(
        select(OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            OrderItem.movie_id == movie_id,
            Order.status
            == OrderStatus.PAID,
        )
        .exists()
    )
    result = await db.scalar(stmt)
    return result or False


async def delete_movie(db: AsyncSession, movie_id: int) -> bool:
    movie = await db.get(Movie, movie_id)
    if not movie:
        return False

    await db.delete(movie)
    await db.commit()
    return True


async def get_genres_with_counts(db: AsyncSession) -> list[dict[str, Any]]:
    stmt = (
        select(
            Genre.id, Genre.name, func.count(MovieGenre.movie_id).label("movies_count")
        )
        .join(MovieGenre, Genre.id == MovieGenre.genre_id, isouter=True)
        .group_by(Genre.id, Genre.name)
    )
    result = await db.execute(stmt)
    return [
        {"id": row.id, "name": row.name, "movies_count": row.movies_count}
        for row in result.all()
    ]
