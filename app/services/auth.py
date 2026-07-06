import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    decode_token,
    hash_password,
    validate_password_complexity,
    verify_password,
)
from app.db.session import AsyncSessionLocal
from app.models import ActivationToken, RefreshToken, User, UserGroup, UserGroupEnum
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResendActivationRequest,
    TokenPairResponse,
)
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

    async def login(self, data: LoginRequest) -> TokenPairResponse:
        user = await self._authenticate_user(data)
        refresh_token = self._create_refresh_token(user)
        self._session.add(refresh_token)
        await self._session.commit()
        return self._create_token_pair(user, refresh_token.token)

    async def refresh(self, data: RefreshTokenRequest) -> TokenPairResponse:
        refresh_token = await self._get_refresh_token(data.refresh_token)
        if is_expired(refresh_token.expires_at):
            await self._session.delete(refresh_token)
            await self._session.commit()
            raise unauthorized("Refresh token has expired.")
        if not refresh_token.user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive.",
            )

        return self._create_token_pair(refresh_token.user, refresh_token.token)

    async def logout(self, data: LogoutRequest) -> MessageResponse:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token == data.refresh_token)
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token is not None:
            await self._session.delete(refresh_token)
            await self._session.commit()

        return MessageResponse(message="Logged out successfully.")

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

    async def _authenticate_user(self, data: LoginRequest) -> User:
        user = await self._get_user_by_email(normalize_email(data.email))
        if user is None or not verify_password(data.password, user.hashed_password):
            raise unauthorized("Invalid email or password.")
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive.",
            )
        return user

    async def _get_refresh_token(self, token: str) -> RefreshToken:
        result = await self._session.execute(
            select(RefreshToken)
            .options(selectinload(RefreshToken.user))
            .where(RefreshToken.token == token)
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token is None:
            raise unauthorized("Invalid refresh token.")
        return refresh_token

    def _create_activation_token(self, user: User) -> ActivationToken:
        return ActivationToken(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC)
            + timedelta(hours=self._settings.activation_token_ttl_hours),
        )

    def _create_refresh_token(self, user: User) -> RefreshToken:
        return RefreshToken(
            user=user,
            token=create_refresh_token_value(),
            expires_at=datetime.now(UTC)
            + timedelta(days=self._settings.refresh_token_expire_days),
        )

    def _create_token_pair(self, user: User, refresh_token: str) -> TokenPairResponse:
        return TokenPairResponse(
            access_token=create_access_token(user.id, user.email, self._settings),
            refresh_token=refresh_token,
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


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    token: str,
    session: AsyncSession,
    settings: Settings,
) -> User:
    try:
        payload = decode_token(token, settings)
        token_type = payload.get("type")
        user_id = int(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise unauthorized("Invalid access token.") from exc

    if token_type != "access":
        raise unauthorized("Invalid access token.")

    user = await session.get(User, user_id)
    if user is None:
        raise unauthorized("Invalid access token.")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )
    return user


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
