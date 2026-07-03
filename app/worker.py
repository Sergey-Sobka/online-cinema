from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "online_cinema",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.timezone = "UTC"


@celery_app.task(name="online_cinema.health_check")  # type: ignore[untyped-decorator]
def celery_health_check() -> str:
    return "ok"
