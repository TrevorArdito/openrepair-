"""One search box across everything: VINs, trouble codes, vehicles, guides & specs,
and — when searching within a vehicle — its recalls and TSBs.

Matching is "every word must appear" (case-insensitive). On Postgres the text columns
have trigram (pg_trgm) indexes so this stays fast as data grows."""

import re
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.community.models import Entry, EntryStatus, EntryVehicle
from app.modules.community.service import vehicle_filter
from app.modules.dtc import service as dtc_service
from app.modules.dtc.models import Dtc
from app.modules.dtc.structure import CODE_RE, normalize_code
from app.modules.safety import service as safety
from app.modules.safety.models import Recall, name_key
from app.modules.vehicles.models import Make, Model, ModelYear, Vehicle
from app.modules.vehicles.service import vehicle_out
from app.modules.vehicles.vin import check_digit_valid, normalize_vin, validate_vin

MAKE_ALIASES = {
    "CHEVY": "CHEVROLET",
    "VW": "VOLKSWAGEN",
    "MERCEDES": "MERCEDESBENZ",
    "BENZ": "MERCEDESBENZ",
    "MB": "MERCEDESBENZ",
    "LANDY": "LANDROVER",
    "OLDS": "OLDSMOBILE",
}
CAMPAIGN_RE = re.compile(r"^\d{2}[VEC]-?\d{3}(-?\d{3})?$", re.I)
GROUP_LIMIT = 8


def stem(word: str) -> str:
    """Very light stemming so 'misfire' finds 'misfiring' and 'brakes' finds 'braking'."""
    if len(word) >= 5 and not any(c.isdigit() for c in word):
        for suffix in ("ing", "ers", "es", "ed", "er", "s", "e"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                return word[: -len(suffix)]
    return word


def words(q: str) -> list[str]:
    raw = [w for w in re.split(r"\s+", q.lower().strip()) if len(w) >= 2 or w.isdigit()][:8]
    return [stem(w) for w in raw]


def _all_words(column, ws: list[str]):
    return and_(*[func.lower(column).like(f"%{w}%") for w in ws])


# ---- vehicles -------------------------------------------------------------------


def find_vehicles(db: Session, q: str) -> list[dict]:
    """Understands things like '2015 f150', 'chevy silverado', 'f-150 2012', 'camry'."""
    tokens = re.split(r"\s+", q.strip())
    this_year = date.today().year + 1
    year = next((int(t) for t in tokens if t.isdigit() and 1981 <= int(t) <= this_year), None)
    rest = [name_key(t) for t in tokens if not (t.isdigit() and len(t) == 4)]
    rest = [MAKE_ALIASES.get(t, t) for t in rest if t]
    if not rest:
        return []

    makes = db.scalars(select(Make)).all()
    make_ids = set()
    model_tokens = []
    for t in rest:
        matched = [
            m.id
            for m in makes
            if name_key(m.name) == t or (len(t) >= 3 and name_key(m.name).startswith(t))
        ]
        if matched:
            make_ids.update(matched)
        else:
            model_tokens.append(t)
    model_key = "".join(model_tokens)

    stmt = select(Model).join(Make, Make.id == Model.make_id)
    if make_ids:
        stmt = stmt.where(Model.make_id.in_(make_ids))
    if year:
        stmt = stmt.where(Model.id.in_(select(ModelYear.model_id).where(ModelYear.year == year)))
    models = db.scalars(stmt).all()
    if model_key:
        models = [m for m in models if model_key in name_key(m.name)]
        # Exact model-name matches first ('f150' -> F-150 before F-150 Heritage)
        models.sort(key=lambda m: (name_key(m.name) != model_key, len(m.name), m.name))
    elif not make_ids:
        return []
    else:
        models.sort(key=lambda m: m.name)

    out = []
    for m in models[:GROUP_LIMIT]:
        years = sorted(
            set(db.scalars(select(ModelYear.year).where(ModelYear.model_id == m.id))), reverse=True
        )
        out.append(
            {
                "model_id": m.id,
                "make": m.make.name,
                "model": m.name,
                "year": year,
                "years": years[:40],
            }
        )
    return out


# ---- everything ---------------------------------------------------------------------


def search(
    db: Session, q: str, vehicle: Vehicle | None = None, types: set[str] | None = None
) -> dict:
    q = q.strip()
    if not q:
        raise AppError("search_empty", 422)
    want = (lambda t: True) if not types else (lambda t: t in types)
    ws = words(q)
    out: dict = {
        "query": q,
        "vin": None,
        "codes": [],
        "vehicles": [],
        "entries": [],
        "recalls": [],
        "tsbs": [],
    }

    vin = normalize_vin(q)
    if len(vin) == 17:
        try:
            validate_vin(vin)
            out["vin"] = {"vin": vin, "check_digit_valid": check_digit_valid(vin)}
        except AppError:
            pass

    code = normalize_code(q)
    looks_like_code = bool(
        CODE_RE.match(code) or (2 <= len(code) <= 5 and code[:1] in "PBCU" and code[1:].isdigit())
    )
    if want("codes"):
        if looks_like_code:
            hits = dtc_service.search(db, code, GROUP_LIMIT)
            out["codes"] = [
                {"code": d.code, "title": d.title, "severity": d.severity} for d in hits
            ]
            if CODE_RE.match(code) and code not in {d.code for d in hits}:
                out["codes"].insert(0, {"code": code, "title": None, "severity": None})
        elif ws:
            # Codes whose title matches come before ones that only mention the words.
            hits = db.scalars(
                select(Dtc)
                .where(Dtc.make_id.is_(None), _all_words(Dtc.title + " " + Dtc.description, ws))
                .order_by(_all_words(Dtc.title, ws).desc(), Dtc.code)
                .limit(GROUP_LIMIT)
            ).all()
            out["codes"] = [
                {"code": d.code, "title": d.title, "severity": d.severity} for d in hits
            ]

    if want("vehicles") and not out["vin"] and not looks_like_code:
        out["vehicles"] = find_vehicles(db, q)

    if want("entries") and ws:
        stmt = select(Entry).where(
            Entry.status == EntryStatus.published, _all_words(Entry.search_text, ws)
        )
        if vehicle is not None:  # entries for this vehicle + general ones
            tagged = select(EntryVehicle.entry_id).where(EntryVehicle.entry_id == Entry.id).exists()
            stmt = stmt.where(Entry.id.in_(vehicle_filter(vehicle)) | ~tagged)
        title_hit = _all_words(Entry.title, ws)
        rows = db.scalars(
            stmt.order_by(title_hit.desc(), Entry.score.desc(), Entry.updated_at.desc()).limit(20)
        ).all()
        out["entries"] = [
            {
                "id": e.id,
                "kind": e.kind.value,
                "title": e.title,
                "safety_critical": e.safety_critical,
                "verified": e.verified_revision_id is not None
                and e.verified_revision_id == e.current_revision_id,
            }  # fmt: skip
            for e in rows
        ]

    if want("recalls"):
        if vehicle is not None and ws:
            recalls = safety.list_recalls(db, vehicle, None)
            recalls = [
                r
                for r in recalls
                if all(w in f"{r.component} {r.summary} {r.campaign_number}".lower() for w in ws)
            ]
            out["recalls"] = [_recall(r) for r in recalls[:GROUP_LIMIT]]
        elif CAMPAIGN_RE.match(q.replace(" ", "")):
            number = q.replace(" ", "").replace("-", "").upper()
            r = db.scalar(select(Recall).where(Recall.campaign_number.startswith(number)))
            out["recalls"] = [_recall(r)] if r else []

    if want("tsbs") and vehicle is not None and ws:
        _, tsbs = safety.list_tsbs(db, vehicle, None, 500, 0)
        tsbs = [
            b
            for b in tsbs
            if all(w in f"{b.bulletin_number} {b.components} {b.summary}".lower() for w in ws)
        ]
        out["tsbs"] = [
            {
                "nhtsa_id": b.nhtsa_id,
                "bulletin_number": b.bulletin_number,
                "date": b.bulletin_date,
                "summary": (b.summary or "")[:200],
            }  # fmt: skip
            for b in tsbs[:GROUP_LIMIT]
        ]

    if vehicle is not None:
        out["vehicle"] = vehicle_out(vehicle).model_dump()
    return out


def _recall(r: Recall) -> dict:
    return {
        "campaign_number": r.campaign_number,
        "component": r.component,
        "summary": (r.summary or "")[:200],
        "report_date": r.report_date,
        "park_it": r.park_it,
        "park_outside": r.park_outside,
    }
