from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.deps import current_user, optional_user, require_role, verify_csrf
from app.core.errors import NotFound
from app.core.ratelimit import rate_limit
from app.db import get_db
from app.modules.accounts.models import Role, User
from app.modules.community import photos, service
from app.modules.community.models import EntryRevision, Kind, Photo, System
from app.modules.community.schemas import (
    EntryEdit,
    EntryIn,
    EntryList,
    EntryOut,
    LaborReportIn,
    PhotoOut,
    ReportIn,
    RevisionOut,
    SystemOut,
    VoteIn,
)
from app.modules.dtc.structure import validate_code
from app.modules.vehicles.models import Vehicle

router = APIRouter(tags=["community"])
service.register_hooks()
WRITE = [Depends(verify_csrf), Depends(rate_limit("contribute", 60, 3600))]


@router.get("/systems", response_model=list[SystemOut])
def systems(db: Session = Depends(get_db)):
    rows = db.scalars(select(System).order_by(System.sort)).all()
    by_id = {s.id: s.slug for s in rows}
    return [
        SystemOut(slug=s.slug, parent=by_id.get(s.parent_id), safety_critical=s.safety_critical)
        for s in rows
    ]


@router.get("/entries", response_model=EntryList)
def list_entries(
    vehicle_id: int | None = None,
    kind: list[Kind] = Query(default=[]),
    system: str | None = Query(default=None, max_length=60),
    dtc: str | None = Query(default=None, max_length=8),
    q: str | None = Query(default=None, max_length=100),
    include_generic: bool = True,
    sort: str = Query(default="top", pattern="^(top|new)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    vehicle = None
    if vehicle_id is not None:
        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle is None:
            raise NotFound("vehicle_not_found")
    total, items = service.list_entries(
        db,
        vehicle=vehicle,
        kinds=kind or None,
        system=system,
        dtc=validate_code(dtc) if dtc else None,
        q=q,
        include_generic=include_generic,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return EntryList(total=total, items=items)


@router.post("/entries", response_model=EntryOut, status_code=201, dependencies=WRITE)
def create(data: EntryIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = service.create_entry(
        db, user, data.kind, data.title, data.data, data.tags, data.edit_summary
    )
    return service.entry_out(db, entry, user)


@router.get("/entries/{entry_id}", response_model=EntryOut)
def get(entry_id: int, viewer: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    return service.entry_out(db, service.get_entry(db, entry_id, viewer), viewer)


@router.post("/entries/{entry_id}/revisions", response_model=EntryOut, dependencies=WRITE)
def edit(
    entry_id: int,
    data: EntryEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    entry = service.get_entry(db, entry_id, user)
    service.edit_entry(
        db, user, entry, data.base_revision, data.title, data.data, data.tags, data.edit_summary
    )
    return service.entry_out(db, entry, user)


@router.get("/entries/{entry_id}/revisions", response_model=list[RevisionOut])
def history(
    entry_id: int, viewer: User | None = Depends(optional_user), db: Session = Depends(get_db)
):
    entry = service.get_entry(db, entry_id, viewer)
    is_mod = viewer is not None and viewer.has_role(Role.moderator)
    revs = [
        r
        for r in entry.revisions
        if is_mod or r.status.value == "approved" or r.author_id == getattr(viewer, "id", None)
    ]
    return [service.revision_out(db, r) for r in reversed(revs)]


@router.post(
    "/entries/{entry_id}/revert/{number}",
    response_model=EntryOut,
    dependencies=[Depends(verify_csrf)],
)
def revert(
    entry_id: int,
    number: int,
    user: User = Depends(require_role(Role.pro)),
    db: Session = Depends(get_db),
):
    entry = service.get_entry(db, entry_id, user)
    service.revert(db, user, entry, number)
    return service.entry_out(db, entry, user)


@router.post(
    "/entries/{entry_id}/verify", response_model=EntryOut, dependencies=[Depends(verify_csrf)]
)
def verify(
    entry_id: int, user: User = Depends(require_role(Role.pro)), db: Session = Depends(get_db)
):
    entry = service.get_entry(db, entry_id, user)
    service.verify(db, user, entry)
    return service.entry_out(db, entry, user)


@router.post("/entries/{entry_id}/vote", response_model=EntryOut, dependencies=WRITE)
def vote(
    entry_id: int, data: VoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    entry = service.get_entry(db, entry_id, user)
    service.vote(db, user, entry, data.value)
    return service.entry_out(db, entry, user)


@router.post("/entries/{entry_id}/reports", status_code=201, dependencies=WRITE)
def report(
    entry_id: int, data: ReportIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    entry = service.get_entry(db, entry_id, user)
    r = service.report(db, user, entry, data.reason, data.details, data.section)
    return {"id": r.id, "status": r.status}


@router.post("/entries/{entry_id}/labor", response_model=EntryOut, dependencies=WRITE)
def add_labor(
    entry_id: int,
    data: LaborReportIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    entry = service.get_entry(db, entry_id, user)
    service.add_labor_report(db, user, entry, data.basis, data.hours, data.rust, data.note)
    return service.entry_out(db, entry, user)


# ---- photos -------------------------------------------------------------------


@router.post(
    "/photos",
    response_model=PhotoOut,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("photos", 60, 3600))],
)
async def upload_photo(
    file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)
):
    service.ensure_can_contribute(user)
    raw = await file.read(photos.MAX_BYTES + 1)
    key, w, h, data = photos.process_upload(raw)
    photo = Photo(uploader_id=user.id, storage_key=key, width=w, height=h)
    db.add(photo)
    db.flush()
    photos.store(db, photo, data)
    db.commit()
    return PhotoOut(id=photo.id, url=f"/api/v1/photos/{photo.id}", width=w, height=h)


@router.get("/photos/{photo_id}")
def get_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if photo is None or photo.status != "visible":
        raise NotFound("photo_not_found")
    data = photos.load(db, photo)
    if data is None:
        raise NotFound("photo_not_found")
    return Response(content=data, media_type="image/webp",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})  # fmt: skip


# ---- moderation (review queue + reports) ----------------------------------------

mod = APIRouter(prefix="/mod", tags=["moderation"])


@mod.get("/queue")
def queue(user: User = Depends(require_role(Role.moderator)), db: Session = Depends(get_db)):
    from app.modules.community.models import Report

    pending = db.scalars(
        select(EntryRevision)
        .where(EntryRevision.status == "pending")
        .order_by(EntryRevision.created_at)
    ).all()
    reports = db.scalars(
        select(Report).where(Report.status == "open").order_by(Report.created_at)
    ).all()
    return {
        "pending_revisions": [
            {
                **service.revision_out(db, r).model_dump(mode="json"),
                "entry_id": r.entry_id,
                "kind": r.entry.kind,
            }
            for r in pending
        ],
        "reports": [
            {
                "id": r.id,
                "entry_id": r.entry_id,
                "reason": r.reason.value,
                "details": r.details,
                "reporter": service.person(db, r.reporter_id).model_dump(),
                "created_at": r.created_at,
            }
            for r in reports
        ],
    }


@mod.post("/revisions/{revision_id}/{action}", dependencies=[Depends(verify_csrf)])
def review(
    revision_id: int,
    action: str,
    user: User = Depends(require_role(Role.moderator)),
    db: Session = Depends(get_db),
):
    if action not in ("approve", "reject"):
        raise NotFound()
    rev = db.get(EntryRevision, revision_id)
    if rev is None:
        raise NotFound("revision_not_found")
    service.review_revision(db, user, rev, approve=action == "approve")
    log_action(db, user, f"revision_{action}", "revision", rev.id)
    db.commit()
    return {"status": rev.status.value}


@mod.post("/reports/{report_id}/{action}", dependencies=[Depends(verify_csrf)])
def resolve_report(
    report_id: int,
    action: str,
    note: str | None = Query(default=None, max_length=500),
    user: User = Depends(require_role(Role.moderator)),
    db: Session = Depends(get_db),
):
    from app.modules.community.models import Report

    if action not in ("resolve", "dismiss"):
        raise NotFound()
    r = db.get(Report, report_id)
    if r is None:
        raise NotFound("report_not_found")
    r.status = "resolved" if action == "resolve" else "dismissed"
    r.resolved_by_id = user.id
    r.resolved_at = service.now()
    r.resolution_note = note
    log_action(db, user, f"report_{r.status}", "report", r.id, note)
    db.commit()
    return {"status": r.status}


@mod.post("/entries/{entry_id}/{action}", dependencies=[Depends(verify_csrf)])
def hide_restore(
    entry_id: int,
    action: str,
    user: User = Depends(require_role(Role.moderator)),
    db: Session = Depends(get_db),
):
    from app.modules.community.models import EntryStatus

    if action not in ("hide", "restore", "unverify"):
        raise NotFound()
    entry = service.get_entry(db, entry_id, user)
    log_action(db, user, f"entry_{action}", "entry", entry.id)
    if action == "unverify":
        service.unverify(db, entry)
    else:
        entry.status = (
            EntryStatus.hidden
            if action == "hide"
            else (EntryStatus.published if entry.current_revision_id else EntryStatus.pending)
        )
        db.commit()
    return {"status": entry.status.value}
