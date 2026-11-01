"""Owner's-manual specs: every transcribed manual loads, and each engine gets only its own data."""

import json

import pytest
from sqlalchemy import select

from app.modules.community.kinds import validate_data
from app.modules.community.models import Entry, Kind
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

    def keys(s):
        e = s.get("engine")
        return [e] if isinstance(e, str) else (e or [])

    titles = [(tuple(keys(s)), s["title"]) for s in doc["specs"]]
    assert len(titles) == len(set(titles)), "duplicate spec titles"
    for s in doc["specs"]:
        assert isinstance(s["page"], int) and s["page"] > 0
        assert all(k in doc["engines"] for k in keys(s))
        data = dict(s["data"])
        if s["kind"] != "labor_time":
            data["sources"] = [{"type": "owner_manual", "citation": "p. 1"}]
        validate_data(Kind(s["kind"]), data)  # same rules the app enforces


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


def test_manual_specs_shared_by_some_engines(db_session_factory):
    """A fact listed for several (not all) engines reaches exactly those engines."""
    from app.modules.vehicles import service as vehicles
    from app.modules.vehicles.catalog import link_engine_families

    with db_session_factory() as db:
        model = db.scalar(
            select(Model).join(Make).where(Make.name == "Ford", Model.name == "F-150")
        )
        v33 = vehicles.get_or_create_vehicle(
            db, year=2022, model=model, displacement_l=3.3, cylinders=6, fuel_type="gasoline"
        )
        hev = vehicles.get_or_create_vehicle(
            db, year=2022, model=model, displacement_l=3.5, cylinders=6, fuel_type="hybrid",
            aspiration="turbo",
        )  # fmt: skip
        link_engine_families(db)
        load_all(db, team_user(db))
        db.commit()
        db.refresh(v33)
        db.refresh(hev)
        assert v33.engine_family.slug == "ford-3-3-v6"
        assert hev.engine_family.slug == "ford-3-5-powerboost"

        _, items = list_entries(db, vehicle=v33, include_generic=False, limit=200)
        by_title = {i.title: i for i in items}
        crew = next(t for t in by_title if "— Fuel tank (SuperCrew, standard)" in t)
        assert "3.3L V6" in crew and by_title[crew].data["amount"] == 98.4
        axle = by_title["2022 Ford F-150 — Rear axle fluid (8.8-inch)"]
        assert (axle.data["amount"], axle.data["amount_max"]) == (1.9, 2.0)

        _, items = list_entries(db, vehicle=hev, include_generic=False, limit=200)
        titles = {i.title for i in items}
        assert not any("SuperCrew" in t for t in titles)  # hybrid has its own tank
        assert "2022 Ford F-150 3.5L PowerBoost Hybrid — Fuel tank" in titles
        assert "2022 Ford F-150 — Wheel lug nut torque" in titles
