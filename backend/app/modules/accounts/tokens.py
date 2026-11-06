"""One-time email links: verify email (48 h) and reset password (1 h)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.email import send_email
from app.core.errors import AppError
from app.core.security import hash_token, new_token
from app.modules.accounts.models import EmailToken, User

LIFETIME = {"verify": timedelta(hours=48), "reset": timedelta(hours=1)}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def issue(db: Session, user: User, purpose: str) -> str:
    db.execute(
        delete(EmailToken).where(EmailToken.user_id == user.id, EmailToken.purpose == purpose)
    )
    token = new_token()
    db.add(
        EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + LIFETIME[purpose],
        )
    )
    db.commit()
    return token


def consume(db: Session, token: str, purpose: str) -> User:
    row = db.scalar(
        select(EmailToken).where(
            EmailToken.token_hash == hash_token(token), EmailToken.purpose == purpose
        )
    )
    if row is None or row.used_at is not None or _aware(row.expires_at) < datetime.now(UTC):
        raise AppError("token_invalid", 400)
    row.used_at = datetime.now(UTC)
    user = db.get(User, row.user_id)
    if user is None:
        raise AppError("token_invalid", 400)
    return user


def send_verification(db: Session, user: User) -> None:
    link = f"{get_settings().public_base_url}/verify-email?token={issue(db, user, 'verify')}"
    send_email(
        user.email,
        "Confirm your River Valley Auto Sales and Market email",
        f"Hi {user.display_name},\n\nConfirm your email address by opening this link:\n{link}\n\n"
        "The link works for 48 hours. If you didn't create an account, ignore this email.\n",
    )


def send_reset(db: Session, user: User) -> None:
    link = f"{get_settings().public_base_url}/reset-password?token={issue(db, user, 'reset')}"
    send_email(
        user.email,
        "Reset your River Valley Auto Sales and Market password",
        f"Hi {user.display_name},\n\nSomeone (hopefully you) asked to reset your password.\n"
        f"Open this link to choose a new one:\n{link}\n\n"
        "The link works for 1 hour. If you didn't ask, ignore this email — your password won't change.\n",
    )
