from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user, require_moderator
from app.db.session import get_db_session
from app.main import app
from app.models import User


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 42
    return user


@pytest.fixture
async def client(mock_db, mock_user):
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_moderator] = lambda: mock_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
