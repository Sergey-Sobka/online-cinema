from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.services.email import EmailService
from app.services.payments import PaymentService


def get_email_service() -> EmailService:
    settings = get_settings()
    return EmailService(settings=settings)


def get_payment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentService:
    return PaymentService(session, settings, email_service)
