import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return cast(str, password_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return cast(bool, password_context.verify(plain_password, hashed_password))


def validate_password_complexity(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")


def create_access_token(user_id: int, email: str, settings: Settings) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "jti": secrets.token_urlsafe(16),
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, settings.jwt_algorithm)
    return cast(str, token)


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(32)


def decode_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Invalid token.") from exc
    return cast(dict[str, object], payload)
