from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Online Cinema"
    app_env: str = "local"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "online_cinema"
    postgres_user: str = "online_cinema"
    postgres_password: str = "online_cinema"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str = "no-reply@online-cinema.local"
    activation_url_base: HttpUrl | None = None
    activation_token_ttl_hours: int = 24
    password_reset_url_base: HttpUrl | None = None
    password_reset_token_ttl_hours: int = 1

    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_endpoint: str = "http://localhost:9000"
    minio_bucket: str = "online-cinema"

    stripe_secret_key: str = "sk_test..."
    stripe_webhook_secret: str = "whsec_..."

    database_url: str = Field(
        default="postgresql+asyncpg://online_cinema:online_cinema@localhost:5432/online_cinema"
    )
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
