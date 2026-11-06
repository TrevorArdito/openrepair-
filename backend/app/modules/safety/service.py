"""Recalls, complaints and TSB index for a vehicle.

Recalls and complaints come from the NHTSA API on demand and are cached for
FRESH_DAYS. TSBs come from NHTSA's bulk files via the importer
(python -m app.importers.nhtsa tsbs)."""

from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.safety.models import (
    Complaint,
    ComplaintVehicle,
    Recall,
    RecallVehicle,
    SafetyFetch,
    Tsb,
    TsbVehicle,
    name_key,
)
from app.modules.safety.nhtsa import NhtsaApi
from app.modules.vehicles.models import Model, Vehicle

FRESH_DAYS = 7


# ---- parsing helpers -------------------------------------------------------


def parse_date(value: Any, *formats: str) -> date | None:
    if not value:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(str(value).strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def clean(value: Any, limit: int | None = None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    return text[:limit] if limit else text


def vehicle_keys(v: Vehicle) -> tuple[str, str, int]:
    return name_key(v.model.make.name), name_key(v.model.name), v.year


# ---- upserts (shared by the API fetch and the importers) -------------------


def _attach(
    db: Session, link_model, fk_name: str, parent_id: int, make: str, model: str, year: int
):
    mk, mo = name_key(make), name_key(model)
    exists = db.scalar(
        select(link_model.id).where(
            getattr(link_model, fk_name) == parent_id,
            link_model.make_key == mk,
            link_model.model_key == mo,
            link_model.year == year,
        )
    )
    if not exists:
        db.add(link_model(**{fk_name: parent_id}, make_key=mk, model_key=mo, year=year))


def upsert_recall(db: Session, row: dict[str, Any], make: str, model: str, year: int) -> bool:
    number = clean(row.get("NHTSACampaignNumber"), 20)
    if not number:
        return False
    recall = db.scalar(select(Recall).where(Recall.campaign_number == number))
    created = recall is None
    if created:
        recall = Recall(campaign_number=number)
        db.add(recall)
    recall.manufacturer = clean(row.get("Manufacturer"), 200)
    recall.component = clean(row.get("Component"), 500)
    recall.summary = clean(row.get("Summary"))
    recall.consequence = clean(row.get("Consequence") or row.get("Conequence"))
    recall.remedy = clean(row.get("Remedy"))
    recall.notes = clean(row.get("Notes"))
    recall.report_date = parse_date(row.get("ReportReceivedDate"), "%d/%m/%Y", "%Y-%m-%d")
    recall.park_it = as_bool(row.get("parkIt"))
    recall.park_outside = as_bool(row.get("parkOutSide"))
    recall.over_the_air = as_bool(row.get("overTheAirUpdate"))
    db.flush()
    _attach(db, RecallVehicle, "recall_id", recall.id, make, model, year)
    return created


def upsert_complaint(db: Session, row: dict[str, Any], make: str, model: str, year: int) -> bool:
    number = clean(row.get("odiNumber"), 20)
    if not number:
        return False
    c = db.scalar(select(Complaint).where(Complaint.odi_number == number))
    created = c is None
    if created:
        c = Complaint(odi_number=number)
        db.add(c)
    c.manufacturer = clean(row.get("manufacturer"), 200)
    c.components = clean(row.get("components"), 500)
    c.summary = clean(row.get("summary"))
    c.crash = as_bool(row.get("crash"))
    c.fire = as_bool(row.get("fire"))
    c.injuries = as_int(row.get("numberOfInjuries"))
    c.deaths = as_int(row.get("numberOfDeaths"))
    c.incident_date = parse_date(row.get("dateOfIncident"), "%m/%d/%Y", "%Y-%m-%d")
    c.filed_date = parse_date(row.get("dateComplaintFiled"), "%m/%d/%Y", "%Y-%m-%d")
    db.flush()
    _attach(db, ComplaintVehicle, "complaint_id", c.id, make, model, year)
    return created


def upsert_tsb(db: Session, rec: dict[str, Any]) -> bool:
    """rec: one parsed line of NHTSA's TSB flat file (see app/importers/nhtsa.py)."""
    tsb = db.scalar(select(Tsb).where(Tsb.nhtsa_id == rec["nhtsa_id"]))
    created = tsb is None
    if created:
        tsb = Tsb(nhtsa_id=rec["nhtsa_id"])
        db.add(tsb)
    tsb.bulletin_number = clean(rec.get("bulletin_number"), 128)
    tsb.bulletin_date = rec.get("bulletin_date")
    tsb.comm_type = clean(rec.get("comm_type"), 60)
    comps = {c for c in (tsb.components or "").split(" | ") if c}
    if rec.get("component"):
        comps.add(clean(rec["component"], 200))
    tsb.components = " | ".join(sorted(comps))[:600] or None
    tsb.summary = clean(rec.get("summary"))
    db.flush()
    _attach(db, TsbVehicle, "tsb_id", tsb.id, rec["make"], rec["model"], rec["year"])
    return created


# ---- on-demand fetch with caching ------------------------------------------


def _fetch_record(db: Session, source: str, mk: str, mo: str, year: int) -> SafetyFetch | None:
    return db.scalar(
        select(SafetyFetch).where(
            SafetyFetch.source == source,
            SafetyFetch.make_key == mk,
            SafetyFetch.model_key == mo,
            SafetyFetch.year == year,
        )
    )


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def refresh(db: Session, nhtsa: NhtsaApi, source: str, v: Vehicle, force: bool = False) -> dict:
    """Make sure we have recent NHTSA data for this vehicle. Returns freshness info."""
    mk, mo, year = vehicle_keys(v)
    record = _fetch_record(db, source, mk, mo, year)
    now = datetime.now(UTC)
    if record and not force and _aware(record.fetched_at) > now - timedelta(days=FRESH_DAYS):
        return {"fetched_at": record.fetched_at, "stale": False}

    make, model = v.model.make.name, v.model.name
    try:
        if source == "recalls":
            for row in nhtsa.recalls(make, model, year):
                upsert_recall(db, row, make, model, year)
        else:
            for row in nhtsa.complaints(make, model, year):
                upsert_complaint(db, row, make, model, year)
    except AppError:
        db.rollback()
        if record:  # NHTSA is down: show what we have, flagged as possibly outdated
            return {"fetched_at": record.fetched_at, "stale": True}
        raise
    if record is None:
        record = SafetyFetch(source=source, make_key=mk, model_key=mo, year=year)
        db.add(record)
    record.fetched_at = now
    db.commit()
    return {"fetched_at": now, "stale": False}


# ---- queries ---------------------------------------------------------------


def _for_vehicle(stmt, link_model, v: Vehicle):
    mk, mo, year = vehicle_keys(v)
    return stmt.join(link_model).where(
        link_model.make_key == mk, link_model.model_key == mo, link_model.year == year
    )


def _search(stmt, q: str | None, *cols):
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(*[func.lower(c).like(like) for c in cols]))
    return stmt


def list_recalls(db: Session, v: Vehicle, q: str | None = None) -> list[Recall]:
    stmt = _for_vehicle(select(Recall), RecallVehicle, v)
    stmt = _search(stmt, q, Recall.component, Recall.summary)
    return list(db.scalars(stmt.order_by(Recall.report_date.desc().nulls_last())).unique())


def page(db: Session, stmt, order, limit: int, offset: int) -> tuple[int, list]:
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(*order).limit(limit).offset(offset)).unique()
    return total, list(rows)


def list_complaints(db: Session, v: Vehicle, q: str | None, limit: int, offset: int):
    stmt = _for_vehicle(select(Complaint), ComplaintVehicle, v)
    stmt = _search(stmt, q, Complaint.components, Complaint.summary)
    return page(
        db, stmt, [Complaint.filed_date.desc().nulls_last(), Complaint.id.desc()], limit, offset
    )


def list_tsbs(db: Session, v: Vehicle, q: str | None, limit: int, offset: int):
    stmt = _for_vehicle(select(Tsb), TsbVehicle, v)
    stmt = _search(stmt, q, Tsb.components, Tsb.summary, Tsb.bulletin_number)
    return page(db, stmt, [Tsb.bulletin_date.desc().nulls_last(), Tsb.id.desc()], limit, offset)


def component_counts(items: Iterable[str | None]) -> dict[str, int]:
    out: dict[str, int] = {}
    for comps in items:
        for c in (comps or "").replace(" | ", ",").split(","):
            c = c.strip()
            if c:
                out[c] = out.get(c, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


# ---- readable recalls ----------------------------------------------------------


def make_model_names(db: Session, v: Vehicle) -> list[str]:
    """Every model name we know for this make, so recall text keeps them capitalized."""
    return list(db.scalars(select(Model.name).where(Model.make_id == v.model.make_id)))


def recall_out(r: Recall, v: Vehicle, models: list[str] | None = None):
    from app.modules.safety.readable import proper_words, readable, recall_group
    from app.modules.safety.schemas import RecallOut

    proper = proper_words(r.manufacturer, v.model.make.name, v.model.name, *(models or ()))
    return RecallOut(
        campaign_number=r.campaign_number,
        manufacturer=r.manufacturer,
        component=readable(r.component, proper),
        summary=readable(r.summary, proper),
        consequence=readable(r.consequence, proper),
        remedy=readable(r.remedy, proper),
        notes=readable(r.notes, proper),
        report_date=r.report_date,
        park_it=r.park_it,
        park_outside=r.park_outside,
        over_the_air=r.over_the_air,
        group=recall_group(r, v.model.make.name, v.engine_displacement_l),
    )


def maker_recall_count(db: Session, v: Vehicle) -> int:
    from app.modules.safety.readable import recall_group

    make = v.model.make.name
    return sum(
        1 for r in list_recalls(db, v) if recall_group(r, make, v.engine_displacement_l) == "maker"
    )


# ---- profile counters ------------------------------------------------------


def _counter(link_model):
    def count(db: Session, v: Vehicle) -> int:
        mk, mo, year = vehicle_keys(v)
        return (
            db.scalar(
                select(func.count()).where(
                    link_model.make_key == mk, link_model.model_key == mo, link_model.year == year
                )
            )
            or 0
        )

    return count


def register_counters() -> None:
    from app.modules.vehicles.service import PROFILE_COUNTERS

    PROFILE_COUNTERS["recalls"] = maker_recall_count  # only the maker's own recalls
    PROFILE_COUNTERS["tsbs"] = _counter(TsbVehicle)
    PROFILE_COUNTERS["complaints"] = _counter(ComplaintVehicle)
