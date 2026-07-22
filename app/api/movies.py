from typing import Any

from fastapi import APIRouter, Depends, Query

from app.schemas.movie import (
    GenreWithCountResponse,
    MovieResponse,
    PaginatedMovieResponse,
)
from app.services.movies import MovieService, get_movie_service

router = APIRouter(prefix="/movies", tags=["Movie Catalog"])


@router.get(
    "",
    response_model=PaginatedMovieResponse,
    summary="Browse movie catalog with pagination, filters, sorting, and search",
)
async def get_movies(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page limit"),
    year: int | None = Query(None, description="Release year"),
    min_rating: float | None = Query(
        None, ge=0.0, le=10.0, description="Minimum IMDb rating"
    ),
    genre_id: int | None = Query(None, description="Filter by genre ID"),
    search: str | None = Query(
        None, description="Search by title, description, actor, or director"
    ),
    sort_by: str = Query(
        "popularity",
        regex="^(popularity|price|release_date)$",
        description="Sort attribute",
    ),
    movie_service: MovieService = Depends(get_movie_service),
) -> dict[str, Any]:
    """
    **Browse the movie catalog with advanced filtering.**

    This public endpoint allows any client to search and filter movies by:
    - **Pagination:** Control page numbers and items per page limits.
    - **Release Year:** Filter movies released in a specific year.
    - **IMDb Rating:** Set a minimum threshold for ratings.
    - **Genres:** Filter by specific genre unique identifier.
    - **Full-text Search:** Matches queries against
    title, description, cast, or directors.
    - **Sorting:** Sort results dynamically by popularity, price, or release date.
    """
    total, results = await movie_service.get_movies_catalog(
        page=page,
        limit=limit,
        year=year,
        min_rating=min_rating,
        genre_id=genre_id,
        search=search,
        sort_by=sort_by,
    )
    return {"total": total, "page": page, "limit": limit, "results": results}


@router.get(
    "/genres",
    response_model=list[GenreWithCountResponse],
    summary="View a list of genres with the count of movies in each",
)
async def get_genres_list(
    movie_service: MovieService = Depends(get_movie_service),
) -> list[dict[str, Any]]:
    """
    **Retrieve a list of all genres.**

    Returns a complete list of movie genres available in the database,
    including the total counter of active movies associated with each genre.
    """
    return await movie_service.get_genres_list()


@router.get(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="View detailed descriptions of a movie",
    responses={404: {"description": "Movie not found"}},
)
async def get_movie_detail(
    movie_id: int,
    movie_service: MovieService = Depends(get_movie_service),
) -> Any:
    """
    **Get comprehensive details of a specific movie.**

    Fetches full metadata for a movie by its unique database ID.

    - **Returns 404:** If the requested movie does not exist.
    """
    return await movie_service.get_movie_detail(movie_id)
