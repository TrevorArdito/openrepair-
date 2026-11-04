"""Engine catalog: browse engine families and see which vehicles use them."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db import get_db
from app.modules.vehicles.models import EngineFamily, Make, Model, Vehicle

router = APIRouter(tags=["engines"])


def family_summary(f: EngineFamily, vehicle_count: int | None = None) -> dict:
    return {
        "id": f.id,
        "slug": f.slug,
        "name": f.name,
        "manufacturer": f.manufacturer,
        "displacement_l": f.displacement_l,
        "cylinders": f.cylinders,
        "layout": f.layout,
        "fuel_type": f.fuel_type,
        "aspiration": f.aspiration,
        "codes": f.codes,
        "year_from": f.year_from,
        "year_to": f.year_to,
        "applications": f.applications,
        "notes": f.notes,
        "vehicle_count": vehicle_count,
    }


def search_families(db: Session, words: list[str], limit: int = 8) -> list[EngineFamily]:
    if not words:
        return []
    conds = []
    for w in words:
        like = f"%{w}%"
        conds.append(or_(func.lower(EngineFamily.name).like(like), func.lower(func.coalesce(EngineFamily.codes, "")).like(like),
                         func.lower(EngineFamily.manufacturer).like(like)))  # fmt: skip
    return list(
        db.scalars(select(EngineFamily).where(*conds).order_by(EngineFamily.name).limit(limit))
    )


@router.get("/engines")
def list_engines(
    q: str = Query(default="", max_length=100),
    application: str | None = Query(default=None, max_length=30),
    db: Session = Depends(get_db),
):
    counts = dict(
        db.execute(
            select(Vehicle.engine_family_id, func.count()).group_by(Vehicle.engine_family_id)
        ).all()
    )
    rows = (
        search_families(db, q.lower().split(), 200)
        if q.strip()
        else db.scalars(
            select(EngineFamily).order_by(EngineFamily.manufacturer, EngineFamily.name)
        ).all()
    )
    if application:
        rows = [f for f in rows if application in (f.applications or [])]
    return [family_summary(f, counts.get(f.id, 0)) for f in rows]


@router.get("/engines/{engine_id}")
def engine_detail(engine_id: int, db: Session = Depends(get_db)):
    f = db.get(EngineFamily, engine_id)
    if f is None:
        raise NotFound("engine_not_found")
    # Which models use it, with the model-year range, from the linked vehicles.
    rows = db.execute(
        select(
            Make.name,
            Model.name,
            Model.id,
            func.min(Vehicle.year),
            func.max(Vehicle.year),
            func.count(),
        )
        .select_from(Vehicle)
        .join(Model, Model.id == Vehicle.model_id)
        .join(Make, Make.id == Model.make_id)
        .where(Vehicle.engine_family_id == f.id)
        .group_by(Make.name, Model.name, Model.id)
        .order_by(Make.name, Model.name)
    ).all()
    used_in = [
        {"make": mk, "model": mo, "model_id": mid, "year_from": y1, "year_to": y2, "vehicles": n}
        for mk, mo, mid, y1, y2, n in rows
    ]
    return {**family_summary(f, sum(u["vehicles"] for u in used_in)), "used_in": used_in}


@router.get("/engines/{engine_id}/vehicles")
def engine_vehicles(engine_id: int, model_id: int = Query(ge=1), db: Session = Depends(get_db)):
    """Model years of one model that use this engine (to open a vehicle page)."""
    rows = db.scalars(
        select(Vehicle)
        .where(Vehicle.engine_family_id == engine_id, Vehicle.model_id == model_id)
        .order_by(Vehicle.year.desc())
    ).all()
    return [{"vehicle_id": v.id, "year": v.year} for v in rows]
