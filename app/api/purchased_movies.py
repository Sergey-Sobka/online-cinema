from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends

from app.core.dependencies import get_current_user, get_purchased_service
from app.models import User
from app.models.purchased_movies import PurchasedMovie
from app.schemas.purchased_movies import PurchasedMoviesResponse
from app.services.purchased_movies import PurchasedMovieService

router = APIRouter(prefix="/purchased_movies", tags=["User Purchased Movies"])


@router.get("/purchased_movies/{user_id}", response_model=list[PurchasedMoviesResponse])
async def get_purchased_movies(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PurchasedMovieService, Depends(get_purchased_service)],
) -> list[PurchasedMovie]:
    return await service.get_purchased_movies(current_user, user_id)
