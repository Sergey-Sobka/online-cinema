from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.uow import SqlAlchemyUnitOfWork
from app.core.uow_abstraction import IUnitOfWork
from app.db.session import AsyncSessionLocal, get_db_session
from app.models import User, UserGroupEnum
from app.services.auth import get_current_active_user
from app.services.email import EmailService
from app.services.orders import OrderService
from app.services.payments import PaymentService
from app.services.purchased_movies import PurchasedMovieService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    return await get_current_active_user(token, session, get_settings())


def get_email_service() -> EmailService:
    settings = get_settings()
    return EmailService(settings=settings)


def get_uow() -> IUnitOfWork:
    return SqlAlchemyUnitOfWork(AsyncSessionLocal)


def get_payment_service(
    uow: Annotated[IUnitOfWork, Depends(get_uow)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentService:
    return PaymentService(uow, settings, email_service)


def get_order_service(uow: Annotated[IUnitOfWork, Depends(get_uow)]) -> OrderService:
    return OrderService(uow)


def get_purchased_service(
    uow: Annotated[IUnitOfWork, Depends(get_uow)],
) -> PurchasedMovieService:
    return PurchasedMovieService(uow)


async def require_moderator(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.group.name not in (UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify catalog records.",
        )
    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage users.",
        )
    return user
