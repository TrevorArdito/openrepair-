"""Refresh NHTSA safety data.

Examples (run from the backend folder, or inside the api container):

  # Re-check recalls + complaints for every vehicle in our database
  python -m app.importers.nhtsa refresh

  # Import the TSB index for models we know about (downloads NHTSA's bulk files)
  python -m app.importers.nhtsa tsbs --period 2020-2024 --period 2025-2026

  # Import from a file you already downloaded
  python -m app.importers.nhtsa tsbs --file TSBS_RECEIVED_2020-2024.zip

Safe to re-run: everything is upserted (no duplicates). Each run is logged in
the data_imports table.
"""

import argparse
import io
import sys
import tempfile
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db import SessionLocal
from app.modules.safety import service
from app.modules.safety.models import DataImport, SafetyFetch, name_key
from app.modules.safety.nhtsa import NhtsaApi, get_nhtsa
from app.modules.vehicles.models import Make, Model, Vehicle

TSB_URL = "https://static.nhtsa.gov/odi/ffdd/tsbs/TSBS_RECEIVED_{period}.zip"
TSB_PERIODS = ["1995-1999", "2000-2004", "2005-2009", "2010-2014", "2015-2019",
               "2020-2024", "2025-2026"]  # fmt: skip
BATCH = 500


def _start(db: Session, source: str) -> DataImport:
    log = DataImport(source=source)
    db.add(log)
    db.commit()
    return log


def _finish(db: Session, log: DataImport, status: str = "ok", error: str | None = None) -> None:
    log.status = status
    log.error = error
    log.finished_at = datetime.now(UTC)
    db.commit()


# ---- recalls / complaints via the API --------------------------------------


def refresh_api(db: Session, nhtsa: NhtsaApi, sources: list[str], force: bool = False) -> dict:
    """Re-check recalls/complaints for every make/model/year someone has looked up.

    (Not every vehicle in the catalog — that would be tens of thousands of NHTSA calls.)"""
    models = {(name_key(m.make.name), name_key(m.name)): m for m in db.scalars(select(Model))}
    results = {}
    for source in sources:
        log = _start(db, source)
        done = failed = 0
        fetched = db.execute(
            select(SafetyFetch.make_key, SafetyFetch.model_key, SafetyFetch.year).where(
                SafetyFetch.source == source
            )
        ).all()
        for mk, mo, year in fetched:
            model = models.get((mk, mo))
            vehicle = model and db.scalar(
                select(Vehicle).where(Vehicle.model_id == model.id, Vehicle.year == year).limit(1)
            )
            if not vehicle:
                continue
            try:
                service.refresh(db, nhtsa, source, vehicle, force=force)
                done += 1
            except AppError:
                failed += 1
        log.rows_updated = done
        _finish(
            db, log, "partial" if failed else "ok", f"{failed} lookups failed" if failed else None
        )
        results[source] = {"vehicles": done, "failed": failed}
    return results


# ---- TSB index from bulk files ---------------------------------------------


def parse_tsb_line(line: str) -> dict[str, Any] | None:
    """One line of NHTSA's TSB flat file (field list: static.nhtsa.gov/odi/ffdd/tsbs/TSBS.txt)."""
    f = line.rstrip("\r\n").split("\t")
    if len(f) < 14 or not f[0].strip().isdigit():
        return None
    try:
        year = int(f[9])
    except ValueError:
        return None
    if year == 9999 or not f[7].strip() or not f[8].strip():
        return None
    return {
        "nhtsa_id": int(f[0]),
        "bulletin_number": f[3].strip() or None,
        "bulletin_date": service.parse_date(f[4], "%Y%m%d"),
        "comm_type": f[6].strip() or None,
        "make": f[7].strip(),
        "model": f[8].strip(),
        "year": year,
        "component": f[10].strip() or None,
        "summary": f[13],
    }


def iter_zip_lines(path: Path) -> Iterator[str]:
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.filename.lower().endswith(".txt"):
                with z.open(info) as raw:
                    yield from io.TextIOWrapper(raw, encoding="utf-8", errors="replace")


def known_model_keys(db: Session) -> set[tuple[str, str]]:
    rows = db.execute(select(Make.name, Model.name).join(Model, Model.make_id == Make.id))
    return {(name_key(mk), name_key(mo)) for mk, mo in rows}


def import_tsb_lines(db: Session, lines, only: set[tuple[str, str]] | None) -> tuple[int, int]:
    added = seen = 0
    for i, line in enumerate(lines, 1):
        rec = parse_tsb_line(line)
        if rec is None:
            continue
        if only is not None and (name_key(rec["make"]), name_key(rec["model"])) not in only:
            continue
        seen += 1
        added += service.upsert_tsb(db, rec)
        if i % BATCH == 0:
            db.commit()
    db.commit()
    return added, seen


def download(url: str, dest: Path) -> Path:
    print(f"Downloading {url} …", flush=True)
    with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
    return dest


def import_tsbs(db: Session, files: list[Path], all_models: bool = False) -> dict:
    log = _start(db, "tsbs")
    only = None if all_models else known_model_keys(db)
    added = seen = 0
    try:
        for path in files:
            a, s = import_tsb_lines(db, iter_zip_lines(path), only)
            added += a
            seen += s
    except Exception as exc:
        _finish(db, log, "failed", str(exc)[:1000])
        raise
    log.rows_added = added
    log.rows_updated = seen - added
    _finish(db, log)
    return {"tsbs_added": added, "rows_matched": seen}


# ---- CLI -------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.importers.nhtsa", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ref = sub.add_parser("refresh", help="refresh recalls/complaints for all known vehicles")
    p_ref.add_argument("--source", choices=["recalls", "complaints", "all"], default="all")
    p_ref.add_argument("--force", action="store_true", help="ignore the 7-day cache")

    p_tsb = sub.add_parser("tsbs", help="import the NHTSA TSB index")
    p_tsb.add_argument("--period", action="append", choices=TSB_PERIODS)
    p_tsb.add_argument("--file", action="append", type=Path, help="local TSBS_RECEIVED_*.zip")
    p_tsb.add_argument("--all-models", action="store_true",
                       help="import every model (large!) instead of only models in our database")  # fmt: skip

    args = parser.parse_args(argv)
    with SessionLocal() as db:
        if args.cmd == "refresh":
            sources = ["recalls", "complaints"] if args.source == "all" else [args.source]
            print(refresh_api(db, get_nhtsa(), sources, force=args.force))
            return 0

        files = list(args.file or [])
        with tempfile.TemporaryDirectory() as tmp:
            for period in args.period or ([] if files else ["2020-2024", "2025-2026"]):
                files.append(download(TSB_URL.format(period=period), Path(tmp) / f"{period}.zip"))
            print(import_tsbs(db, files, all_models=args.all_models))
    return 0


if __name__ == "__main__":
    sys.exit(main())
