import asyncio

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "online_cinema",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    timezone="UTC",
    beat_schedule={
        "cleanup-expired-activation-tokens": {
            "task": "online_cinema.cleanup_expired_activation_tokens",
            "schedule": 3600.0,
        },
    },
)


@celery_app.task(name="online_cinema.health_check")
def celery_health_check() -> str:
    return "ok"


@celery_app.task(name="online_cinema.cleanup_expired_activation_tokens")
def cleanup_expired_activation_tokens() -> int:
    from app.services.auth import cleanup_expired_activation_tokens as cleanup

    return asyncio.run(cleanup())
