from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.crud.movies import get_genres_with_counts, get_movie_by_id, get_movies_catalog
from app.models.movie import Base, Certification, Director, Genre, Movie, Star

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def local_db():
    """
    Creates ONLY movie-related tables inside the isolated test database.
    """
    catalog_tables = [
        Certification.__table__,
        Genre.__table__,
        Star.__table__,
        Director.__table__,
        Movie.__table__,
        Base.metadata.tables["movie_genres"],
        Base.metadata.tables["movie_directors"],
        Base.metadata.tables["movie_stars"],
    ]

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=catalog_tables)
        )

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=catalog_tables)
        )


@pytest.fixture(autouse=True)
async def setup_test_data(local_db: AsyncSession):
    """
    Seeds the isolated database with sample data before running each test.
    """
    cert = Certification(name="PG-13")
    local_db.add(cert)
    await local_db.flush()

    genre_action = Genre(name="Action")
    genre_drama = Genre(name="Drama")
    local_db.add_all([genre_action, genre_drama])
    await local_db.flush()

    star = Star(name="Keanu Reeves")
    director = Director(name="Christopher Nolan")
    local_db.add_all([star, director])
    await local_db.flush()

    movie1 = Movie(
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=2500000,
        description="A thief who steals corporate secrets "
                    "through the use of dream-sharing technology.",
        price=Decimal("14.99"),
        certification_id=cert.id,
        genres=[genre_action, genre_drama],
        directors=[director],
        stars=[star],
    )

    movie2 = Movie(
        name="The Matrix",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1900000,
        description="When a beautiful stranger leads "
                    "computer hacker Neo to a forbidding underworld...",
        price=Decimal("9.99"),
        certification_id=cert.id,
        genres=[genre_action],
        directors=[],
        stars=[star],
    )

    local_db.add_all([movie1, movie2])
    await local_db.commit()


@pytest.mark.anyio
async def test_get_movies_catalog_pagination(local_db: AsyncSession):
    """Test pagination works and returns correct totals."""
    total, results = await get_movies_catalog(local_db, page=1, limit=1)

    assert total == 2
    assert len(results) == 1
    assert results[0].name == "Inception"


@pytest.mark.anyio
async def test_get_movies_catalog_filter_by_year(local_db: AsyncSession):
    """Test filtering movies by release year."""
    total, results = await get_movies_catalog(local_db, year=1999)

    assert total == 1
    assert results[0].name == "The Matrix"


@pytest.mark.anyio
async def test_get_movies_catalog_search(local_db: AsyncSession):
    """Test search functionality across title, description, stars, and directors."""
    _, res_title = await get_movies_catalog(local_db, search="Matrix")
    assert len(res_title) == 1

    _, res_actor = await get_movies_catalog(local_db, search="Keanu")
    assert len(res_actor) == 2

    _, res_director = await get_movies_catalog(local_db, search="Nolan")
    assert len(res_director) == 1
    assert res_director[0].name == "Inception"


@pytest.mark.anyio
async def test_get_movies_catalog_sorting(local_db: AsyncSession):
    """Test sorting by different fields (price, release date)."""
    _, res_price = await get_movies_catalog(local_db, sort_by="price")
    assert res_price[0].name == "The Matrix"

    _, res_date = await get_movies_catalog(local_db, sort_by="release_date")
    assert res_date[0].year == 2010


@pytest.mark.anyio
async def test_get_movie_detail_n1_optimized(local_db: AsyncSession):
    """Test that movie detail fetches
    relations properly without lazy-loading failures."""
    movie_id = (await local_db.scalars(select(Movie.id).limit(1))).first()

    movie = await get_movie_by_id(local_db, movie_id=movie_id)
    assert movie is not None

    assert len(movie.genres) > 0
    assert movie.certification.name == "PG-13"


@pytest.mark.anyio
async def test_genre_list_with_movie_count(local_db: AsyncSession):
    """Test aggregation of genres with movie counts."""
    counts = await get_genres_with_counts(local_db)

    genre_map = {g["name"]: g["movies_count"] for g in counts}

    assert genre_map["Action"] == 2
    assert genre_map["Drama"] == 1
