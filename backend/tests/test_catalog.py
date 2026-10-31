"""Vehicle catalog: EPA import, engine families, heavy-duty diesel trucks, priorities."""

import csv
import io
import zipfile

from sqlalchemy import func, select

from app.importers.epa import clean_model, fuel_of, layout_of, run
from app.modules.vehicles.models import EngineFamily, Make, Model, Vehicle
from app.modules.vehicles.service import vehicle_out

COLS = [
    "year",
    "make",
    "model",
    "baseModel",
    "displ",
    "cylinders",
    "fuelType",
    "atvType",
    "tCharger",
    "sCharger",
]
ROWS = [
    # year, make, model, baseModel, displ, cyl, fuel, atv, turbo, supercharger
    ("2015", "Ford", "F150 Pickup 4WD", "F150", "3.5", "6", "Regular", "", "T", ""),
    ("2015", "Ford", "F150 Pickup 2WD FFV", "F150", "3.5", "6", "Gasoline or E85", "FFV", "", ""),
    ("2015", "Ford", "F150 Pickup 4WD FFV", "F150", "5.0", "8", "Gasoline or E85", "FFV", "", ""),
    (
        "2015",
        "Ford",
        "F150 Pickup 2WD FFV",
        "F150",
        "5.0",
        "8",
        "Gasoline or E85",
        "FFV",
        "",
        "",
    ),  # same engine, 2WD
    ("2019", "Ram", "1500 4WD", "1500", "5.7", "8", "Regular", "", "", ""),
    ("2005", "Dodge", "Ram 1500 Pickup 2WD", "Ram 1500 Pickup", "4.7", "8", "Regular", "", "", ""),
    ("2004", "Jeep", "Wrangler/TJ 4WD", "Wrangler/TJ", "4.0", "6", "Regular", "", "", ""),
    ("2021", "Tesla", "Model 3 Long Range AWD", "Model 3", "", "", "Electricity", "EV", "", ""),
    ("2019", "Toyota", "Camry Hybrid LE", "Camry", "2.5", "4", "Regular", "Hybrid", "", ""),
    ("2019", "Toyota", "Camry", "Camry", "2.5", "4", "Regular", "", "", ""),
    ("2016", "Subaru", "Outback AWD", "Outback", "2.5", "4", "Regular", "", "", ""),
]


def epa_zip(tmp_path):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLS)
    w.writerows(ROWS)
    path = tmp_path / "vehicles.csv.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("vehicles.csv", buf.getvalue())
    return path


def labels(db, make, model, year):
    rows = db.scalars(
        select(Vehicle)
        .join(Model)
        .join(Make)
        .where(Make.name == make, Model.name == model, Vehicle.year == year)
    ).all()
    return sorted(
        (vehicle_out(v).engine.label or "", v.engine_family.slug if v.engine_family else None)
        for v in rows
    )


def test_name_and_fuel_rules():
    assert clean_model("Ford", "F150 Pickup") == "F150"
    assert clean_model("Dodge", "Ram 1500 Pickup") == "Ram"  # NHTSA calls it "Ram"
    assert clean_model("Jeep", "Wrangler/TJ") == "Wrangler"
    assert fuel_of({"fuelType": "Gasoline or E85", "atvType": "FFV"}) == "gasoline"
    assert fuel_of({"fuelType": "Diesel", "atvType": "Diesel"}) == "diesel"
    assert fuel_of({"fuelType": "Regular", "atvType": "Hybrid"}) == "hybrid"
    assert layout_of("Subaru", "Outback", 4) == "flat"
    assert layout_of("Ford", "F150", 6) is None  # V6 or I6? don't guess
    assert layout_of("Toyota", "Camry", 4) == "inline"


def test_epa_import_matches_existing_models_and_links_engines(db_session_factory, tmp_path):
    path = epa_zip(tmp_path)
    with db_session_factory() as db:
        before_models = db.scalar(select(func.count()).select_from(Model))
        stats = run(db, path)
        assert stats["rows"] == len(ROWS)
        # EPA "F150" joins our existing "F-150", Dodge "Ram 1500 Pickup" joins "Ram", no duplicates
        f150_models = db.scalars(
            select(Model).join(Make).where(Make.name == "Ford", Model.name.in_(["F150", "F-150"]))
        ).all()
        assert [m.name for m in f150_models] == ["F-150"]

        f150 = labels(db, "Ford", "F-150", 2015)
        assert ("3.5L V6 Turbo", "ford-3-5-ecoboost") in f150
        assert ("3.5L V6", "ford-3-5-cyclone") in f150  # non-turbo 3.5 stays separate
        assert ("5.0L V8", "ford-5-0-coyote") in f150  # FFV + 2WD/4WD rows collapse into one engine
        assert len([x for x in f150 if x[0] == "5.0L V8"]) == 1

        assert labels(db, "Ram", "1500", 2019) == [("5.7L V8", "chrysler-5-7-hemi")]
        assert labels(db, "Dodge", "Ram", 2005)[:2] == [
            ("4.7L V8", "chrysler-4-7-powertech"),
            ("5.9L I6 Turbo Diesel", "cummins-5-9"),
        ]
        assert labels(db, "Jeep", "Wrangler", 2004) == [("4.0L I6", "jeep-4-0-i6")]
        assert labels(db, "Tesla", "Model 3", 2021) == [("Electric", None)]
        assert labels(db, "Toyota", "Camry", 2019) == [
            ("2.5L I4", "toyota-2-5-a25a"),
            ("2.5L I4 Hybrid", None),
        ]
        assert labels(db, "Subaru", "Outback", 2016) == [("2.5L H4", None)]

        new_models = db.scalar(select(func.count()).select_from(Model)) - before_models
        again = run(db, path)  # idempotent
        assert again["vehicles_added"] == 0 and again["models_added"] == 0
        assert new_models >= 2  # Tesla Model 3, Subaru Outback


def test_heavy_duty_diesels_and_priorities_seeded(client, db_session_factory):
    with db_session_factory() as db:
        assert labels(db, "Ford", "F-250", 2006) == [
            ("6.0L V8 Turbo Diesel", "ford-6-0-powerstroke")
        ]
        assert labels(db, "Ram", "2500", 2020) == [("6.7L I6 Turbo Diesel", "cummins-6-7")]
        both = labels(db, "Dodge", "Ram", 2007)  # the 5.9 → 6.7 changeover year
        assert ("5.9L I6 Turbo Diesel", "cummins-5-9") in both and (
            "6.7L I6 Turbo Diesel",
            "cummins-6-7",
        ) in both
        assert ("6.6L V8 Turbo Diesel", "gm-6-6-duramax") in labels(
            db, "Chevrolet", "Silverado", 2012
        )
        top = db.scalars(
            select(Model).where(Model.priority.is_not(None)).order_by(Model.priority, Model.name)
        ).all()
        assert [m.name for m in top[:3]] == ["F-150", "Silverado", "1500"]
        assert db.scalar(select(func.count()).select_from(EngineFamily)) >= 40


def test_engines_api_and_search(client):
    engines = client.get("/api/v1/engines").json()
    cummins = next(e for e in engines if e["slug"] == "cummins-6-7")
    assert cummins["vehicle_count"] > 10 and "heavy_duty" in cummins["applications"]
    detail = client.get(f"/api/v1/engines/{cummins['id']}").json()
    assert {(u["make"], u["model"]) for u in detail["used_in"]} >= {
        ("Ram", "2500"),
        ("Ram", "3500"),
        ("Dodge", "Ram"),
    }
    ram2500 = next(u for u in detail["used_in"] if u["model"] == "2500")
    years = client.get(
        f"/api/v1/engines/{cummins['id']}/vehicles", params={"model_id": ram2500["model_id"]}
    ).json()
    from datetime import date

    assert (
        years[0]["year"] == date.today().year and years[-1]["year"] == 2011
    )  # no future model years
    assert client.get("/api/v1/engines/999999").status_code == 404

    found = client.get("/api/v1/search", params={"q": "cummins"}).json()["engines"]
    assert {e["name"] for e in found} >= {
        "Cummins 6.7L I6 Turbo Diesel",
        "Cummins 5.9L I6 Turbo Diesel",
    }
    assert (
        client.get("/api/v1/search", params={"q": "L83"})
        .json()["engines"][0]["name"]
        .startswith("GM 5.3L")
    )
    heavy = client.get("/api/v1/engines", params={"application": "heavy_duty"}).json()
    assert all("heavy_duty" in e["applications"] for e in heavy) and len(heavy) >= 7


def test_vehicle_shows_engine_family(client):
    engines = client.get("/api/v1/engines", params={"q": "power stroke 6.7"}).json()
    detail = client.get(f"/api/v1/engines/{engines[0]['id']}").json()
    f250 = next(u for u in detail["used_in"] if u["model"] == "F-250")
    vid = client.get(
        f"/api/v1/engines/{engines[0]['id']}/vehicles", params={"model_id": f250["model_id"]}
    ).json()[0]["vehicle_id"]
    v = client.get(f"/api/v1/vehicles/{vid}").json()
    assert v["engine"]["family"]["name"] == "Ford 6.7L Power Stroke V8 Turbo Diesel"
    assert v["engine"]["label"] == "6.7L V8 Turbo Diesel"
