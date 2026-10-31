"""Load sample data so a fresh install shows something right away.

Usage:  python -m app.seed
Safe to run more than once (it only adds what's missing)."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.modules.dtc.models import Dtc
from app.modules.vehicles import service
from app.modules.vehicles.models import Make

DATA = Path(__file__).parent / "data"


def load(name: str):
    return json.loads((DATA / name).read_text())


def seed_makes(db: Session) -> int:
    added = 0
    for row in load("makes.json"):
        make = db.scalar(select(Make).where(Make.vpic_make_id == row["vpic_make_id"]))
        if make is None:
            make = db.scalar(select(Make).where(Make.name == row["name"]))
        if make is None:
            make = Make(name=row["name"], vpic_make_id=row["vpic_make_id"])
            db.add(make)
            added += 1
        make.name = row["name"]
        make.vpic_make_id = row["vpic_make_id"]
        make.popular = True
    db.flush()
    return added


def seed_vehicles(db: Session) -> int:
    count = 0
    for row in load("vehicles.json"):
        make = service.get_or_create_make(db, None, row["make"])
        model = service.get_or_create_model(db, make, None, row["model"])
        service.get_or_create_vehicle(
            db,
            year=row["year"],
            model=model,
            displacement_l=row.get("displacement_l"),
            cylinders=row.get("cylinders"),
            fuel_type=row.get("fuel"),
            engine_layout=row.get("layout"),
            engine_code=row.get("engine_code"),
        )
        count += 1
    return count


def seed_dtcs(db: Session) -> int:
    """Insert or update generic codes from dtcs.json (our own writing, CC BY-SA 4.0)."""
    count = 0
    for row in load("dtcs.json"):
        dtc = db.scalar(select(Dtc).where(Dtc.code == row["code"], Dtc.make_id.is_(None)))
        if dtc is None:
            dtc = Dtc(code=row["code"])
            db.add(dtc)
        for field in ("title", "description", "symptoms", "causes", "diagnostic_steps",
                      "severity", "systems", "source", "source_license"):  # fmt: skip
            setattr(dtc, field, row[field])
        count += 1
    return count


def run(db: Session) -> dict[str, int]:
    result = {"makes_added": seed_makes(db), "vehicles": seed_vehicles(db), "dtcs": seed_dtcs(db)}
    db.commit()
    return result


def main() -> None:
    with SessionLocal() as db:
        print("Seed complete:", run(db))


if __name__ == "__main__":
    main()
