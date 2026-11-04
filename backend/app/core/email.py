"""Sending email. Development prints messages to the log; production uses any SMTP
provider (free tiers exist — see docs/HOSTING.md). Credentials come from env vars."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger("chrystalclear.email")
OUTBOX: list[EmailMessage] = []  # console backend keeps recent messages (used by tests)


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if settings.email_backend == "smtp" and settings.smtp_host:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls(context=context)
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return

    OUTBOX.append(msg)
    del OUTBOX[:-50]
    log.warning("EMAIL (console backend) to=%s subject=%s\n%s", to, subject, body)
