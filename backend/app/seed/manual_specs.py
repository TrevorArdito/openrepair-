"""Owner's-manual specs → community entries.

Each file in data/manual_specs/ is one owner's manual, transcribed by hand: the facts only
(capacities, fluid types, torque, engine specs, part numbers), each with the manual's printed
page number. Entries are authored by "ChrystalClear Team", tagged to the exact model years and
engine, and stay editable/verifiable like any other entry. Re-running never overwrites edits.

File format (see ford-f150-2015.json):
  vehicle:  make, model, year_from, year_to
  source:   title (printing/date), url (the manufacturer's own PDF)
  engines:  key -> {family: engine-family slug, label: "2.7L EcoBoost"}
  specs:    [{engine: key|null, page, kind, title, data, systems?}]
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.community.models import Entry, Kind
from app.modules.community.schemas import Tags
from app.modules.community.service import create_entry
from app.modules.vehicles import service as vehicles
from app.modules.vehicles.catalog import _make
from app.modules.vehicles.models import EngineFamily

DIR = Path(__file__).parent / "data" / "manual_specs"

FLUID_SYSTEMS = {
    "engine_oil": ["maintenance", "engine.lubrication"],
    "coolant": ["maintenance", "engine.cooling"],
    "automatic_transmission": ["transmission.automatic"],
    "manual_transmission": ["transmission.manual"],
    "cvt": ["transmission.automatic"],
    "transfer_case": ["drivetrain.transfer_case"],
    "front_differential": ["drivetrain.differential"],
    "rear_differential": ["drivetrain.differential"],
    "brake": ["brakes.hydraulic"],
    "power_steering": ["steering"],
    "refrigerant": ["hvac"],
    "refrigerant_oil": ["hvac"],
    "fuel_tank": ["fuel"],
    "washer": ["body"],
}


def _systems(item: dict) -> list[str]:
    if item.get("systems"):
        return item["systems"]
    if item["kind"] == "fluid_capacity":
        return FLUID_SYSTEMS.get(item["data"]["system"], ["maintenance"])
    return ["maintenance"]


def load_file(db: Session, author, path: Path) -> int:
    doc = json.loads(path.read_text())
    v, src = doc["vehicle"], doc["source"]
    make = _make(db, v["make"])
    model = vehicles.get_or_create_model(db, make, None, v["model"])
    years = (
        str(v["year_from"])
        if v["year_from"] == v["year_to"]
        else f"{v['year_from']}–{v['year_to']}"
    )
    engines = {}
    for key, e in doc.get("engines", {}).items():
        fam = db.scalar(select(EngineFamily).where(EngineFamily.slug == e["family"]))
        if fam is None:
            raise ValueError(f"{path.name}: unknown engine family {e['family']}")
        engines[key] = (fam, e["label"])

    added = 0
    for item in doc["specs"]:
        fam, elabel = engines[item["engine"]] if item.get("engine") else (None, None)
        title = (
            f"{years} {make.name} {model.name}{' ' + elabel if elabel else ''} — {item['title']}"
        )
        if db.scalar(
            select(Entry.id).where(Entry.title == title, Entry.created_by_id == author.id)
        ):
            continue
        data = dict(item["data"])
        if item["kind"] != "labor_time":
            data["sources"] = [
                {"type": "owner_manual", "citation": f"{src['title']}, p. {item['page']}"}
            ]
        applies = {
            "make_id": make.id,
            "model_id": model.id,
            "year_from": v["year_from"],
            "year_to": v["year_to"],
        }
        if fam is not None:
            applies.update(engine_family_id=fam.id, displacement_l=fam.displacement_l)
        tags = Tags(applies_to=[applies], systems=_systems(item))
        create_entry(db, author, Kind(item["kind"]), title, data, tags, f"From {src['title']}")
        added += 1
    return added


def load_all(db: Session, author) -> int:
    return sum(load_file(db, author, p) for p in sorted(DIR.glob("*.json")))
