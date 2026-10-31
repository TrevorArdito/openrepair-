"""Import every light-duty vehicle and engine from the EPA fuel-economy database
(fueleconomy.gov, US government data, public domain): ~50,000 rows, 1984 → next model year.

  python -m app.importers.epa                 # download the latest file and import
  python -m app.importers.epa --file vehicles.csv.zip

Each row becomes a year + make + model + engine (displacement, cylinders, fuel,
turbo/supercharger) in our `vehicles` table, matched to the makes/models we already
have from NHTSA. Safe to re-run: nothing is duplicated, and community content is untouched.
Heavy-duty trucks (F-250+, Ram 2500+, Silverado/Sierra HD) aren't in EPA data; their
diesel engines come from our engine catalog instead (see catalog.py).
"""

import argparse
import csv
import io
import re
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.modules.safety.models import DataImport, name_key
from app.modules.vehicles.catalog import link_engine_families
from app.modules.vehicles.models import Make, Model, ModelYear, Vehicle
from app.modules.vehicles.service import config_key, make_display_name

EPA_URL = "https://www.fueleconomy.gov/feg/epadata/vehicles.csv.zip"
MIN_YEAR = 1984

_SUFFIXES = re.compile(r"\s+(Pickup|Pickup Truck|2WD|4WD|AWD|FWD|RWD|FFV|Cab Chassis)\b", re.I)
# EPA name -> the name NHTSA uses, where they differ.
MODEL_ALIASES = {
    ("DODGE", "RAM1500"): "Ram",
    ("DODGE", "RAM2500"): "Ram",
    ("DODGE", "RAM3500"): "Ram",
    ("JEEP", "WRANGLERTJ"): "Wrangler",
    ("NISSAN", "ALTIMASTANZA"): "Altima",
    ("HYUNDAI", "JCARELANTRA"): "Elantra",
}


def clean_model(make: str, base: str) -> str:
    name = base.strip()
    for _ in range(3):
        name = _SUFFIXES.sub("", name).strip()
    return MODEL_ALIASES.get((name_key(make), name_key(name)), name)


def fuel_of(row: dict) -> str:
    atv = row.get("atvType", "").strip()
    fuel = row.get("fuelType", "")
    if atv == "EV":
        return "electric"
    if atv in ("Hybrid", "Plug-in Hybrid"):
        return "hybrid"
    if atv in ("FCV", "eFCV"):
        return "hydrogen"
    if atv == "CNG" or fuel == "CNG":
        return "cng"
    if atv == "Diesel" or "Diesel" in fuel:
        return "diesel"
    return "gasoline"  # regular/premium/midgrade, flex-fuel (E85) and bi-fuel gasoline engines


def aspiration_of(row: dict) -> str | None:
    t = row.get("tCharger", "").strip().upper() == "T"
    s = row.get("sCharger", "").strip().upper() == "S"
    return "twincharged" if t and s else "turbo" if t else "supercharged" if s else None


FLAT_MODELS = {"911", "BOXSTER", "CAYMAN", "718BOXSTER", "718CAYMAN", "718SPYDER"}


def layout_of(make: str, model: str, cylinders: int | None) -> str | None:
    """Only fill in a cylinder layout when it's certain; otherwise leave it blank."""
    if cylinders is None:
        return None
    if name_key(make) == "SUBARU" or (
        name_key(make) == "PORSCHE" and name_key(model) in FLAT_MODELS
    ):
        return "flat"
    if cylinders <= 5:
        return "inline"
    if cylinders in (8, 10):
        return "v"
    return None  # 6 and 12 cylinders vary (V6/I6, V12/W12) — the engine catalog fills these in


def _int(v: str) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _float(v: str) -> float | None:
    try:
        f = round(float(v), 1)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def read_rows(path: Path):
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(name) as raw:
            yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", errors="replace"))


def import_rows(db: Session, rows) -> dict:
    """Bulk import with in-memory lookups (fast even against a remote database)."""
    makes = {name_key(m.name): m for m in db.scalars(select(Make))}
    models = {(m.make_id, name_key(m.name)): m for m in db.scalars(select(Model))}
    keys = set(db.scalars(select(Vehicle.config_key)))
    model_years = {(m, y) for m, y in db.execute(select(ModelYear.model_id, ModelYear.year))}
    stats = {"rows": 0, "skipped": 0, "makes_added": 0, "models_added": 0, "vehicles_added": 0}

    for row in rows:
        stats["rows"] += 1
        year = _int(row.get("year", ""))
        make_raw = (row.get("make") or "").strip()
        base = (row.get("baseModel") or row.get("model") or "").strip()
        if not year or year < MIN_YEAR or not make_raw or not base:
            stats["skipped"] += 1
            continue
        mk = name_key(make_raw)
        make = makes.get(mk)
        if make is None:
            make = Make(name=make_display_name(make_raw))
            db.add(make)
            db.flush()
            makes[mk] = make
            stats["makes_added"] += 1
        model_name = clean_model(make_raw, base)
        model = models.get((make.id, name_key(model_name)))
        if model is None:
            model = Model(make_id=make.id, name=model_name)
            db.add(model)
            db.flush()
            models[(make.id, name_key(model_name))] = model
            stats["models_added"] += 1
        if (model.id, year) not in model_years:
            db.add(ModelYear(model_id=model.id, make_id=make.id, year=year))
            model_years.add((model.id, year))

        fuel = fuel_of(row)
        disp = _float(row.get("displ", "")) if fuel != "electric" else None
        cyl = _int(row.get("cylinders", "")) if fuel != "electric" else None
        asp = aspiration_of(row) if fuel != "electric" else None
        key = config_key(year, model.id, disp, cyl, fuel, asp)
        if key in keys:
            continue
        db.add(Vehicle(
            config_key=key, year=year, model_id=model.id, engine_displacement_l=disp, cylinders=cyl,
            fuel_type=fuel, aspiration=asp, engine_layout=layout_of(make_raw, model_name, cyl), source="epa",
        ))  # fmt: skip
        keys.add(key)
        stats["vehicles_added"] += 1
        if stats["vehicles_added"] % 2000 == 0:
            db.flush()
    db.flush()
    stats["vehicles_linked_to_engines"] = link_engine_families(db)
    db.commit()
    return stats


def run(db: Session, path: Path) -> dict:
    log = DataImport(source="epa_vehicles")
    db.add(log)
    db.commit()
    try:
        stats = import_rows(db, read_rows(path))
    except Exception as exc:
        db.rollback()
        log.status, log.error, log.finished_at = "failed", str(exc)[:1000], datetime.now(UTC)
        db.commit()
        raise
    log.status, log.finished_at = "ok", datetime.now(UTC)
    log.rows_added = stats["vehicles_added"]
    db.commit()
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.importers.epa", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    p.add_argument("--file", type=Path, help="local vehicles.csv.zip (otherwise downloaded)")
    args = p.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp, SessionLocal() as db:
        path = args.file
        if path is None:
            path = Path(tmp) / "vehicles.csv.zip"
            print(f"Downloading {EPA_URL} …", flush=True)
            with httpx.stream("GET", EPA_URL, timeout=300, follow_redirects=True) as r:
                r.raise_for_status()
                with path.open("wb") as fh:
                    for chunk in r.iter_bytes(1 << 20):
                        fh.write(chunk)
        print(run(db, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
