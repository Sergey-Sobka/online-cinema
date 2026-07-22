from fastapi import APIRouter, Depends, status

from app.core.dependencies import require_moderator
from app.models import Movie
from app.schemas.movie import MovieCreate, MovieResponse, MovieUpdate
from app.services.movies import MovieService, get_movie_service

router = APIRouter(
    prefix="/admin/movies",
    tags=["Admin Movie Management"],
    dependencies=[Depends(require_moderator)],
)


@router.post(
    "",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new movie",
    responses={
        401: {"description": "Missing or corrupted authentication token"},
        403: {"description": "Insufficient permissions (Admin or Moderator required)"},
        422: {"description": "Validation error in the movie payload JSON structure"},
    },
)
async def create_new_movie(
    payload: MovieCreate, movie_service: MovieService = Depends(get_movie_service)
) -> Movie:
    """
    **Create and register a new movie record in the catalog.**

    **Permissions Required:**
    - Must be authenticated via a valid JWT token.
    - User group must be **Admin** or **Moderator**.

    Validates payload input structural constraints and appends records securely.
    """
    return await movie_service.create_new_movie(payload)


@router.put(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="Partially or fully update an existing movie",
    responses={
        401: {"description": "Missing or corrupted authentication token"},
        403: {"description": "Insufficient permissions (Admin or Moderator required)"},
        404: {"description": "Target movie entity not found"},
    },
)
async def update_existing_movie(
    movie_id: int,
    payload: MovieUpdate,
    movie_service: MovieService = Depends(get_movie_service),
) -> Movie | None:
    """
    **Modify an existing movie record.**

    Performs full or partial update transitions
    over the specified movie target attributes.

    **Permissions Required:**
    - Must be authenticated via a valid JWT token.
    - User group must be **Admin** or **Moderator**.
    """
    return await movie_service.update_existing_movie(movie_id, payload)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a movie",
    responses={
        401: {"description": "Missing or corrupted authentication token"},
        403: {"description": "Insufficient permissions (Admin or Moderator required)"},
        404: {"description": "Target movie entity not found"},
    },
)
async def delete_existing_movie(
    movie_id: int, movie_service: MovieService = Depends(get_movie_service)
) -> None:
    """
    **Permanently remove a movie record from the database storage.**

    **Warning:** This operation cascades down and purges all nested social attachments
    (likes, user scores, and related user comments) tied to this movie.

    **Permissions Required:**
    - Must be authenticated via a valid JWT token.
    - User group must be **Admin** or **Moderator**.
    """
    await movie_service.delete_existing_movie(movie_id)
