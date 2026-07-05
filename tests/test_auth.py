from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.auth import get_auth_service
from app.api.dependencies import get_current_user
from app.core.config import Settings
from app.core.security import verify_password
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models import ActivationToken, RefreshToken, User, UserGroup, UserGroupEnum
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
)
from app.services.auth import (
    AuthService,
    cleanup_expired_activation_tokens,
    get_current_active_user,
)
from app.services.email import EmailDeliveryError


class FakeEmailService:
    def __init__(self) -> None:
        self.activation_emails: list[tuple[str, str]] = []

    def send_activation_email(self, recipient: str, token: str) -> None:
        self.activation_emails.append((recipient, token))


class FailingEmailService:
    def send_activation_email(self, recipient: str, token: str) -> None:
        raise EmailDeliveryError("SMTP is unavailable.")


class FakeAuthService:
    async def register(self, data: RegisterRequest) -> MessageResponse:
        return MessageResponse(message=f"registered {data.email}")

    async def activate(self, token: str) -> MessageResponse:
        return MessageResponse(message=f"activated {token}")

    async def resend_activation(self, data: object) -> MessageResponse:
        return MessageResponse(message="resent")

    async def login(self, data: LoginRequest) -> TokenPairResponse:
        return TokenPairResponse(access_token="access", refresh_token="refresh")

    async def refresh(self, data: RefreshTokenRequest) -> TokenPairResponse:
        return TokenPairResponse(access_token="new-access", refresh_token="refresh")

    async def logout(self, data: LogoutRequest) -> MessageResponse:
        return MessageResponse(message="Logged out successfully.")


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add(UserGroup(name=UserGroupEnum.USER))
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
def settings() -> Settings:
    return Settings(activation_token_ttl_hours=24)


async def create_active_user(
    db_session: AsyncSession,
    settings: Settings,
    email: str = "user@example.com",
    password: str = "Password1",
) -> User:
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]
    await service.register(RegisterRequest(email=email, password=password))
    token = (
        await db_session.execute(
            select(ActivationToken).join(User).where(User.email == email)
        )
    ).scalar_one()
    await service.activate(token.token)
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


async def test_register_creates_inactive_user_activation_token_and_sends_email(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    email_service = FakeEmailService()
    service = AuthService(db_session, settings, email_service)  # type: ignore[arg-type]

    response = await service.register(
        RegisterRequest(email="User@Example.com", password="Password1")
    )

    user = (
        await db_session.execute(select(User).where(User.email == "user@example.com"))
    ).scalar_one()
    token = (
        await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
    ).scalar_one()

    assert response.message == "Registration successful. Check your email."
    assert user.is_active is False
    assert verify_password("Password1", user.hashed_password)
    assert token.expires_at > datetime.now(UTC)
    assert email_service.activation_emails == [("user@example.com", token.token)]


async def test_register_rolls_back_user_when_activation_email_fails(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    service = AuthService(db_session, settings, FailingEmailService())  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        await service.register(
            RegisterRequest(email="user@example.com", password="Password1")
        )

    users = (await db_session.execute(select(User))).scalars().all()
    tokens = (await db_session.execute(select(ActivationToken))).scalars().all()
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert users == []
    assert tokens == []


async def test_register_rejects_duplicate_email(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]
    await service.register(
        RegisterRequest(email="user@example.com", password="Password1")
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.register(
            RegisterRequest(email="USER@example.com", password="Password1")
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT


async def test_activate_marks_user_active_and_deletes_token(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]
    await service.register(
        RegisterRequest(email="user@example.com", password="Password1")
    )
    token = (await db_session.execute(select(ActivationToken))).scalar_one()

    response = await service.activate(token.token)

    user = (await db_session.execute(select(User))).scalar_one()
    remaining_token = (
        await db_session.execute(select(ActivationToken))
    ).scalar_one_or_none()
    assert response.message == "Account activated successfully."
    assert user.is_active is True
    assert remaining_token is None


async def test_cleanup_expired_activation_tokens(db_session: AsyncSession) -> None:
    group = (
        await db_session.execute(
            select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
        )
    ).scalar_one()
    expired_user = User(
        email="expired@example.com",
        hashed_password="hash",
        is_active=False,
        group=group,
    )
    valid_user = User(
        email="valid@example.com",
        hashed_password="hash",
        is_active=False,
        group=group,
    )
    db_session.add_all([expired_user, valid_user])
    await db_session.flush()
    db_session.add_all(
        [
            ActivationToken(
                user=expired_user,
                token="expired",
                expires_at=datetime.now(UTC) - timedelta(hours=1),
            ),
            ActivationToken(
                user=valid_user,
                token="valid",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        ]
    )
    await db_session.commit()

    deleted_count = await cleanup_expired_activation_tokens(db_session)

    tokens = (await db_session.execute(select(ActivationToken))).scalars().all()
    assert deleted_count == 1
    assert [token.token for token in tokens] == ["valid"]


async def test_login_returns_token_pair_and_stores_refresh_token(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    user = await create_active_user(db_session, settings)
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]

    response = await service.login(
        LoginRequest(email="USER@example.com", password="Password1")
    )

    refresh_token = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    ).scalar_one()
    assert response.token_type == "bearer"
    assert response.access_token
    assert response.refresh_token == refresh_token.token


async def test_login_rejects_inactive_user(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]
    await service.register(
        RegisterRequest(email="user@example.com", password="Password1")
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            LoginRequest(email="user@example.com", password="Password1")
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


async def test_login_rejects_invalid_password(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    await create_active_user(db_session, settings)
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        await service.login(LoginRequest(email="user@example.com", password="Wrong1"))

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


async def test_refresh_returns_new_access_token(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    await create_active_user(db_session, settings)
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]
    login_response = await service.login(
        LoginRequest(email="user@example.com", password="Password1")
    )

    refresh_response = await service.refresh(
        RefreshTokenRequest(refresh_token=login_response.refresh_token)
    )

    assert refresh_response.access_token
    assert refresh_response.refresh_token == login_response.refresh_token


async def test_logout_deletes_refresh_token(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    await create_active_user(db_session, settings)
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]
    login_response = await service.login(
        LoginRequest(email="user@example.com", password="Password1")
    )

    response = await service.logout(
        LogoutRequest(refresh_token=login_response.refresh_token)
    )

    refresh_token = (
        await db_session.execute(select(RefreshToken))
    ).scalar_one_or_none()
    assert response.message == "Logged out successfully."
    assert refresh_token is None


async def test_get_current_active_user_returns_user(
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    await create_active_user(db_session, settings)
    service = AuthService(db_session, settings, FakeEmailService())  # type: ignore[arg-type]
    login_response = await service.login(
        LoginRequest(email="user@example.com", password="Password1")
    )

    user = await get_current_active_user(
        login_response.access_token,
        db_session,
        settings,
    )

    assert user.email == "user@example.com"


async def test_auth_router_delegates_to_service() -> None:
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "Password1"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"message": "registered user@example.com"}


async def test_me_endpoint_uses_auth_dependency(db_session: AsyncSession) -> None:
    user = User(
        email="user@example.com",
        hashed_password="hash",
        is_active=True,
        group_id=1,
    )
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer token"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"email": "user@example.com"}
