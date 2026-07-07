import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import joinedload
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_current_user, require_moderator
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models import (
    Certification,
    Movie,
    Payment,
    PaymentStatus,
    User,
    UserGroup,
    UserGroupEnum,
)
from app.services.orders import OrderService


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
        session.add_all(
            [UserGroup(name=UserGroupEnum.USER), UserGroup(name=UserGroupEnum.ADMIN)]
        )
        await session.commit()
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
def create_user(db_session):
    async def _create_user(email=None, password="test123456789", group_id=1):
        if email is None:
            email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=email, hashed_password=password, is_active=True, group_id=group_id
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest_asyncio.fixture
def create_order(db_session, create_user):
    async def _create_order(user=None):
        certification = Certification(name="Name")
        db_session.add(certification)
        await db_session.flush()
        movie_1 = Movie(
            name="Movie",
            uuid=uuid.uuid4(),
            year=2020,
            time=90,
            imdb=4,
            votes=100,
            meta_score=6,
            description="d",
            price=Decimal("100"),
            certification_id=certification.id,
        )
        movie_2 = Movie(
            name="Movie2",
            uuid=uuid.uuid4(),
            year=2020,
            time=90,
            imdb=4,
            votes=100,
            meta_score=6,
            description="d",
            price=Decimal("100"),
            certification_id=certification.id,
        )
        db_session.add_all([movie_1, movie_2])
        await db_session.flush()

        user = user or await create_user()
        service = OrderService(db_session)
        order = await service.place_order(
            current_user=user, movie_ids=[movie_1.id, movie_2.id]
        )
        return order

    return _create_order


@pytest_asyncio.fixture
async def admin_user(db_session, create_user):
    admin_group = await db_session.scalar(
        select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN)
    )
    user = await create_user(group_id=admin_group.id)
    stmt = select(User).options(joinedload(User.group)).where(User.id == user.id)
    result = await db_session.execute(stmt)
    full_user = result.scalar_one()
    return full_user


@pytest_asyncio.fixture
async def paid_payment(db_session, create_order):
    order = await create_order()
    payment = Payment(
        user_id=order.user_id,
        order_id=order.id,
        amount=Decimal(200),
        external_payment_id=f"pi_{uuid.uuid4().hex}",
        status=PaymentStatus.SUCCESSFUL,
    )
    db_session.add(payment)
    await db_session.commit()
    await db_session.refresh(payment)
    return payment
