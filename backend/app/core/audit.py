from sqlalchemy.orm import Session

from app.modules.accounts.models import ModerationLog, User


def log_action(
    db: Session,
    actor: User,
    action: str,
    target_type: str,
    target_id: int,
    reason: str | None = None,
):
    """Record a moderator/admin action. Caller commits."""
    db.add(
        ModerationLog(
            actor_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
        )
    )
