"""Team-written repair content (content/ at the repo root) → community entries.

Content Research Program (CONTENT_PROGRAM.md): each page is one JSON file, written from the
research notes in research/, and published only after a *different* agent fact-checked it
(owner decision 2026-11-06: a designated reviewer agent signs off instead of a mechanic).

File format (see content/README.md):
  kind:        dtc_guide | procedure | ...  (community entry kinds)
  title:       page title
  applies_to:  [{make, model?, year_from, year_to, engine?: engine-family slug}]
  systems:     [system slugs]
  data:        the page, validated by app/modules/community/kinds.py
  fact_check:  {written_by, reviewed_by, reviewed_at, checklist: {...}, notes}

Re-running is safe: an unchanged page is skipped; a changed page becomes a new revision
(history kept). Pages without a valid sign-off are skipped and reported.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.community.kinds import validate_data
from app.modules.community.models import Entry, Kind
from app.modules.community.schemas import Tags
from app.modules.community.service import create_entry, current_rev, edit_entry
from app.modules.vehicles import service as vehicles
from app.modules.vehicles.catalog import _make
from app.modules.vehicles.models import EngineFamily

_HERE = Path(__file__).resolve()
# Repo checkout: <repo>/content ; Docker image: /app/content (see Dockerfile).
CANDIDATES = [_HERE.parents[3] / "content", _HERE.parents[2] / "content"]
CHECKLIST = ("specs_match_sources", "two_sources_for_critical_specs", "applications_exact",
             "safety_warnings_present", "no_copied_text", "steps_complete")  # fmt: skip


def content_dir() -> Path | None:
    return next((p for p in CANDIDATES if p.is_dir()), None)


def signed_off(fc: dict | None) -> bool:
    """Reviewed by someone other than the writer, with every checklist item passed."""
    if not fc or not fc.get("reviewed_by") or not fc.get("reviewed_at"):
        return False
    if fc.get("reviewed_by") == fc.get("written_by"):
        return False
    checks = fc.get("checklist") or {}
    return all(checks.get(k) is True for k in CHECKLIST)


def _applies(db: Session, rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        make = _make(db, r["make"])
        model = vehicles.get_or_create_model(db, make, None, r["model"]) if r.get("model") else None
        a = {"make_id": make.id, "model_id": model.id if model else None,
             "year_from": r["year_from"], "year_to": r["year_to"]}  # fmt: skip
        if r.get("engine"):
            fam = db.scalar(select(EngineFamily).where(EngineFamily.slug == r["engine"]))
            if fam is None:
                raise ValueError(f"unknown engine family {r['engine']}")
            a.update(engine_family_id=fam.id, displacement_l=fam.displacement_l)
        out.append(a)
    return out


def load_file(db: Session, author, path: Path) -> str:
    doc = json.loads(path.read_text(encoding="utf-8"))
    fc = doc.get("fact_check")
    if not signed_off(fc):
        return "waiting_for_review"
    kind = Kind(doc["kind"])
    tags = Tags(applies_to=_applies(db, doc.get("applies_to", [])), systems=doc.get("systems", []))
    existing = db.scalar(
        select(Entry).where(Entry.title == doc["title"], Entry.created_by_id == author.id)
    )
    summary = f"Content program: reviewed by {fc['reviewed_by']} on {fc['reviewed_at']}"
    if existing is None:
        entry = create_entry(db, author, kind, doc["title"], doc["data"], tags, summary)
        rev = current_rev(db, entry)
        result = "added"
    else:
        rev = current_rev(db, existing)
        clean = validate_data(kind, doc["data"])  # compare as stored (defaults filled in)
        same = rev is not None and rev.data == clean and rev.fact_check == fc
        if same:
            return "unchanged"
        rev = edit_entry(db, author, existing, rev.number if rev else 0, doc["title"], doc["data"],
                         tags, summary)  # fmt: skip
        result = "updated"
    rev.fact_check = fc
    db.commit()
    return result


def load_all(db: Session, author) -> dict[str, int]:
    counts: dict[str, int] = {}
    root = content_dir()
    if root is None:
        return counts
    for path in sorted(root.rglob("*.json")):
        result = load_file(db, author, path)
        counts[result] = counts.get(result, 0) + 1
    return counts
