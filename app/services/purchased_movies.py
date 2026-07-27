from fastapi import HTTPException

from app.core.uow_abstraction import IUnitOfWork
from app.models import User, UserGroupEnum
from app.models.purchased_movies import PurchasedMovie


class PurchasedMovieService:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    async def get_purchased_movies(
        self, current_user: User, user_id: int
    ) -> list[PurchasedMovie]:
        async with self.uow:
            if current_user.id != user_id and current_user.group.name not in (
                UserGroupEnum.ADMIN,
                UserGroupEnum.MODERATOR,
            ):
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to "
                           "view other users' purchased movies.",
                )
            else:
                return await self.uow.purchased_movies.get_purchased_movies_by_user_id(
                    user_id
                )

    async def create_purchased_movie(self, current_user: User, movie_id: int) -> None:
        async with self.uow:
            self.uow.purchased_movies.add_purchased_movie(current_user.id, movie_id)
