"""Owner's-manual specs: every transcribed manual loads, and each engine gets only its own data."""

import json

import pytest
from sqlalchemy import select

from app.modules.community.models import Entry
from app.modules.community.service import list_entries
from app.modules.vehicles.models import EngineFamily, Make, Model, Vehicle
from app.seed.__main__ import team_user
from app.seed.manual_specs import DIR, load_all

FILES = sorted(DIR.glob("*.json"))


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_manual_file_is_well_formed(path):
    doc = json.loads(path.read_text())
    assert doc["source"]["url"].startswith("https://"), "must link the manufacturer's own manual"
    assert doc["source"]["title"]
    titles = [(s.get("engine"), s["title"]) for s in doc["specs"]]
    assert len(titles) == len(set(titles)), "duplicate spec titles"
    for s in doc["specs"]:
        assert isinstance(s["page"], int) and s["page"] > 0
        assert s.get("engine") is None or s["engine"] in doc["engines"]


def _f150(db, slug):
    return db.scalar(
        select(Vehicle).join(Model).join(Make).join(EngineFamily, EngineFamily.id == Vehicle.engine_family_id)
        .where(Make.name == "Ford", Model.name == "F-150", Vehicle.year == 2015, EngineFamily.slug == slug)
    )  # fmt: skip


def test_manual_specs_load_per_engine_and_idempotent(db_session_factory):
    with db_session_factory() as db:
        added = load_all(db, team_user(db))
        db.commit()
        assert added >= 50
        assert load_all(db, team_user(db)) == 0  # re-running adds nothing

        eb = _f150(db, "ford-3-5-ecoboost")
        _, items = list_entries(db, vehicle=eb, include_generic=False, limit=100)
        titles = {i.title for i in items}
        assert "2015 Ford F-150 3.5L EcoBoost — Engine oil" in titles
        assert "2015 Ford F-150 5.0L V8 — Engine oil" not in titles  # other engine's data excluded
        assert "2015 Ford F-150 — Wheel lug nut torque" in titles  # shared by every engine
        oil = next(i for i in items if i.title.endswith("EcoBoost — Engine oil"))
        assert oil.data["amount"] == 5.7 and "5W-30" in oil.data["fluid_spec"]
        assert oil.data["printed"] == "6.0 qt (5.7 L)"

        v8 = _f150(db, "ford-5-0-coyote")
        _, items = list_entries(db, vehicle=v8, include_generic=False, limit=100)
        v8_oil = next(i for i in items if i.title.endswith("5.0L V8 — Engine oil"))
        assert "5W-20" in v8_oil.data["fluid_spec"]
        firing = next(i for i in items if i.title.endswith("— Firing order"))
        assert firing.data["text"] == "1-3-7-2-6-5-4-8"

        entry = db.scalar(
            select(Entry).where(Entry.title == "2015 Ford F-150 — Wheel lug nut torque")
        )
        assert entry.safety_critical  # torque always carries the safety banner
