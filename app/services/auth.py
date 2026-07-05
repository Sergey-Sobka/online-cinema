import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.security import hash_password, validate_password_complexity
from app.db.session import AsyncSessionLocal
from app.models import ActivationToken, User, UserGroup, UserGroupEnum
from app.schemas.auth import MessageResponse, RegisterRequest, ResendActivationRequest
from app.services.email import EmailDeliveryError, EmailService


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        email_service: EmailService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._email_service = email_service or EmailService(settings)

    async def register(self, data: RegisterRequest) -> MessageResponse:
        email = normalize_email(data.email)
        await self._ensure_email_is_available(email)
        validate_password(data.password)

        group = await self._get_user_group()
        user = User(
            email=email,
            hashed_password=hash_password(data.password),
            is_active=False,
            group=group,
        )
        self._session.add(user)
        await self._session.flush()

        activation_token = self._create_activation_token(user)
        self._session.add(activation_token)
        await self._session.flush()

        await self._send_activation_email(email, activation_token.token)
        await self._session.commit()
        return MessageResponse(message="Registration successful. Check your email.")

    async def activate(self, token: str) -> MessageResponse:
        activation_token = await self._get_activation_token(token)
        if is_expired(activation_token.expires_at):
            await self._session.delete(activation_token)
            await self._session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation token has expired.",
            )

        activation_token.user.is_active = True
        await self._session.delete(activation_token)
        await self._session.commit()
        return MessageResponse(message="Account activated successfully.")

    async def resend_activation(self, data: ResendActivationRequest) -> MessageResponse:
        email = normalize_email(data.email)
        user = await self._get_user_by_email(email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email was not found.",
            )
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is already active.",
            )

        if user.activation_token is not None:
            await self._session.delete(user.activation_token)
            await self._session.flush()

        activation_token = self._create_activation_token(user)
        self._session.add(activation_token)
        await self._session.flush()

        await self._send_activation_email(email, activation_token.token)
        await self._session.commit()
        return MessageResponse(message="Activation email has been sent.")

    async def _ensure_email_is_available(self, email: str) -> None:
        user = await self._get_user_by_email(email)
        if user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            )

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.activation_token))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def _get_user_group(self) -> UserGroup:
        result = await self._session.execute(
            select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
        )
        group = result.scalar_one_or_none()
        if group is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default user group is not configured.",
            )
        return group

    async def _get_activation_token(self, token: str) -> ActivationToken:
        result = await self._session.execute(
            select(ActivationToken)
            .options(selectinload(ActivationToken.user))
            .where(ActivationToken.token == token)
        )
        activation_token = result.scalar_one_or_none()
        if activation_token is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activation token was not found.",
            )
        return activation_token

    def _create_activation_token(self, user: User) -> ActivationToken:
        return ActivationToken(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC)
            + timedelta(hours=self._settings.activation_token_ttl_hours),
        )

    async def _send_activation_email(self, email: str, token: str) -> None:
        try:
            self._email_service.send_activation_email(email, token)
        except EmailDeliveryError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Activation email could not be sent. Please try again later.",
            ) from exc


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    try:
        validate_password_complexity(password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)


async def cleanup_expired_activation_tokens(
    session: AsyncSession | None = None,
) -> int:
    close_session = session is None
    active_session = session or AsyncSessionLocal()

    try:
        result = await active_session.execute(
            delete(ActivationToken).where(
                ActivationToken.expires_at <= datetime.now(UTC)
            )
        )
        await active_session.commit()
        return int(getattr(result, "rowcount", 0) or 0)
    finally:
        if close_session:
            await active_session.close()


def build_auth_service(session: AsyncSession) -> AuthService:
    settings = get_settings()
    return AuthService(session=session, settings=settings)
