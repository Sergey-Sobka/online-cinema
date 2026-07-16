from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password, validate_password_complexity
from app.models import Cart, User, UserGroup, UserGroupEnum
from app.schemas.admin_users import AdminUserCreateRequest, AdminUserResponse
from app.services.auth import email_conflict, normalize_email


class AdminUserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(self, data: AdminUserCreateRequest) -> AdminUserResponse:
        email = normalize_email(data.email)
        await self._ensure_email_is_available(email)
        validate_admin_password(data.password)

        group = await self._get_group(data.group)
        user = User(
            email=email,
            hashed_password=hash_password(data.password),
            is_active=data.is_active,
            group=group,
            cart=Cart(),
        )
        self._session.add(user)

        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise email_conflict() from exc

        return to_admin_user_response(user)

    async def delete_user(self, user_id: int) -> None:
        user = await self._get_user(user_id)
        await self._session.delete(user)
        await self._session.commit()

    async def _ensure_email_is_available(self, email: str) -> None:
        result = await self._session.execute(select(User.id).where(User.email == email))
        if result.scalar_one_or_none() is not None:
            raise email_conflict()

    async def _get_group(self, group_name: UserGroupEnum) -> UserGroup:
        result = await self._session.execute(
            select(UserGroup).where(UserGroup.name == group_name)
        )
        group = result.scalar_one_or_none()
        if group is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User group does not exist.",
            )
        return group

    async def _get_user(self, user_id: int) -> User:
        result = await self._session.execute(
            select(User).options(selectinload(User.group)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User was not found.",
            )
        return user


def validate_admin_password(password: str) -> None:
    try:
        validate_password_complexity(password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def to_admin_user_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        message="User created successfully.",
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        group=user.group.name,
    )


def build_admin_user_service(session: AsyncSession) -> AdminUserService:
    return AdminUserService(session=session)
