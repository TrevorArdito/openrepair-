"""Community guides & specs: creating, editing, review, verification, votes, reports,
labor times and photos."""

import io

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.modules.accounts.models import Role, User, UserStatus
from tests.conftest import csrf, register

PROCEDURE = {
    "summary": "Replace front pads and rotors.",
    "difficulty": 2,
    "tools": ["Jack and stands", "Torque wrench"],
    "steps": [
        {"text": "Loosen lug nuts, raise and support the vehicle."},
        {
            "text": "Remove caliper bracket bolts.",
            "torque_nm": 150,
            "torque_label": "Bracket bolts",
        },
    ],
}
TORQUE = {
    "component": "Wheel lug nuts",
    "stages": [{"type": "torque", "value_nm": 204}],
    "thread_condition": "dry",
    "sources": [{"type": "owner_manual", "citation": "Owner's manual, wheels section"}],
}


def login_as(client, db_session_factory, email, role=Role.user, status=None):
    register(client, email=email, name=email.split("@")[0])
    with db_session_factory() as db:
        u = db.scalar(select(User).where(User.email == email))
        u.role = role
        if status:
            u.status = status
        elif role != Role.user:
            u.status = UserStatus.active
        db.commit()


def f150(client):
    makes = client.get("/api/v1/vehicles/makes").json()
    ford = next(m["id"] for m in makes if m["name"] == "Ford")
    models = client.get("/api/v1/vehicles/models", params={"year": 2015, "make_id": ford}).json()
    model = next(m["id"] for m in models if m["name"] == "F-150")
    vid = client.get("/api/v1/vehicles/engines", params={"year": 2015, "model_id": model}).json()[
        0
    ]["id"]
    return ford, model, vid


def create(client, kind="procedure", data=None, tags=None, title="Front brake job"):
    return client.post(
        "/api/v1/entries",
        json={"kind": kind, "title": title, "data": data or PROCEDURE, "tags": tags or {}},
        headers=csrf(client),
    )


# ---- creating & review ---------------------------------------------------------


def test_new_user_contribution_waits_for_review(client, db_session_factory):
    login_as(client, db_session_factory, "new@example.com")
    r = create(client)
    assert r.status_code == 201, r.text
    entry = r.json()
    assert entry["status"] == "pending"
    eid = entry["id"]
    assert client.get(f"/api/v1/entries/{eid}").status_code == 200  # author can see it

    client.cookies.clear()
    assert client.get(f"/api/v1/entries/{eid}").status_code == 404  # public can't yet
    assert client.get("/api/v1/entries").json()["total"] == 0

    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    queue = client.get("/api/v1/mod/queue").json()
    rev_id = queue["pending_revisions"][0]["id"]
    assert (
        client.post(f"/api/v1/mod/revisions/{rev_id}/approve", headers=csrf(client)).status_code
        == 200
    )

    client.cookies.clear()
    assert client.get(f"/api/v1/entries/{eid}").json()["status"] == "published"


def test_probation_ends_after_three_approved(client, db_session_factory):
    login_as(client, db_session_factory, "new@example.com")
    ids = [create(client, title=f"Guide {i}").json()["id"] for i in range(3)]
    client.cookies.clear()
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    for rev in client.get("/api/v1/mod/queue").json()["pending_revisions"]:
        client.post(f"/api/v1/mod/revisions/{rev['id']}/approve", headers=csrf(client))
    with db_session_factory() as db:
        u = db.scalar(select(User).where(User.email == "new@example.com"))
        assert u.status == UserStatus.active
    assert len(ids) == 3


def test_rejected_new_entry_is_hidden(client, db_session_factory):
    login_as(client, db_session_factory, "new@example.com")
    eid = create(client).json()["id"]
    client.cookies.clear()
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    rev = client.get("/api/v1/mod/queue").json()["pending_revisions"][0]["id"]
    client.post(f"/api/v1/mod/revisions/{rev}/reject", headers=csrf(client))
    client.cookies.clear()
    assert client.get(f"/api/v1/entries/{eid}").status_code == 404


def test_pro_publishes_directly(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    body = create(client).json()
    assert body["status"] == "published"
    assert body["revision"]["number"] == 1
    assert body["revision"]["author"]["display_name"] == "pro"


# ---- editing (required tests) ---------------------------------------------------


def test_edit_creates_revision_and_history(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    new = {**PROCEDURE, "summary": "Replace front pads and rotors, both sides."}
    r = client.post(
        f"/api/v1/entries/{eid}/revisions",
        json={
            "base_revision": 1,
            "title": "Front brake job (pads + rotors)",
            "data": new,
            "edit_summary": "Clarified scope",
        },  # fmt: skip
        headers=csrf(client),
    )
    assert r.status_code == 200, r.text
    assert r.json()["revision"]["number"] == 2
    assert r.json()["title"] == "Front brake job (pads + rotors)"
    history = client.get(f"/api/v1/entries/{eid}/revisions").json()
    assert [h["number"] for h in history] == [2, 1]
    assert history[0]["edit_summary"] == "Clarified scope"
    assert history[1]["data"]["summary"] == "Replace front pads and rotors."


def test_edit_conflict(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    edit = {"base_revision": 1, "title": "A", "data": PROCEDURE, "edit_summary": "one"}
    assert (
        client.post(
            f"/api/v1/entries/{eid}/revisions",
            json={**edit, "title": "Edit one"},
            headers=csrf(client),
        ).status_code
        == 200
    )
    stale = client.post(
        f"/api/v1/entries/{eid}/revisions", json={**edit, "title": "Edit two"}, headers=csrf(client)
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "edit_conflict"
    assert stale.json()["error"]["details"]["current_revision"] == 2


def test_edit_by_probation_user_is_pending(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    client.cookies.clear()
    login_as(client, db_session_factory, "new@example.com")
    r = client.post(
        f"/api/v1/entries/{eid}/revisions",
        json={"base_revision": 1, "title": "Vandalized", "data": PROCEDURE, "edit_summary": "x"},
        headers=csrf(client),
    )
    body = r.json()
    assert body["title"] == "Front brake job"  # public version unchanged
    assert body["pending_revisions"] == 1


def test_edit_requires_login_and_csrf(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    edit = {"base_revision": 1, "title": "x y", "data": PROCEDURE, "edit_summary": "x"}
    assert client.post(f"/api/v1/entries/{eid}/revisions", json=edit).status_code == 403
    client.cookies.clear()
    assert client.post(f"/api/v1/entries/{eid}/revisions", json=edit).status_code == 401


def test_invalid_content_rejected(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    no_source = {k: v for k, v in TORQUE.items() if k != "sources"}
    r = create(client, "torque_spec", no_source, title="Lug nuts")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "entry_invalid"
    angle_first = {**TORQUE, "stages": [{"type": "angle", "degrees": 90}]}
    assert create(client, "torque_spec", angle_first, title="Lug nuts").status_code == 422
    no_steps = {**PROCEDURE, "steps": []}
    assert create(client, "procedure", no_steps).status_code == 422
    extra = {**PROCEDURE, "evil": "<script>"}
    assert create(client, "procedure", extra).status_code == 422


def test_revert(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    client.post(f"/api/v1/entries/{eid}/revisions",
                json={"base_revision": 1, "title": "Bad edit", "data": PROCEDURE, "edit_summary": "oops"},
                headers=csrf(client))  # fmt: skip
    r = client.post(f"/api/v1/entries/{eid}/revert/1", headers=csrf(client)).json()
    assert r["title"] == "Front brake job"
    assert r["revision"]["number"] == 3
    assert r["revision"]["edit_summary"] == "Reverted to version 1"


# ---- verification ----------------------------------------------------------------


def test_verification_tied_to_revision(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client, "torque_spec", TORQUE, title="Lug nut torque").json()["id"]
    body = client.post(f"/api/v1/entries/{eid}/verify", headers=csrf(client)).json()
    assert body["verification"]["state"] == "verified"
    assert body["safety_critical"] is True  # torque specs always show the disclaimer
    client.post(f"/api/v1/entries/{eid}/revisions",
                json={"base_revision": 1, "title": "Lug nut torque", "data": {**TORQUE, "notes": "Re-check after 50 miles"},
                      "edit_summary": "note"},
                headers=csrf(client))  # fmt: skip
    body = client.get(f"/api/v1/entries/{eid}").json()
    assert body["verification"]["state"] == "verified_older"
    assert body["verification"]["revision_number"] == 1


def test_regular_user_cannot_verify(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    client.cookies.clear()
    login_as(client, db_session_factory, "joe@example.com", status=UserStatus.active)
    assert client.post(f"/api/v1/entries/{eid}/verify", headers=csrf(client)).status_code == 403


# ---- tags, vehicle matching, codes -------------------------------------------------


def test_vehicle_matching_and_generic_entries(client, db_session_factory):
    ford, model, vid = f150(client)
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    tags = {"applies_to": [{"make_id": ford, "model_id": model, "year_from": 2015, "year_to": 2017}],
            "systems": ["brakes.disc"], "dtcs": ["p0420"]}  # fmt: skip
    specific = create(client, tags=tags, title="F-150 front brakes").json()
    generic = create(client, title="Brake job basics").json()
    assert specific["safety_critical"] is True  # brakes are safety-critical
    assert specific["revision"]["tags"]["dtcs"] == ["P0420"]

    listed = client.get("/api/v1/entries", params={"vehicle_id": vid}).json()
    assert [i["id"] for i in listed["items"]] == [specific["id"], generic["id"]]  # specific first
    assert listed["items"][1]["generic"] is True
    only = client.get(
        "/api/v1/entries", params={"vehicle_id": vid, "include_generic": False}
    ).json()
    assert only["total"] == 1

    # "brakes" includes sub-systems like brakes.disc; the generic guide has no system tag.
    assert client.get("/api/v1/entries", params={"system": "brakes"}).json()["total"] == 1
    assert client.get("/api/v1/entries", params={"system": "engine"}).json()["total"] == 0
    related = client.get("/api/v1/dtcs/P0420").json()["related_entries"]
    assert [r["id"] for r in related] == [specific["id"]]
    profile = client.get(f"/api/v1/vehicles/{vid}").json()
    assert profile["counts"]["guides"] == 1


def test_unknown_system_or_vehicle_rejected(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    assert (
        create(client, tags={"systems": ["flux_capacitor"]}).json()["error"]["code"]
        == "unknown_system"
    )
    bad = {"applies_to": [{"make_id": 99999, "year_from": 2015, "year_to": 2016}]}
    assert create(client, tags=bad).status_code == 404


# ---- votes, reports, labor ------------------------------------------------------------


def test_votes(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    assert (
        client.post(
            f"/api/v1/entries/{eid}/vote", json={"value": 1}, headers=csrf(client)
        ).status_code
        == 409
    )
    client.cookies.clear()
    login_as(client, db_session_factory, "joe@example.com")
    assert (
        client.post(f"/api/v1/entries/{eid}/vote", json={"value": 1}, headers=csrf(client)).json()[
            "score"
        ]
        == 1
    )
    body = client.post(
        f"/api/v1/entries/{eid}/vote", json={"value": -1}, headers=csrf(client)
    ).json()
    assert body["score"] == -1 and body["my_vote"] == -1


def test_report_wrong_info_flow(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client, "torque_spec", TORQUE, title="Lug nut torque").json()["id"]
    client.cookies.clear()
    login_as(client, db_session_factory, "joe@example.com")
    r = client.post(f"/api/v1/entries/{eid}/reports", json={"reason": "wrong_info", "details": "Should be 165 N·m"},
                    headers=csrf(client))  # fmt: skip
    assert r.status_code == 201
    again = client.post(
        f"/api/v1/entries/{eid}/reports", json={"reason": "wrong_info"}, headers=csrf(client)
    )
    assert again.status_code == 409
    assert client.get(f"/api/v1/entries/{eid}").json()["open_reports"] == 1
    assert client.get("/api/v1/mod/queue").status_code == 403

    client.cookies.clear()
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    rep = client.get("/api/v1/mod/queue").json()["reports"][0]
    assert rep["reason"] == "wrong_info"
    client.post(
        f"/api/v1/mod/reports/{rep['id']}/resolve", params={"note": "Fixed"}, headers=csrf(client)
    )
    assert client.get(f"/api/v1/entries/{eid}").json()["open_reports"] == 0


def test_labor_time_from_several_sources(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    data = {"job": "Replace front pads and rotors", "includes": ["Both sides"]}
    eid = create(client, "labor_time", data, title="Front brakes labor").json()["id"]
    for basis, hours, rust in [("warranty", 1.2, "none"), ("flat_rate", 1.5, "none"), ("flat_rate", 1.7, "none"),
                               ("pro_actual", 1.0, "none"), ("pro_actual", 2.0, "heavy"), ("diy_actual", 3.0, "none")]:  # fmt: skip
        r = client.post(f"/api/v1/entries/{eid}/labor", json={"basis": basis, "hours": hours, "rust": rust},
                        headers=csrf(client))  # fmt: skip
        assert r.status_code == 200, r.text
    labor = client.get(f"/api/v1/entries/{eid}").json()["labor"]
    assert labor["flat_rate"]["none"] == {"reports": 2, "median": 1.6, "min": 1.5, "max": 1.7}
    assert labor["pro_actual"]["heavy"]["median"] == 2.0
    assert labor["diy_actual"]["light"] == {"reports": 0}
    bad = client.post(
        f"/api/v1/entries/{eid}/labor",
        json={"basis": "pro_actual", "hours": 0},
        headers=csrf(client),
    )
    assert bad.status_code == 422


# ---- photos -----------------------------------------------------------------------------


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_local_dir", str(tmp_path))
    return tmp_path


def test_photo_upload_strips_location_and_reencodes(client, db_session_factory, uploads):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    img = Image.new("RGB", (3000, 1500), "red")
    exif = Image.Exif()
    exif[0x8825] = {2: (40.0, 0.0, 0.0)}  # GPS info
    exif[0x010F] = "SecretCam"
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    r = client.post(
        "/api/v1/photos",
        files={"file": ("p.jpg", buf.getvalue(), "image/jpeg")},
        headers=csrf(client),
    )
    assert r.status_code == 201, r.text
    photo = r.json()
    assert (photo["width"], photo["height"]) == (2000, 1000)
    got = client.get(photo["url"])
    saved = Image.open(io.BytesIO(got.content))
    assert saved.format == "WEBP"
    assert not saved.getexif()  # no GPS, no camera info

    data = {**PROCEDURE, "steps": [{"text": "Look here", "photo_id": photo["id"]}]}
    assert create(client, data=data).status_code == 201


def test_photo_rejects_non_images(client, db_session_factory, uploads):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    r = client.post(
        "/api/v1/photos",
        files={"file": ("x.jpg", b"<?php evil ?>", "image/jpeg")},
        headers=csrf(client),
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "photo_bad_type"


def test_cannot_use_someone_elses_photo(client, db_session_factory, uploads):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "PNG")
    pid = client.post("/api/v1/photos", files={"file": ("p.png", buf.getvalue(), "image/png")},
                      headers=csrf(client)).json()["id"]  # fmt: skip
    client.cookies.clear()
    login_as(client, db_session_factory, "pro2@example.com", Role.pro)
    data = {**PROCEDURE, "steps": [{"text": "x", "photo_id": pid}]}
    assert create(client, data=data).json()["error"]["code"] == "photo_not_found"


# ---- moderation & privacy ------------------------------------------------------------------


def test_hidden_entry_not_public(client, db_session_factory):
    login_as(client, db_session_factory, "mod@example.com", Role.moderator)
    eid = create(client).json()["id"]
    client.post(f"/api/v1/mod/entries/{eid}/hide", headers=csrf(client))
    client.cookies.clear()
    assert client.get(f"/api/v1/entries/{eid}").status_code == 404


def test_deleted_author_shown_as_former_member(client, db_session_factory):
    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client).json()["id"]
    client.delete("/api/v1/me", headers=csrf(client))
    client.cookies.clear()
    body = client.get(f"/api/v1/entries/{eid}").json()
    assert body["revision"]["author"]["display_name"] == "Former member"
    with db_session_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
