"""Unified search."""

from app.modules.accounts.models import Role
from tests.conftest import csrf
from tests.test_community import PROCEDURE, create, f150, login_as


def s(client, q, **params):
    r = client.get("/api/v1/search", params={"q": q, **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_vin_is_recognized(client):
    body = s(client, "1hgcm82633a004352")
    assert body["vin"] == {"vin": "1HGCM82633A004352", "check_digit_valid": True}
    assert body["vehicles"] == []


def test_code_search(client):
    body = s(client, "p0420")
    assert body["codes"][0]["code"] == "P0420"
    prefix = s(client, "P030")
    assert {"P0300", "P0301"} <= {c["code"] for c in prefix["codes"]}
    unknown = s(client, "P1450")  # valid but not written up yet -> still offered
    assert unknown["codes"][0] == {"code": "P1450", "title": None, "severity": None}


def test_code_search_by_words(client):
    codes = {c["code"] for c in s(client, "catalytic converter")["codes"]}
    assert "P0420" in codes


def test_vehicle_search_understands_common_typing(client, vpic):
    f150(client)  # loads Ford models for 2015
    for q in ["2015 f150", "ford f-150", "F150 2015", "2015 ford f 150"]:
        body = s(client, q)
        assert body["vehicles"], q
        top = body["vehicles"][0]
        assert (top["make"], top["model"]) == ("Ford", "F-150"), q
    assert s(client, "2015 f150")["vehicles"][0]["year"] == 2015
    assert 2015 in s(client, "f150")["vehicles"][0]["years"]
    honda = s(client, "chevy")["vehicles"]
    assert all(v["make"] == "Chevrolet" for v in honda)


def test_entry_search_all_words_and_vehicle_scope(client, db_session_factory):
    ford, model, vid = f150(client)
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    tags = {
        "applies_to": [{"make_id": ford, "model_id": model, "year_from": 2015, "year_to": 2017}]
    }
    specific = create(client, tags=tags, title="F-150 front brake job").json()
    general = create(
        client, title="Brake bleeding basics", data={**PROCEDURE, "summary": "Bleed the brakes."}
    ).json()
    other = create(
        client,
        tags={
            "applies_to": [{"make_id": ford, "model_id": model, "year_from": 2009, "year_to": 2010}]
        },
        title="Old F-150 brake job",
    ).json()

    ids = [e["id"] for e in s(client, "brake")["entries"]]
    assert set(ids) == {specific["id"], general["id"], other["id"]}
    assert [e["id"] for e in s(client, "front brake job f-150")["entries"]][0] == specific["id"]
    # Words from inside the steps are searchable too
    assert specific["id"] in [e["id"] for e in s(client, "caliper bracket")["entries"]]
    scoped = [e["id"] for e in s(client, "brake", vehicle_id=vid)["entries"]]
    assert other["id"] not in scoped and specific["id"] in scoped and general["id"] in scoped

    # Edits update what search finds
    client.post(
        f"/api/v1/entries/{general['id']}/revisions",
        json={
            "base_revision": 1,
            "title": "Clutch hydraulic bleeding",
            "data": PROCEDURE,
            "edit_summary": "retitle",
        },
        headers=csrf(client),
    )
    assert general["id"] in [e["id"] for e in s(client, "clutch")["entries"]]


def test_recalls_searchable_within_vehicle_and_by_campaign(client):
    _, _, vid = f150(client)
    client.get(f"/api/v1/vehicles/{vid}/recalls")  # loads the (fake) NHTSA recall
    scoped = s(client, "heater", vehicle_id=vid)
    assert scoped["recalls"][0]["campaign_number"] == "18V894000"
    assert scoped["vehicle"]["id"] == vid
    assert s(client, "18V-894")["recalls"][0]["campaign_number"] == "18V894000"


def test_type_filter_and_validation(client):
    body = s(client, "p0420", types=["entries"])
    assert body["codes"] == []
    assert client.get("/api/v1/search", params={"q": ""}).status_code == 422
    assert client.get("/api/v1/search", params={"q": "x" * 101}).status_code == 422
    assert (
        client.get("/api/v1/search", params={"q": "brake", "vehicle_id": 99999}).status_code == 404
    )


def test_word_endings_match():
    from app.modules.search.service import stem, words

    assert stem("misfire") == stem("misfiring") == "misfir"
    assert stem("brakes") == "brak" and "brak" in "braking"
    assert words("P0420 2015") == ["p0420", "2015"]  # codes and years untouched


def test_misfire_search_puts_random_misfire_first(client):
    codes = [c["code"] for c in s(client, "misfire")["codes"]]
    assert codes[0] == "P0300"
