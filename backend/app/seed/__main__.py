"""Load sample data so a fresh install shows something right away.

Usage:  python -m app.seed
Safe to run more than once (it only adds what's missing)."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, new_token
from app.db import SessionLocal
from app.modules.accounts.models import Role, User, UserStatus
from app.modules.community.models import Entry, Kind
from app.modules.community.schemas import Tags
from app.modules.community.service import create_entry, seed_systems
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
            aspiration=row.get("aspiration"),
            source="seed",
        )
        count += 1
    return count


def seed_dtcs(db: Session) -> int:
    """Insert or update generic codes from dtcs.json (our own writing; proprietary, see content/LICENSE)."""
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


TEAM_EMAIL = "team@chrystalclear.invalid"


def team_user(db: Session) -> User:
    """Author for built-in content. It can't log in (random unknown password)."""
    user = db.scalar(select(User).where(User.email == TEAM_EMAIL))
    if user is None:
        user = User(
            email=TEAM_EMAIL,
            password_hash=hash_password(new_token()),
            display_name="ChrystalClear Team",
            role=Role.pro,
            status=UserStatus.active,
        )
        db.add(user)
        db.flush()
    return user


def seed_guides(db: Session) -> int:
    """Add built-in general guides/specs once. Never overwrites community edits."""
    author = team_user(db)
    added = 0
    for row in load("guides.json"):
        exists = db.scalar(
            select(Entry.id).where(Entry.title == row["title"], Entry.created_by_id == author.id)
        )
        if exists:
            continue
        create_entry(
            db,
            author,
            Kind(row["kind"]),
            row["title"],
            row["data"],
            Tags(**row["tags"]),
            "Initial version",
        )
        added += 1
    return added


def run(db: Session, guides: bool = True) -> dict[str, int]:
    from app.modules.vehicles.catalog import seed_engine_families, seed_priorities

    result = {
        "makes_added": seed_makes(db),
        "vehicles": seed_vehicles(db),
        "dtcs": seed_dtcs(db),
        "systems": seed_systems(db),
        "priority_models": seed_priorities(db),
    }
    result.update(seed_engine_families(db))
    if guides:
        from app.seed.manual_specs import load_all

        result["guides_added"] = seed_guides(db)
        result["manual_specs_added"] = load_all(db, team_user(db))
        from app.seed import content

        result["content_pages"] = content.load_all(db, team_user(db))
    from app.config import get_settings

    if get_settings().enable_marketplace:  # optional module: ZIP points for distance search
        from app.modules.marketplace import zips

        result["zip_points_added"] = zips.load(db)
        from app.modules.marketplace import demo

        if get_settings().market_demo_data:
            result["demo_listings_added"] = demo.load(db)
        elif demo.remove(db):
            result["demo_listings_removed"] = True
    db.commit()
    return result


def main() -> None:
    with SessionLocal() as db:
        print("Seed complete:", run(db))


if __name__ == "__main__":
    main()
