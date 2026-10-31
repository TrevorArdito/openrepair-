"""Recalls, complaints and the TSB index (NHTSA data)."""

import zipfile
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.importers.nhtsa import import_tsbs, parse_tsb_line, refresh_api
from app.modules.safety.models import DataImport, SafetyFetch, Tsb


def _f150_id(client):
    makes = client.get("/api/v1/vehicles/makes").json()
    ford = next(m["id"] for m in makes if m["name"] == "Ford")
    models = client.get("/api/v1/vehicles/models", params={"year": 2015, "make_id": ford}).json()
    f150 = next(m["id"] for m in models if m["name"] == "F-150")
    engines = client.get("/api/v1/vehicles/engines", params={"year": 2015, "model_id": f150})
    return engines.json()[0]["id"]


def test_recalls_fetched_parsed_and_cached(client, nhtsa):
    vid = _f150_id(client)
    body = client.get(f"/api/v1/vehicles/{vid}/recalls").json()
    assert body["total"] == 1
    r = body["items"][0]
    assert r["campaign_number"] == "18V894000"
    assert r["report_date"] == "2018-12-18"  # NHTSA sends day/month/year
    assert r["park_outside"] is True
    assert body["stale"] is False
    assert body["source_url"] == "https://www.nhtsa.gov/vehicle/2015/FORD/F-150"

    client.get(f"/api/v1/vehicles/{vid}/recalls")
    assert nhtsa.calls == 1  # cached for 7 days
    assert client.get(f"/api/v1/vehicles/{vid}").json()["counts"]["recalls"] == 1


def test_recalls_shared_across_engines(client, nhtsa):
    """Recalls are per make/model/year, so both F-150 engines see them."""
    vid = _f150_id(client)
    client.get(f"/api/v1/vehicles/{vid}/recalls")
    other = client.post("/api/v1/vehicles", json={"year": 2015, "model_id": 1}).json()
    assert client.get(f"/api/v1/vehicles/{other['id']}/recalls").json()["total"] == 1
    assert nhtsa.calls == 1


def test_recall_search(client):
    vid = _f150_id(client)
    assert (
        client.get(f"/api/v1/vehicles/{vid}/recalls", params={"q": "heater"}).json()["total"] == 1
    )
    assert (
        client.get(f"/api/v1/vehicles/{vid}/recalls", params={"q": "airbag"}).json()["total"] == 0
    )


def test_stale_data_served_when_nhtsa_down(client, nhtsa, db_session_factory):
    vid = _f150_id(client)
    client.get(f"/api/v1/vehicles/{vid}/recalls")
    with db_session_factory() as db:
        old = datetime.now(UTC) - timedelta(days=30)
        db.execute(update(SafetyFetch).values(fetched_at=old))
        db.commit()
    nhtsa.fail = True
    body = client.get(f"/api/v1/vehicles/{vid}/recalls").json()
    assert body["stale"] is True
    assert body["total"] == 1


def test_nhtsa_down_without_cache(client, nhtsa):
    nhtsa.fail = True
    r = client.get(f"/api/v1/vehicles/{_f150_id(client)}/recalls")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "upstream_unavailable"


def test_complaints_paginated_with_component_summary(client):
    vid = _f150_id(client)
    p1 = client.get(f"/api/v1/vehicles/{vid}/complaints", params={"limit": 10}).json()
    p2 = client.get(f"/api/v1/vehicles/{vid}/complaints", params={"limit": 10, "offset": 10}).json()
    assert p1["total"] == 30
    assert len(p1["items"]) == 10
    assert {c["odi_number"] for c in p1["items"]}.isdisjoint({c["odi_number"] for c in p2["items"]})
    assert p1["components"] == {"ENGINE": 15, "BRAKES": 15}
    brakes = client.get(f"/api/v1/vehicles/{vid}/complaints", params={"q": "brakes"}).json()
    assert brakes["total"] == 15


def test_unknown_vehicle_404(client):
    assert client.get("/api/v1/vehicles/9999/recalls").status_code == 404


# ---- TSB importer -----------------------------------------------------------

TSB_LINES = [
    # id, repl, added, bulletin, date, campaign, type, make, model, year, component, sys, sub, summary
    "10074303\t\t20160622\t15-NA-058\t20160801\t\tService Bulletin\tFORD\tF-150\t2015\tENGINE\t\t\t"
    "Engine ticking noise at idle.\n",
    "10074303\t\t20160622\t15-NA-058\t20160801\t\tService Bulletin\tFORD\tF-150\t2015\tENGINE:COOLING\t\t\t"
    "Engine ticking noise at idle.\n",
    "10074304\t\t20160622\t16-01\t20160901\t\tService Bulletin\tFORD\tF150 PICKUP\t2015\tBRAKES\t\t\t"
    "Brake squeal.\n",
    "10074305\t\t20160622\t99-X\t20160901\t\tOther\tCHEVROLET\tVOLT\t2017\tPOWER TRAIN\t\t\tAxle creak.\n",
    "garbage line\n",
]


def _zip(tmp_path):
    path = tmp_path / "TSBS_RECEIVED_TEST.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("TSBS_RECEIVED_TEST.txt", "".join(TSB_LINES))
    return path


def test_parse_tsb_line():
    rec = parse_tsb_line(TSB_LINES[0])
    assert rec["nhtsa_id"] == 10074303
    assert rec["bulletin_number"] == "15-NA-058"
    assert str(rec["bulletin_date"]) == "2016-08-01"
    assert (rec["make"], rec["model"], rec["year"]) == ("FORD", "F-150", 2015)
    assert parse_tsb_line("garbage line") is None


def test_tsb_import_only_known_models_and_idempotent(client, db_session_factory, tmp_path):
    vid = _f150_id(client)
    path = _zip(tmp_path)
    with db_session_factory() as db:
        result = import_tsbs(db, [path])
        assert result["tsbs_added"] == 1  # Chevy Volt and "F150 PICKUP" aren't models we know
        import_tsbs(db, [path])  # re-run: no duplicates
        assert len(db.scalars(select(Tsb)).all()) == 1
        assert db.scalars(select(DataImport)).all()[-1].status == "ok"

    body = client.get(f"/api/v1/vehicles/{vid}/tsbs").json()
    assert body["total"] == 1
    tsb = body["items"][0]
    assert tsb["bulletin_number"] == "15-NA-058"
    assert tsb["components"] == "ENGINE | ENGINE:COOLING"
    assert body["last_import"] is not None
    assert client.get(f"/api/v1/vehicles/{vid}").json()["counts"]["tsbs"] == 1


def test_tsb_import_all_models(db_session_factory, tmp_path):
    with db_session_factory() as db:
        assert import_tsbs(db, [_zip(tmp_path)], all_models=True)["tsbs_added"] == 3


def test_refresh_command(db_session_factory, nhtsa):
    with db_session_factory() as db:
        result = refresh_api(db, nhtsa, ["recalls", "complaints"])
        assert result["recalls"]["failed"] == 0
        assert result["recalls"]["vehicles"] == 8  # every seeded vehicle checked
