import smtplib
from email.message import EmailMessage

from app.core.config import Settings


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

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as smtp:
            if self._settings.smtp_username and self._settings.smtp_password:
                smtp.login(self._settings.smtp_username, self._settings.smtp_password)
            smtp.send_message(message)

    def _build_activation_link(self, token: str) -> str:
        if self._settings.activation_url_base is not None:
            base_url = str(self._settings.activation_url_base).rstrip("/")
            return f"{base_url}?token={token}"
        return f"/api/v1/auth/activate?token={token}"
