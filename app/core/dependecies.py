from app.services.email import EmailService
from app.core.config import get_settings


def get_email_service() -> EmailService:
    settings = get_settings()
    return EmailService(settings=settings)
