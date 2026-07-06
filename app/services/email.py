import smtplib
from email.message import EmailMessage

from app.core.config import Settings


class EmailDeliveryError(Exception):
    pass


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send_activation_email(self, recipient: str, token: str) -> None:
        activation_link = self._build_activation_link(token)
        message = EmailMessage()
        message["Subject"] = "Activate your Online Cinema account"
        message["From"] = self._settings.email_from
        message["To"] = recipient
        message.set_content(
            "Welcome to Online Cinema.\n\n"
            f"Activate your account using this link: {activation_link}\n\n"
            "This link is valid for 24 hours."
        )

        self._send_message(message)

    def send_password_reset_email(self, recipient: str, token: str) -> None:
        reset_link = self._build_password_reset_link(token)
        message = EmailMessage()
        message["Subject"] = "Reset your password"
        message["From"] = self._settings.email_from
        message["To"] = recipient
        message.set_content(
            "Use this link to reset your password:\n\n"
            f"{reset_link}\n\n"
            "This link is valid for a limited time."
        )

        self._send_message(message)

    def _send_message(self, message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(
                host=self._settings.smtp_host,
                port=self._settings.smtp_port,
            ) as smtp:
                if self._settings.smtp_username and self._settings.smtp_password:
                    smtp.login(
                        user=self._settings.smtp_username,
                        password=self._settings.smtp_password,
                    )
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("Email could not be sent.") from exc

    def _build_activation_link(self, token: str) -> str:
        if self._settings.activation_url_base is not None:
            base_url = str(self._settings.activation_url_base).rstrip("/")
            return f"{base_url}?token={token}"
        return f"/api/v1/auth/activate?token={token}"

    def _build_password_reset_link(self, token: str) -> str:
        if self._settings.password_reset_url_base is not None:
            base_url = str(self._settings.password_reset_url_base).rstrip("/")
            return f"{base_url}?token={token}"
        return f"/api/v1/auth/password/reset?token={token}"
