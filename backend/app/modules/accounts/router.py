from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import CSRF_COOKIE, SESSION_COOKIE, current_user, optional_user, verify_csrf
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.core.security import (
    DUMMY_HASH,
    hash_password,
    hash_token,
    new_token,
    password_needs_rehash,
    verify_password,
)
from app.db import get_db
from app.modules.accounts import tokens
from app.modules.accounts.models import ProRequest, Role, User, UserSession, UserStatus
from app.modules.accounts.schemas import (
    ForgotIn,
    LoginIn,
    MeOut,
    MeUpdate,
    ProRequestIn,
    RegisterIn,
    ResetIn,
    TokenIn,
)

router = APIRouter(tags=["accounts"])


def me_out(user: User) -> MeOut:
    out = MeOut.model_validate(user)
    out.email_verified = user.email_verified_at is not None
    return out


def _start_session(db: Session, user: User, response: Response) -> None:
    settings = get_settings()
    if user.email.lower() in settings.admin_email_set and user.role != Role.admin:
        user.role = Role.admin  # owner bootstrap via ADMIN_EMAILS (no shell on free hosts)
        user.status = UserStatus.active
    token = new_token()
    expires = datetime.now(UTC) + timedelta(days=settings.session_days)
    db.add(UserSession(token_hash=hash_token(token), user_id=user.id, expires_at=expires))
    user.last_login_at = datetime.now(UTC)
    db.commit()
    max_age = settings.session_days * 86400
    secure = settings.is_production
    response.set_cookie(
        SESSION_COOKIE, token, max_age=max_age, httponly=True, secure=secure, samesite="lax"
    )
    # Readable by our JS, echoed back in a header to prove the request came from our page.
    response.set_cookie(
        CSRF_COOKIE, new_token(), max_age=max_age, httponly=False, secure=secure, samesite="lax"
    )


@router.post(
    "/auth/register",
    response_model=MeOut,
    status_code=201,
    dependencies=[Depends(rate_limit("register", 5, 3600))],
)
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if data.website:  # honeypot tripped
        raise AppError("registration_rejected", 400)
    if not data.accept_terms:
        raise AppError("terms_not_accepted", 400)
    email = data.email.lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise AppError("email_taken", 409)
    user = User(
        email=email, password_hash=hash_password(data.password), display_name=data.display_name
    )
    db.add(user)
    db.commit()
    _start_session(db, user, response)
    tokens.send_verification(db, user)
    return me_out(user)


@router.post(
    "/auth/login", response_model=MeOut, dependencies=[Depends(rate_limit("login", 10, 300))]
)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if user is None:
        verify_password(DUMMY_HASH, data.password)  # same timing either way
        raise AppError("invalid_credentials", 401)
    if not verify_password(user.password_hash, data.password):
        raise AppError("invalid_credentials", 401)
    if user.status.value in ("suspended", "banned"):
        raise AppError("account_disabled", 403)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    _start_session(db, user, response)
    return me_out(user)


@router.post("/auth/logout", status_code=204, dependencies=[Depends(verify_csrf)])
def logout(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Logging out ends every session for this user (simple + safe on shared shop devices).
    for s in list(user.sessions):
        db.delete(s)
    db.commit()
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)


@router.get("/auth/session")
def session(user: User | None = Depends(optional_user)):
    """Who is logged in (or null). Unlike /me this never answers 401."""
    return {"user": me_out(user).model_dump() if user else None}


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user)):
    return me_out(user)


@router.patch("/me", response_model=MeOut, dependencies=[Depends(verify_csrf)])
def update_me(data: MeUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return me_out(user)


# Optional modules (e.g. marketplace) add their data to "download my data" here.
EXPORT_HOOKS: list = []


@router.get("/me/export")
def export_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Everything we store about you, as JSON (privacy: you can always take your data)."""
    from app.modules.vehicles.models import GarageVehicle  # local import avoids a cycle

    garage = db.scalars(select(GarageVehicle).where(GarageVehicle.user_id == user.id)).all()
    out = {
        "account": me_out(user).model_dump(),
        "created_at": user.created_at,
        "garage": [
            {"vehicle_id": g.vehicle_id, "vin": g.vin, "nickname": g.nickname, "notes": g.notes}
            for g in garage
        ],
    }
    for hook in EXPORT_HOOKS:
        out.update(hook(db, user))
    return out


@router.delete("/me", status_code=204, dependencies=[Depends(verify_csrf)])
def delete_me(
    response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.delete(user)
    db.commit()
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)


# ---- email verification & password reset ----------------------------------------


@router.post(
    "/auth/verify-email/request",
    status_code=202,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("verify_email", 5, 3600))],
)
def resend_verification(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.email_verified_at is None:
        tokens.send_verification(db, user)
    return {"status": "sent"}


@router.post(
    "/auth/verify-email",
    response_model=MeOut,
    dependencies=[Depends(rate_limit("verify", 20, 3600))],
)
def verify_email(data: TokenIn, db: Session = Depends(get_db)):
    user = tokens.consume(db, data.token, "verify")
    user.email_verified_at = user.email_verified_at or datetime.now(UTC)
    db.commit()
    return me_out(user)


@router.post(
    "/auth/forgot-password", status_code=202, dependencies=[Depends(rate_limit("forgot", 5, 3600))]
)
def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    """Always answers the same way, so nobody can use it to find out who has an account."""
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if user is not None and user.status.value not in ("banned",):
        tokens.send_reset(db, user)
    return {"status": "sent_if_account_exists"}


@router.post(
    "/auth/reset-password", status_code=204, dependencies=[Depends(rate_limit("reset", 10, 3600))]
)
def reset_password(data: ResetIn, response: Response, db: Session = Depends(get_db)):
    user = tokens.consume(db, data.token, "reset")
    user.password_hash = hash_password(data.password)
    user.email_verified_at = user.email_verified_at or datetime.now(UTC)  # they proved they own it
    for s in list(user.sessions):  # log out everywhere
        db.delete(s)
    db.commit()
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)


# ---- "verified pro" applications ---------------------------------------------------


@router.get("/pro-requests/mine")
def my_pro_request(user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.scalar(
        select(ProRequest).where(ProRequest.user_id == user.id).order_by(ProRequest.id.desc())
    )
    return (
        None
        if r is None
        else {"id": r.id, "status": r.status, "note": r.note, "created_at": r.created_at}
    )


@router.post(
    "/pro-requests",
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("pro_request", 3, 86400))],
)
def request_pro(
    data: ProRequestIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if user.has_role(Role.pro):
        raise AppError("already_pro", 409)
    pending = db.scalar(
        select(ProRequest.id).where(ProRequest.user_id == user.id, ProRequest.status == "pending")
    )
    if pending:
        raise AppError("pro_request_pending", 409)
    r = ProRequest(user_id=user.id, statement=data.statement)
    db.add(r)
    db.commit()
    return {"id": r.id, "status": r.status}
