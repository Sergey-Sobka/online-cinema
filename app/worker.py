import asyncio

from celery import Celery

from app.core.config import get_settings
from app.services.email import EmailService
from app.services.payments import delete_old_pending_payments

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
        "cleanup-expired-refresh-tokens": {
            "task": "online_cinema.cleanup_expired_refresh_tokens",
            "schedule": 3600.0,
        },
        "cleanup-expired-password-reset-tokens": {
            "task": "online_cinema.cleanup_expired_password_reset_tokens",
            "schedule": 3600.0,
        },
        "cleanup-old-payments": {
            "task": "online_cinema.delete_expired_payments",
            "schedule": 7200.0,
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


@celery_app.task(name="online_cinema.cleanup_expired_refresh_tokens")
def cleanup_expired_refresh_tokens() -> int:
    from app.services.auth import cleanup_expired_refresh_tokens as cleanup

    return asyncio.run(cleanup())


@celery_app.task(name="online_cinema.cleanup_expired_password_reset_tokens")
def cleanup_expired_password_reset_tokens() -> int:
    from app.services.auth import cleanup_expired_password_reset_tokens as cleanup

    return asyncio.run(cleanup())


@celery_app.task(name="online_cinema.send_comment_notification")
def send_comment_notification_task(
    recipient_email: str, subject: str, message_body: str
) -> str:
    email_service = EmailService(settings)
    try:
        email_service.send_notification_email(
            recipient=recipient_email, subject=subject, body=message_body
        )
        return f"Notification sent to {recipient_email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@celery_app.task(name="online_cinema.delete_expired_payments")
def task_cleanup_old_payments() -> str:
    count = asyncio.run(delete_old_pending_payments())
    return f"Deleted {count} expired pending payments."
