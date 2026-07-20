from datetime import date

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import get_storage_service
from app.core.dependencies import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.models import User, UserProfile


class FakeStorageService:
    def __init__(self) -> None:
        self.uploads: list[tuple[int, bytes, str | None, str]] = []

    def upload_avatar(
        self,
        *,
        user_id: int,
        content: bytes,
        filename: str | None,
        content_type: str,
    ) -> str:
        self.uploads.append((user_id, content, filename, content_type))
        return f"http://storage.test/avatars/{user_id}/{filename}"


async def test_get_profile_creates_empty_profile(
    db_session: AsyncSession,
    create_user,
) -> None:
    user = await create_user(email="profile@example.com")
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/users/me/profile")

    app.dependency_overrides.clear()
    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    assert response.status_code == 200
    assert response.json()["avatar"] is None
    assert profile.user_id == user.id


async def test_update_profile(
    db_session: AsyncSession,
    create_user,
) -> None:
    user = await create_user(email="update-profile@example.com")
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user

    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "gender": "WOMAN",
        "date_of_birth": "1995-05-12",
        "info": "Cinema fan.",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.patch("/api/v1/users/me/profile", json=payload)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Ada"
    assert body["date_of_birth"] == "1995-05-12"

    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    assert profile.last_name == "Lovelace"
    assert profile.date_of_birth == date(1995, 5, 12)


async def test_upload_avatar_uses_storage_and_updates_profile(
    db_session: AsyncSession,
    create_user,
) -> None:
    user: User = await create_user(email="avatar@example.com")
    storage = FakeStorageService()
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_storage_service] = lambda: storage

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"avatar": ("avatar.png", b"image-bytes", "image/png")},
        )

    app.dependency_overrides.clear()
    expected_avatar = f"http://storage.test/avatars/{user.id}/avatar.png"
    assert response.status_code == 200
    assert response.json()["avatar"] == expected_avatar
    assert storage.uploads == [(user.id, b"image-bytes", "avatar.png", "image/png")]

    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    assert profile.avatar == expected_avatar


async def test_upload_avatar_rejects_non_image(
    db_session: AsyncSession,
    create_user,
) -> None:
    user = await create_user(email="invalid-avatar@example.com")
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_storage_service] = lambda: FakeStorageService()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"avatar": ("notes.txt", b"text", "text/plain")},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Avatar must be an image file."
