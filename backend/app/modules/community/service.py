"""Rules for community content.

- Anyone logged in (and not suspended) can add or edit — like a wiki.
- New accounts are on probation: their first PROBATION_APPROVALS contributions wait
  in the review queue. Verified pros, moderators and admins publish immediately.
- Every save is a full revision. "Verified by a pro" points at one revision; if the
  entry is edited later, readers see "verified on an earlier version".
"""

import statistics
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFound
from app.modules.accounts.models import Role, User, UserStatus
from app.modules.community.kinds import ALWAYS_SAFETY_CRITICAL, validate_data
from app.modules.community.models import (
    Entry,
    EntryDtc,
    EntryRevision,
    EntryStatus,
    EntrySystem,
    EntryVehicle,
    Kind,
    LaborBasis,
    LaborReport,
    Photo,
    Report,
    RevisionStatus,
    RustLevel,
    System,
    Vote,
)
from app.modules.community.schemas import (
    EntryOut,
    EntrySummary,
    Person,
    RevisionOut,
    Tags,
    Verification,
)
from app.modules.vehicles.fitment import fits
from app.modules.vehicles.models import Make, Model, Vehicle

PROBATION_APPROVALS = 3


def now() -> datetime:
    return datetime.now(UTC)


def current_rev(db: Session, entry: Entry) -> EntryRevision | None:
    """The live revision (looked up fresh, never from a cached relationship)."""
    return db.get(EntryRevision, entry.current_revision_id) if entry.current_revision_id else None


def can_publish_directly(user: User) -> bool:
    return user.has_role(Role.pro) or user.status == UserStatus.active


def ensure_can_contribute(user: User) -> None:
    if user.status in (UserStatus.suspended, UserStatus.banned):
        raise AppError("account_disabled", 403)


# ---- validation ----------------------------------------------------------------


def _validate(db: Session, kind: Kind, data: dict, tags: Tags, user: User) -> tuple[dict, dict]:
    try:
        clean = validate_data(kind, data)
    except ValidationError as exc:
        fields = [{"loc": [str(p) for p in e["loc"]], "type": e["type"]} for e in exc.errors()]
        raise AppError("entry_invalid", 422, fields=fields) from exc

    for a in tags.applies_to:
        if a.year_from > a.year_to:
            raise AppError("entry_invalid", 422, fields=[{"loc": ["tags", "applies_to"]}])
        if db.get(Make, a.make_id) is None:
            raise NotFound("make_not_found")
        if a.model_id is not None:
            model = db.get(Model, a.model_id)
            if model is None or model.make_id != a.make_id:
                raise NotFound("model_not_found")
    known = set(db.scalars(select(System.slug).where(System.slug.in_(tags.systems))))
    if unknown := set(tags.systems) - known:
        raise AppError("unknown_system", 422, systems=sorted(unknown))

    # Photos used in steps must be the author's own uploads (or already on this entry).
    for step in clean.get("steps", []):
        if pid := step.get("photo_id"):
            photo = db.get(Photo, pid)
            if photo is None or (photo.uploader_id != user.id and photo.entry_id is None):
                raise AppError("photo_not_found", 422, photo_id=pid)
    return clean, tags.model_dump(mode="json")


def _attach_photos(db: Session, entry: Entry, data: dict) -> None:
    for step in data.get("steps", []):
        if pid := step.get("photo_id"):
            photo = db.get(Photo, pid)
            if photo and photo.entry_id is None:
                photo.entry_id = entry.id


# ---- applying the current revision ------------------------------------------------


def _apply_current(db: Session, entry: Entry, rev: EntryRevision) -> None:
    entry.current_revision_id = rev.id
    entry.title = rev.title
    entry.status = EntryStatus.published if entry.status != EntryStatus.hidden else entry.status
    db.execute(delete(EntryVehicle).where(EntryVehicle.entry_id == entry.id))
    db.execute(delete(EntrySystem).where(EntrySystem.entry_id == entry.id))
    db.execute(delete(EntryDtc).where(EntryDtc.entry_id == entry.id))
    tags = rev.tags
    for a in tags.get("applies_to", []):
        db.add(EntryVehicle(entry_id=entry.id, **a))
    systems = db.scalars(select(System).where(System.slug.in_(tags.get("systems", [])))).all()
    for s in systems:
        db.add(EntrySystem(entry_id=entry.id, system_id=s.id))
    for code in tags.get("dtcs", []):
        db.add(EntryDtc(entry_id=entry.id, code=code))
    entry.safety_critical = entry.kind in ALWAYS_SAFETY_CRITICAL or any(
        s.safety_critical for s in systems
    )
    _attach_photos(db, entry, rev.data)


def _maybe_promote(db: Session, author_id: int | None) -> None:
    """After enough approved contributions, a new account leaves probation."""
    if author_id is None:
        return
    user = db.get(User, author_id)
    if user is None or user.status != UserStatus.probation:
        return
    approved = db.scalar(
        select(func.count())
        .select_from(EntryRevision)
        .where(
            EntryRevision.author_id == author_id,
            EntryRevision.status == RevisionStatus.approved,
        )
    )
    if (approved or 0) >= PROBATION_APPROVALS:
        user.status = UserStatus.active


# ---- create / edit / review ----------------------------------------------------


def create_entry(db: Session, user: User, kind: Kind, title: str, data: dict, tags: Tags, summary):
    ensure_can_contribute(user)
    clean, tag_data = _validate(db, kind, data, tags, user)
    direct = can_publish_directly(user)
    entry = Entry(kind=kind, title=title, created_by_id=user.id, status=EntryStatus.pending)
    db.add(entry)
    db.flush()
    rev = EntryRevision(
        entry_id=entry.id,
        number=1,
        author_id=user.id,
        title=title,
        data=clean,
        tags=tag_data,
        edit_summary=summary or "Created",
        status=RevisionStatus.approved if direct else RevisionStatus.pending,
    )
    db.add(rev)
    db.flush()
    if direct:
        _apply_current(db, entry, rev)
    else:
        entry.current_revision_id = None
        _attach_photos(db, entry, clean)
    db.commit()
    return entry


def _latest_number(db: Session, entry: Entry) -> int:
    return db.scalar(
        select(func.max(EntryRevision.number)).where(EntryRevision.entry_id == entry.id)
    )


def edit_entry(db: Session, user: User, entry: Entry, base: int, title, data, tags: Tags, summary):
    ensure_can_contribute(user)
    if entry.status == EntryStatus.hidden and not user.has_role(Role.moderator):
        raise NotFound("entry_not_found")
    current = current_rev(db, entry)
    current_no = current.number if current else 0
    if base != current_no:
        raise AppError("edit_conflict", 409, current_revision=current_no)
    clean, tag_data = _validate(db, entry.kind, data, tags, user)
    direct = can_publish_directly(user)
    rev = EntryRevision(
        entry_id=entry.id,
        number=_latest_number(db, entry) + 1,
        author_id=user.id,
        title=title,
        data=clean,
        tags=tag_data,
        edit_summary=summary,
        status=RevisionStatus.approved if direct else RevisionStatus.pending,
    )
    db.add(rev)
    db.flush()
    if direct:
        _apply_current(db, entry, rev)
    db.commit()
    return rev


def review_revision(db: Session, mod: User, rev: EntryRevision, approve: bool) -> None:
    if rev.status != RevisionStatus.pending:
        raise AppError("revision_not_pending", 409)
    rev.status = RevisionStatus.approved if approve else RevisionStatus.rejected
    rev.reviewed_by_id = mod.id
    rev.reviewed_at = now()
    entry = rev.entry
    if approve:
        current = current_rev(db, entry)
        if current is None or rev.number > current.number:
            _apply_current(db, entry, rev)
        db.flush()
        _maybe_promote(db, rev.author_id)
    elif entry.current_revision_id is None:
        entry.status = EntryStatus.hidden  # a brand-new entry that was rejected
    db.commit()


def revert(db: Session, user: User, entry: Entry, number: int) -> EntryRevision:
    old = db.scalar(
        select(EntryRevision).where(
            EntryRevision.entry_id == entry.id, EntryRevision.number == number
        )
    )
    if old is None or old.status != RevisionStatus.approved:
        raise NotFound("revision_not_found")
    current = current_rev(db, entry)
    current_no = current.number if current else 0
    return edit_entry(
        db, user, entry, current_no, old.title, old.data, Tags(**old.tags),
        f"Reverted to version {number}",
    )  # fmt: skip


def verify(db: Session, pro: User, entry: Entry) -> None:
    if entry.current_revision_id is None:
        raise AppError("entry_not_published", 409)
    entry.verified_revision_id = entry.current_revision_id
    entry.verified_by_id = pro.id
    entry.verified_at = now()
    db.commit()


def unverify(db: Session, entry: Entry) -> None:
    entry.verified_revision_id = entry.verified_by_id = entry.verified_at = None
    db.commit()


def vote(db: Session, user: User, entry: Entry, value: int) -> int:
    if entry.created_by_id == user.id:
        raise AppError("cannot_vote_own", 409)
    existing = db.scalar(select(Vote).where(Vote.entry_id == entry.id, Vote.user_id == user.id))
    if value == 0 and existing:
        db.delete(existing)
    elif value and existing:
        existing.value = value
    elif value:
        db.add(Vote(entry_id=entry.id, user_id=user.id, value=value))
    db.flush()
    entry.score = db.scalar(
        select(func.coalesce(func.sum(Vote.value), 0)).where(Vote.entry_id == entry.id)
    )
    db.commit()
    return entry.score


def report(db: Session, user: User, entry: Entry, reason, details) -> Report:
    open_by_me = db.scalar(
        select(Report.id).where(
            Report.entry_id == entry.id, Report.reporter_id == user.id, Report.status == "open"
        )
    )
    if open_by_me:
        raise AppError("already_reported", 409)
    r = Report(
        entry_id=entry.id,
        revision_id=entry.current_revision_id,
        reporter_id=user.id,
        reason=reason,
        details=details,
    )
    db.add(r)
    db.commit()
    return r


def add_labor_report(db: Session, user: User, entry: Entry, basis, hours, rust, note) -> None:
    if entry.kind != Kind.labor_time:
        raise AppError("not_labor_entry", 409)
    ensure_can_contribute(user)
    db.add(
        LaborReport(
            entry_id=entry.id, user_id=user.id, basis=basis, hours=hours, rust=rust, note=note
        )
    )
    db.commit()


def labor_summary(db: Session, entry: Entry) -> dict:
    """Median/min/max hours for each source (warranty, flat-rate, pro, DIY) x rust level."""
    rows = db.execute(
        select(LaborReport.basis, LaborReport.rust, LaborReport.hours).where(
            LaborReport.entry_id == entry.id
        )
    ).all()
    out: dict = {}
    for basis in LaborBasis:
        out[basis.value] = {}
        for rust in RustLevel:
            hrs = [h for b, r, h in rows if b == basis and r == rust]
            out[basis.value][rust.value] = (
                {
                    "reports": len(hrs),
                    "median": round(statistics.median(hrs), 2),
                    "min": min(hrs),
                    "max": max(hrs),
                }  # fmt: skip
                if hrs
                else {"reports": 0}
            )
    return out


# ---- reading -----------------------------------------------------------------


def person(db: Session, user_id: int | None) -> Person:
    user = db.get(User, user_id) if user_id else None
    if user is None:
        return Person(id=None, display_name="Former member")
    return Person(id=user.id, display_name=user.display_name, role=user.role.value)


def revision_out(db: Session, rev: EntryRevision) -> RevisionOut:
    return RevisionOut(
        id=rev.id,
        number=rev.number,
        title=rev.title,
        data=rev.data,
        tags=rev.tags,
        edit_summary=rev.edit_summary,
        status=rev.status.value,
        author=person(db, rev.author_id),
        created_at=rev.created_at,
    )


def tags_display(db: Session, tags: dict) -> dict:
    """Turn ids into names for display."""
    applies = []
    for a in tags.get("applies_to", []):
        make = db.get(Make, a["make_id"])
        model = db.get(Model, a["model_id"]) if a.get("model_id") else None
        applies.append(
            {**a, "make": make.name if make else "?", "model": model.name if model else None}
        )
    return {"applies_to": applies, "systems": tags.get("systems", []), "dtcs": tags.get("dtcs", [])}


def get_entry(db: Session, entry_id: int, viewer: User | None) -> Entry:
    entry = db.get(Entry, entry_id)
    if entry is None:
        raise NotFound("entry_not_found")
    is_mod = viewer is not None and viewer.has_role(Role.moderator)
    is_author = viewer is not None and entry.created_by_id == viewer.id
    if entry.status == EntryStatus.hidden and not is_mod:
        raise NotFound("entry_not_found")
    if entry.status == EntryStatus.pending and not (is_mod or is_author):
        raise NotFound("entry_not_found")
    return entry


def entry_out(db: Session, entry: Entry, viewer: User | None) -> EntryOut:
    db.refresh(entry)
    rev = current_rev(db, entry)
    if rev is None:  # pending first version: only the author/mods get here
        rev = db.scalar(
            select(EntryRevision)
            .where(EntryRevision.entry_id == entry.id)
            .order_by(EntryRevision.number.desc())
        )
    if entry.verified_revision_id is None:
        verification = Verification(state="none")
    else:
        vrev = db.get(EntryRevision, entry.verified_revision_id)
        verification = Verification(
            state="verified"
            if entry.verified_revision_id == entry.current_revision_id
            else "verified_older",
            by=person(db, entry.verified_by_id),
            at=entry.verified_at,
            revision_number=vrev.number if vrev else None,
        )
    my_vote = 0
    if viewer:
        my_vote = (
            db.scalar(
                select(Vote.value).where(Vote.entry_id == entry.id, Vote.user_id == viewer.id)
            )
            or 0
        )
    open_reports = db.scalar(
        select(func.count())
        .select_from(Report)
        .where(Report.entry_id == entry.id, Report.status == "open")
    )
    pending = db.scalar(
        select(func.count())
        .select_from(EntryRevision)
        .where(EntryRevision.entry_id == entry.id, EntryRevision.status == RevisionStatus.pending)
    )
    return EntryOut(
        id=entry.id,
        kind=entry.kind,
        status=entry.status.value,
        title=entry.title,
        score=entry.score,
        my_vote=my_vote,
        safety_critical=entry.safety_critical or entry.kind in ALWAYS_SAFETY_CRITICAL,
        verification=verification,
        open_reports=open_reports or 0,
        pending_revisions=pending or 0,
        revision=revision_out(db, rev) if rev else None,
        tags_display=tags_display(db, rev.tags) if rev else {},
        labor=labor_summary(db, entry) if entry.kind == Kind.labor_time else None,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _summary_text(db: Session, entry: Entry) -> str | None:
    rev = current_rev(db, entry)
    if not rev:
        return None
    d = rev.data
    return (
        d.get("summary")
        or d.get("component")
        or d.get("job")
        or d.get("name")
        or d.get("part_name")
    )


def vehicle_filter(v: Vehicle):
    """Entries that apply to this vehicle (make, model, year range, engine size)."""
    return select(EntryVehicle.entry_id).where(fits(EntryVehicle, v))


def list_entries(
    db: Session,
    *,
    vehicle: Vehicle | None = None,
    kinds: list[Kind] | None = None,
    system: str | None = None,
    dtc: str | None = None,
    q: str | None = None,
    include_generic: bool = True,
    sort: str = "top",
    limit: int = 25,
    offset: int = 0,
) -> tuple[int, list[EntrySummary]]:
    stmt = select(Entry).where(Entry.status == EntryStatus.published)
    has_vehicle_tags = (
        select(EntryVehicle.entry_id).where(EntryVehicle.entry_id == Entry.id).exists()
    )
    if vehicle is not None:
        conds = [Entry.id.in_(vehicle_filter(vehicle))]
        if include_generic:
            conds.append(~has_vehicle_tags)
        stmt = stmt.where(or_(*conds))
    if kinds:
        stmt = stmt.where(Entry.kind.in_(kinds))
    if system:
        sys_ids = select(System.id).where(
            or_(System.slug == system, System.slug.startswith(f"{system}."))
        )
        stmt = stmt.where(
            Entry.id.in_(select(EntrySystem.entry_id).where(EntrySystem.system_id.in_(sys_ids)))
        )
    if dtc:
        stmt = stmt.where(Entry.id.in_(select(EntryDtc.entry_id).where(EntryDtc.code == dtc)))
    if q:
        stmt = stmt.where(func.lower(Entry.title).like(f"%{q.strip().lower()}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = (
        [Entry.score.desc(), Entry.updated_at.desc()]
        if sort == "top"
        else [Entry.updated_at.desc()]
    )
    if vehicle is not None:  # vehicle-specific entries first, then general ones
        order.insert(0, has_vehicle_tags.desc())
    rows = db.scalars(stmt.order_by(*order).limit(limit).offset(offset)).all()
    generic_ids = set()
    if rows:
        tagged = set(
            db.scalars(
                select(EntryVehicle.entry_id).where(EntryVehicle.entry_id.in_([e.id for e in rows]))
            )
        )
        generic_ids = {e.id for e in rows} - tagged
    items = [
        EntrySummary(
            id=e.id,
            kind=e.kind,
            title=e.title,
            score=e.score,
            verified=e.verified_revision_id is not None
            and e.verified_revision_id == e.current_revision_id,
            safety_critical=e.safety_critical,
            generic=e.id in generic_ids,
            summary=(_summary_text(db, e) or "")[:200] or None,
            updated_at=e.updated_at,
        )
        for e in rows
    ]
    return total, items


# ---- hooks into other modules --------------------------------------------------


def related_for_dtc(db: Session, code: str) -> list[dict]:
    _, items = list_entries(db, dtc=code, limit=20)
    return [{"id": i.id, "title": i.title, "kind": i.kind.value} for i in items]


def _count(kinds: list[Kind]):
    def counter(db: Session, v: Vehicle) -> int:
        total, _ = list_entries(db, vehicle=v, kinds=kinds, include_generic=False, limit=1)
        return total

    return counter


def register_hooks() -> None:
    from app.modules.dtc.service import RELATED_FINDERS
    from app.modules.vehicles.service import PROFILE_COUNTERS

    if related_for_dtc not in RELATED_FINDERS:
        RELATED_FINDERS.append(related_for_dtc)
    PROFILE_COUNTERS["guides"] = _count([Kind.procedure])
    PROFILE_COUNTERS["specs"] = _count(
        [Kind.torque_spec, Kind.fluid_capacity, Kind.spec, Kind.part_note, Kind.labor_time]
    )


def seed_systems(db: Session) -> int:
    from app.modules.community.systems import SYSTEM_TREE

    by_slug = {s.slug: s for s in db.scalars(select(System))}
    for i, (slug, parent, critical) in enumerate(SYSTEM_TREE):
        s = by_slug.get(slug) or System(slug=slug)
        s.parent_id = by_slug[parent].id if parent else None
        s.safety_critical = critical
        s.sort = i
        db.add(s)
        db.flush()
        by_slug[slug] = s
    return len(SYSTEM_TREE)
