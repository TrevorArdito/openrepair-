"""Shared request dependencies: current user, role checks, CSRF protection."""

import secrets
from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_token
from app.db import get_db
from app.modules.accounts.models import Role, User, UserSession, UserStatus

SESSION_COOKIE = "cc_session"
CSRF_COOKIE = "cc_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if not sess or _aware(sess.expires_at) < datetime.now(UTC):
        return None
    user = sess.user
    if user.status in (UserStatus.suspended, UserStatus.banned):
        return None
    return user


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise AppError("auth_required", 401)
    return user


def require_role(minimum: Role):
    def _dep(user: User = Depends(current_user)) -> User:
        if not user.has_role(minimum):
            raise AppError("forbidden", 403)
        return user

    return _dep


def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check for state-changing requests that carry a session cookie."""
    if request.method in SAFE_METHODS or SESSION_COOKIE not in request.cookies:
        return
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not secrets.compare_digest(cookie, header):
        raise AppError("csrf_failed", 403)
