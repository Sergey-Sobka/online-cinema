from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_db_session
from app.models import User
from app.schemas.admin_users import AdminUserCreateRequest, AdminUserResponse
from app.schemas.auth import MessageResponse
from app.services.admin_users import AdminUserService, build_admin_user_service

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


def get_admin_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUserService:
    return build_admin_user_service(session)


@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a user manually. Admin access is required.",
)
async def create_user(
    data: AdminUserCreateRequest,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
) -> AdminUserResponse:
    return await service.create_user(data)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete user",
    description="Delete a user manually. Admin access is required.",
)
async def delete_user(
    user_id: int,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
) -> MessageResponse:
    await service.delete_user(user_id)
    return MessageResponse(message="User deleted successfully.")
