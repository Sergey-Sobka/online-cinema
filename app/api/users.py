from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.users import UserProfileRead, UserProfileUpdate
from app.services.storage import StorageService
from app.services.users import UserProfileService, build_user_profile_service

router = APIRouter(prefix="/users", tags=["Users"])


def get_storage_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StorageService:
    return StorageService(settings)


def get_user_profile_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> UserProfileService:
    return build_user_profile_service(session, storage)


@router.get(
    "/me/profile",
    response_model=UserProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description=(
        "Return the authenticated user's profile. "
        "Creates an empty profile if it does not exist yet."
    ),
)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserProfileService, Depends(get_user_profile_service)],
) -> UserProfileRead:
    return await service.get_profile(current_user)


@router.patch(
    "/me/profile",
    response_model=UserProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Update editable profile fields for the authenticated user.",
)
async def update_my_profile(
    data: UserProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserProfileService, Depends(get_user_profile_service)],
) -> UserProfileRead:
    return await service.update_profile(current_user, data)


@router.post(
    "/me/avatar",
    response_model=UserProfileRead,
    status_code=status.HTTP_200_OK,
    summary="Upload current user avatar",
    description=(
        "Upload an image avatar to MinIO/S3-compatible storage "
        "and store its URL in the user profile."
    ),
)
async def upload_my_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserProfileService, Depends(get_user_profile_service)],
    avatar: Annotated[UploadFile, File(description="Image file to use as avatar.")],
) -> UserProfileRead:
    content = await avatar.read()
    return await service.upload_avatar(
        current_user,
        content=content,
        filename=avatar.filename,
        content_type=avatar.content_type,
    )
