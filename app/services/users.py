from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserProfile
from app.schemas.users import UserProfileRead, UserProfileUpdate
from app.services.storage import StorageService


class UserProfileService:
    def __init__(self, session: AsyncSession, storage: StorageService) -> None:
        self._session = session
        self._storage = storage

    async def get_profile(self, user: User) -> UserProfileRead:
        profile = await self._get_or_create_profile(user)
        return UserProfileRead.model_validate(profile)

    async def update_profile(
        self,
        user: User,
        data: UserProfileUpdate,
    ) -> UserProfileRead:
        profile = await self._get_or_create_profile(user)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(profile, field, value)

        await self._session.commit()
        await self._session.refresh(profile)
        return UserProfileRead.model_validate(profile)

    async def upload_avatar(
        self,
        user: User,
        *,
        content: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> UserProfileRead:
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Avatar file is empty.",
            )
        if not content_type or not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Avatar must be an image file.",
            )

        profile = await self._get_or_create_profile(user)
        profile.avatar = self._storage.upload_avatar(
            user_id=user.id,
            content=content,
            filename=filename,
            content_type=content_type,
        )
        await self._session.commit()
        await self._session.refresh(profile)
        return UserProfileRead.model_validate(profile)

    async def _get_or_create_profile(self, user: User) -> UserProfile:
        result = await self._session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = result.scalar_one_or_none()
        if profile is not None:
            return profile

        profile = UserProfile(user_id=user.id)
        self._session.add(profile)
        await self._session.flush()
        return profile


def build_user_profile_service(
    session: AsyncSession,
    storage: StorageService,
) -> UserProfileService:
    return UserProfileService(session=session, storage=storage)
