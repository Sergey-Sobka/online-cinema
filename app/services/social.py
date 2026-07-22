from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import social as social_crud
from app.db.session import get_db_session
from app.models import MovieComment, User
from app.schemas.movie import CommentCreate
from app.worker import send_comment_notification_task


class SocialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _notify_comment_author(
        actor: User, target_comment: MovieComment, subject: str, message_body: str
    ) -> None:
        if target_comment.user_id != actor.id:
            send_comment_notification_task.delay(
                recipient_email=target_comment.user.email,
                subject=subject,
                message_body=message_body,
            )

    async def add_favorite(self, user_id: int, movie_id: int) -> None:
        await social_crud.toggle_favorite(self.db, user_id, movie_id, add=True)

    async def remove_favorite(self, user_id: int, movie_id: int) -> None:
        await social_crud.toggle_favorite(self.db, user_id, movie_id, add=False)

    async def like_movie(self, user_id: int, movie_id: int, is_like: bool) -> None:
        await social_crud.set_movie_like(self.db, user_id, movie_id, is_like)

    async def rate_movie(self, user_id: int, movie_id: int, score: int) -> None:
        await social_crud.set_movie_rating(self.db, user_id, movie_id, score)

    async def add_comment(
        self, user: User, movie_id: int, payload: CommentCreate
    ) -> MovieComment:
        comment = await social_crud.add_movie_comment(
            self.db, user.id, movie_id, payload
        )

        if hasattr(payload, "parent_id") and payload.parent_id is not None:
            parent_comment = await social_crud.get_comment_by_id(
                self.db, payload.parent_id
            )

            if parent_comment:
                self._notify_comment_author(
                    actor=user,
                    target_comment=parent_comment,
                    subject="New reply to your comment!",
                    message_body=(
                        f"Hello!\n\nUser {user.email} left "
                        f"a reply to your comment on movie #{movie_id}.\n\nThank you!"
                    ),
                )
        return comment

    async def like_comment(self, user: User, comment_id: int, is_like: bool) -> None:
        comment = await social_crud.get_comment_by_id(self.db, comment_id)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
            )

        await social_crud.set_comment_like(self.db, user.id, comment_id, is_like)

        if is_like:
            self._notify_comment_author(
                actor=user,
                target_comment=comment,
                subject="Someone liked your comment!",
                message_body=(
                    f"Hello!\n\nUser {user.email} just liked your comment "
                    f"on movie #{comment.movie_id}.\n\nKeep it up!"
                ),
            )


def get_social_service(db: AsyncSession = Depends(get_db_session)) -> SocialService:
    return SocialService(db)
