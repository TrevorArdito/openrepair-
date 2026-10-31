"""Moderator & admin tools for people: pro applications, account status, roles, audit log."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.deps import require_role, verify_csrf
from app.core.errors import AppError, NotFound
from app.db import get_db
from app.modules.accounts.models import ROLE_RANK, ModerationLog, ProRequest, Role, User, UserStatus
from app.modules.accounts.schemas import ReviewIn, RoleIn, StatusIn

router = APIRouter(tags=["moderation"])
MOD = require_role(Role.moderator)


def _user_row(u: User) -> dict:
    return {
        "id": u.id,
        "display_name": u.display_name,
        "email": u.email,
        "role": u.role.value,
        "status": u.status.value,
        "email_verified": u.email_verified_at is not None,
        "created_at": u.created_at,
    }


@router.get("/mod/users")
def users(
    q: str = Query(default="", max_length=100),
    mod: User = Depends(MOD),
    db: Session = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc()).limit(50)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(func.lower(User.email).like(like), func.lower(User.display_name).like(like))
        )
    return [_user_row(u) for u in db.scalars(stmt)]


def _target(db: Session, actor: User, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise NotFound("user_not_found")
    if target.id == actor.id:
        raise AppError("cannot_moderate_self", 409)
    # You can only act on people below your own level (mods can't ban mods/admins).
    if ROLE_RANK[target.role] >= ROLE_RANK[actor.role]:
        raise AppError("forbidden", 403)
    return target


@router.post("/mod/users/{user_id}/status", dependencies=[Depends(verify_csrf)])
def set_status(
    user_id: int, data: StatusIn, mod: User = Depends(MOD), db: Session = Depends(get_db)
):
    target = _target(db, mod, user_id)
    target.status = UserStatus(data.status)
    if target.status in (UserStatus.suspended, UserStatus.banned):
        for s in list(target.sessions):
            db.delete(s)
    log_action(db, mod, f"user_{data.status}", "user", target.id, data.reason)
    db.commit()
    return _user_row(target)


@router.post("/admin/users/{user_id}/role", dependencies=[Depends(verify_csrf)])
def set_role(
    user_id: int,
    data: RoleIn,
    admin: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
):
    target = _target(db, admin, user_id)
    target.role = data.role
    if target.has_role(Role.pro) and target.status == UserStatus.probation:
        target.status = UserStatus.active
    log_action(db, admin, f"role_{data.role.value}", "user", target.id, data.reason)
    db.commit()
    return _user_row(target)


@router.get("/mod/pro-requests")
def pro_requests(mod: User = Depends(MOD), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ProRequest).where(ProRequest.status == "pending").order_by(ProRequest.created_at)
    ).all()
    out = []
    for r in rows:
        u = db.get(User, r.user_id)
        out.append(
            {"id": r.id, "statement": r.statement, "created_at": r.created_at, "user": _user_row(u)}
        )
    return out


@router.post("/mod/pro-requests/{request_id}/{action}", dependencies=[Depends(verify_csrf)])
def review_pro(
    request_id: int,
    action: str,
    data: ReviewIn | None = None,
    mod: User = Depends(MOD),
    db: Session = Depends(get_db),
):
    if action not in ("approve", "reject"):
        raise NotFound()
    r = db.get(ProRequest, request_id)
    if r is None or r.status != "pending":
        raise NotFound("pro_request_not_found")
    user = db.get(User, r.user_id)
    r.status = "approved" if action == "approve" else "rejected"
    r.reviewed_by_id = mod.id
    r.reviewed_at = datetime.now(UTC)
    r.note = data.note if data else None
    if action == "approve" and not user.has_role(Role.pro):
        user.role = Role.pro
        user.status = UserStatus.active
    log_action(db, mod, f"pro_request_{r.status}", "pro_request", r.id, r.note)
    db.commit()
    return {"status": r.status}


@router.get("/mod/log")
def mod_log(mod: User = Depends(MOD), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ModerationLog).order_by(ModerationLog.created_at.desc()).limit(200)
    ).all()
    names = {
        u.id: u.display_name
        for u in db.scalars(select(User).where(User.id.in_({r.actor_id for r in rows})))
    }
    return [
        {
            "id": r.id,
            "actor": names.get(r.actor_id, "Former member"),
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "reason": r.reason,
            "created_at": r.created_at,
        }
        for r in rows
    ]
