"""Vehicle catalog building blocks: engine families, priority models, and linking
engines to vehicles. Used by the seed script and the EPA importer.

Linking rule (strict on purpose — no guessing): a vehicle gets an engine family only
when make, model, model year, displacement, cylinder count, fuel and turbo/supercharger
all match one of that family's known applications."""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.vehicles import service
from app.modules.vehicles.models import EngineFamily, EngineFamilyApplication, Make, Model, Vehicle

DATA = Path(__file__).parents[2] / "seed" / "data"


def present_year() -> int:
    return date.today().year + 1


def _make(db: Session, name: str) -> Make:
    from app.modules.safety.models import name_key

    for m in db.scalars(select(Make)):
        if name_key(m.name) == name_key(name):
            return m
    return service.get_or_create_make(db, None, name)


def seed_priorities(db: Session) -> int:
    rows = json.loads((DATA / "priority_models.json").read_text())["models"]
    for row in rows:
        model = service.get_or_create_model(db, _make(db, row["make"]), None, row["model"])
        model.priority = row["priority"]
    db.flush()
    return len(rows)


def seed_engine_families(db: Session) -> dict:
    families = json.loads((DATA / "engine_families.json").read_text())
    created_vehicles = 0
    for f in families:
        fam = db.scalar(select(EngineFamily).where(EngineFamily.slug == f["slug"]))
        if fam is None:
            fam = EngineFamily(slug=f["slug"])
            db.add(fam)
        for key in ("name", "manufacturer", "displacement_l", "cylinders", "layout", "fuel_type", "aspiration",
                    "codes", "year_from", "year_to", "applications", "notes"):  # fmt: skip
            setattr(fam, key, f.get(key))
        db.flush()
        db.query(EngineFamilyApplication).filter_by(engine_family_id=fam.id).delete()
        for a in f["fitment"]:
            make = _make(db, a["make"])
            model = (
                service.get_or_create_model(db, make, None, a["model"]) if a.get("model") else None
            )
            app = EngineFamilyApplication(
                engine_family_id=fam.id,
                make_id=make.id,
                model_id=model.id if model else None,
                year_from=a["year_from"],
                year_to=a["year_to"] or present_year(),
                creates_vehicles=bool(a.get("create")),
            )
            db.add(app)
            if app.creates_vehicles and model is not None:
                # Vehicles missing from EPA data (heavy-duty trucks): create one per model year.
                # Only through the current calendar year: never assume a future model exists.
                for year in range(app.year_from, min(app.year_to, date.today().year) + 1):
                    before = db.scalar(select(func.count()).select_from(Vehicle))
                    service.get_or_create_vehicle(
                        db, year=year, model=model, displacement_l=fam.displacement_l, cylinders=fam.cylinders,
                        fuel_type=fam.fuel_type, engine_layout=fam.layout, engine_code=fam.codes.split(",")[0] if fam.codes else None,
                        aspiration=fam.aspiration, source="catalog",
                    )  # fmt: skip
                    created_vehicles += (
                        db.scalar(select(func.count()).select_from(Vehicle)) - before
                    )
    db.flush()
    linked = link_engine_families(db)
    return {
        "engine_families": len(families),
        "catalog_vehicles_added": created_vehicles,
        "vehicles_linked": linked,
    }


def link_engine_families(db: Session) -> int:
    """Attach engine families to matching vehicles (see the rule at the top)."""
    linked = 0
    rows = db.execute(select(EngineFamilyApplication, EngineFamily).join(EngineFamily)).all()
    for app, fam in rows:
        model_ids = (
            [app.model_id]
            if app.model_id
            else list(db.scalars(select(Model.id).where(Model.make_id == app.make_id)))
        )
        if not model_ids or fam.displacement_l is None:
            continue
        stmt = (
            update(Vehicle)
            .where(
                Vehicle.model_id.in_(model_ids),
                Vehicle.year >= app.year_from,
                Vehicle.year <= app.year_to,
                func.abs(Vehicle.engine_displacement_l - fam.displacement_l) < 0.05,
                Vehicle.cylinders == fam.cylinders,
                Vehicle.fuel_type == fam.fuel_type,
                (Vehicle.aspiration == fam.aspiration)
                if fam.aspiration
                else Vehicle.aspiration.is_(None),
            )
            .values(engine_family_id=fam.id)
            .execution_options(synchronize_session=False)
        )
        linked += db.execute(stmt).rowcount or 0
        # Fill in the cylinder layout (V8, I4...) where the source data didn't have it.
        db.execute(
            update(Vehicle)
            .where(Vehicle.engine_family_id == fam.id, Vehicle.engine_layout.is_(None))
            .values(engine_layout=fam.layout)
            .execution_options(synchronize_session=False)
        )
    db.flush()
    return linked
