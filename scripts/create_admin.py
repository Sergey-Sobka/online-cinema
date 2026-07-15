import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import hash_password  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models import Cart, User, UserGroup, UserGroupEnum  # noqa: E402

email_adapter = TypeAdapter(EmailStr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or promote an admin user.")
    parser.add_argument("email", help="Admin email.")
    parser.add_argument("password", help="Admin password.")
    return parser.parse_args()


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password cannot be longer than 72 bytes for bcrypt.")


def normalize_email(email: str) -> str:
    try:
        return str(email_adapter.validate_python(email.strip())).lower()
    except ValidationError as exc:
        raise ValueError("Invalid email address.") from exc


async def create_or_promote_admin(email: str, password: str) -> str:
    async with AsyncSessionLocal() as session:
        group = await session.scalar(
            select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN)
        )
        if group is None:
            raise RuntimeError("ADMIN group does not exist. Run migrations first.")

        result = await session.execute(
            select(User).options(selectinload(User.cart)).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                is_active=True,
                group=group,
                cart=Cart(),
            )
            session.add(user)
            message = "Admin user created."
        else:
            user.hashed_password = hash_password(password)
            user.is_active = True
            user.group = group
            if user.cart is None:
                user.cart = Cart()
            message = "Existing user promoted to admin."

        await session.commit()
        return message


async def main() -> None:
    args = parse_args()
    email = normalize_email(args.email)
    password = args.password

    validate_password(password)
    message = await create_or_promote_admin(email, password)
    print(message)
    print(f"email: {email}")


if __name__ == "__main__":
    asyncio.run(main())
