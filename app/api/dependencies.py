from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models import User, UserGroupEnum
from app.services.auth import get_current_active_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    return await get_current_active_user(token, session, get_settings())


async def require_moderator(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.group.name not in (UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify catalog records.",
        )
    return user
