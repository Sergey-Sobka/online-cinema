from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.crud import movies as movies_crud
from app.crud import social as social_crud
from app.db.session import get_db_session
from app.models import MovieComment, User
from app.schemas.movie import CommentCreate, CommentResponse, PaginatedMovieResponse
from app.worker import send_comment_notification_task

router = APIRouter(prefix="/movies", tags=["User Social Actions"])


@router.get(
    "/user/favorites",
    response_model=PaginatedMovieResponse,
    summary="Perform catalog functions on the user's favorites list",
    responses={401: {"description": "Authentication token missing or invalid"}},
)
async def get_user_favorites(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    year: int | None = None,
    min_rating: float | None = None,
    genre_id: int | None = None,
    search: str | None = None,
    sort_by: str = Query("popularity"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    **View an authenticated user's bookmarked favorite movies list.**

    Applies exact filtering, sorting, and pagination strategies over
    the active subset of movies explicitly saved to favorites by the current user.

    **Permissions Required:**
    - Valid authenticated **User**, **Moderator**, or **Admin** JWT token.
    """
    total, results = await movies_crud.get_movies_catalog(
        db,
        page=page,
        limit=limit,
        year=year,
        min_rating=min_rating,
        genre_id=genre_id,
        search=search,
        sort_by=sort_by,
        favorite_user_id=user.id,
    )
    return {"total": total, "page": page, "limit": limit, "results": results}


@router.post(
    "/{movie_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add movie to favorites",
    responses={
        401: {"description": "Authentication token missing or invalid"},
        404: {"description": "Target movie record not found"},
    },
)
async def add_favorite(
    movie_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> None:
    """
    **Add a specific movie to the authenticated user's favorite bookmarks.**

    Idempotent operation that assigns a favorite link entity context mapping.

    **Permissions Required:**
    - Valid authenticated JWT token.
    """
    await social_crud.toggle_favorite(db, user.id, movie_id, add=True)


@router.delete(
    "/{movie_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove movie from favorites",
    responses={
        401: {"description": "Authentication token missing or invalid"},
        404: {"description": "Target movie record not found"},
    },
)
async def remove_favorite(
    movie_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> None:
    """
    **Remove a specific movie from the user's favorite bookmarks.**

    Detaches the user's favorite contextual
    binding mapping without deleting the movie itself.

    **Permissions Required:**
    - Valid authenticated JWT token.
    """
    await social_crud.toggle_favorite(db, user.id, movie_id, add=False)


@router.post(
    "/{movie_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Like or dislike a movie",
    responses={
        401: {"description": "Authentication token missing or invalid"},
        404: {"description": "Target movie record not found"},
    },
)
async def like_movie(
    movie_id: int,
    is_like: bool = Query(..., description="True for like, False for dislike"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> None:
    """
    **Express a like or dislike reaction toward a given movie.**

    Updates or toggles reaction records based on the binary state parameter:
    - **True:** Upvote / Like.
    - **False:** Downvote / Dislike.

    **Permissions Required:**
    - Valid authenticated JWT token.
    """
    await social_crud.set_movie_like(db, user.id, movie_id, is_like)


@router.post(
    "/{movie_id}/rate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Rate movie on a 10-point scale",
    responses={
        401: {"description": "Authentication token missing or invalid"},
        404: {"description": "Target movie record not found"},
        422: {"description": "Rating score scale constraint value out of bounds"},
    },
)
async def rate_movie(
    movie_id: int,
    score: int = Query(..., ge=1, le=10, description="Rating score from 1 to 10"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> None:
    """
    **Submit a numerical rating evaluate score for a movie.**

    Calculates global catalog average rating statistics updates later on.
    Allows integers bounded strict from **1** to **10** points limit boundaries.

    **Permissions Required:**
    - Valid authenticated JWT token.
    """
    await social_crud.set_movie_rating(db, user.id, movie_id, score)


@router.post(
    "/{movie_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Write a comment or reply to an existing one",
    responses={
        401: {"description": "Authentication token missing or invalid"},
        404: {"description": "Target movie or parent reference id context missing"},
        422: {
            "description": "Malformed body "
            "formatting rules constraint validation failed"
        },
    },
)
async def add_comment(
    movie_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> MovieComment:
    """
    **Publish a textual review comment or submit
    nested replies under a movie timeline thread.**

    Supports root comment posts or threading
    hierarchy responses targeting upstream comment keys.

    **Permissions Required:**
    - Valid authenticated JWT token.
    """
    comment = await social_crud.add_movie_comment(db, user.id, movie_id, payload)

    if hasattr(payload, "parent_id") and payload.parent_id is not None:
        parent_comment = await social_crud.get_comment_by_id(db, payload.parent_id)

        if parent_comment and parent_comment.user_id != user.id:
            parent_user_email = parent_comment.user.email
            send_comment_notification_task.delay(
                recipient_email=parent_user_email,
                subject="New reply to your comment!",
                message_body=f"Hello!\n\nUser {user.email} left "
                f"a reply to your comment on movie #{movie_id}.\n\nThank you!",
            )
    return comment
