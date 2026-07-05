import re
from typing import cast

from passlib.context import CryptContext

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
