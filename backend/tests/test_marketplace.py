"""Parts marketplace: sellers, listings with fitment, prohibited-item rules, review queue,
messages, reports, seller verification, privacy."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.config import Settings, get_settings
from app.core import ratelimit
from app.db import get_db
from app.main import create_app
from app.modules.accounts.models import Role, User, UserStatus
from app.modules.marketplace.models import Listing, Seller
from app.modules.safety.nhtsa import get_nhtsa
from app.modules.vehicles.vpic import get_vpic
from tests.conftest import csrf, register

PW = "correct-horse-battery"
API = "/api/v1/market"


@pytest.fixture
def mclient(db_session_factory, vpic, nhtsa):
    ratelimit.reset()
    app = create_app(Settings(enable_marketplace=True))

    def _db():
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_vpic] = lambda: vpic
    app.dependency_overrides[get_nhtsa] = lambda: nhtsa
    with TestClient(app) as c:
        yield c


def user(client, factory, email, role=Role.user, status=UserStatus.active):
    register(client, email=email, password=PW, name=email.split("@")[0])
    with factory() as db:
        u = db.scalar(select(User).where(User.email == email))
        u.role, u.status = role, status
        db.commit()


def login(client, email):
    client.cookies.clear()
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text


def seller(client, name="Joe's Parts", **kw):
    body = {"seller_type": "recycler", "display_name": name, "city": "Dayton", "state": "oh",
            "postal_code": "45402", **kw}  # fmt: skip
    r = client.put(f"{API}/seller/me", json=body, headers=csrf(client))
    assert r.status_code == 200, r.text
    return r.json()


def f150(client):
    makes = client.get("/api/v1/vehicles/makes").json()
    ford = next(m["id"] for m in makes if m["name"] == "Ford")
    models = client.get("/api/v1/vehicles/models", params={"year": 2015, "make_id": ford}).json()
    model = next(m["id"] for m in models if m["name"] == "F-150")
    vid = client.get("/api/v1/vehicles/engines", params={"year": 2015, "model_id": model}).json()
    return ford, model, vid[0]["id"]


def listing(client, **kw):
    body = {
        "title": "Alternator, 2015 F-150",
        "description": "Pulled from a running truck, tested good.",
        "category": "electrical",
        "condition": "used",
        "price_cents": 8500,
        "shipping": "pickup_or_ships",
        "accept_rules": True,
        **kw,
    }
    return client.post(f"{API}/listings", json=body, headers=csrf(client))


def test_marketplace_is_off_by_default(client):
    assert client.get(f"{API}/categories").status_code == 404
    assert "marketplace" not in client.get("/api/v1/meta").json()["modules"]


def test_seller_listing_and_vehicle_fitment(mclient, db_session_factory):
    c = mclient
    assert "marketplace" in c.get("/api/v1/meta").json()["modules"]
    user(c, db_session_factory, "seller@example.com")
    assert listing(c).json()["error"]["code"] == "seller_profile_required"
    s = seller(c)
    assert s["state"] == "OH" and s["postal_code"] == "45402"

    ford, model, vid = f150(c)
    fit = [{"make_id": ford, "model_id": model, "year_from": 2015, "year_to": 2017}]
    r = listing(c, fitment=fit, part_number="FL3T-10300-AA")
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["status"] == "active" and item["is_owner"]
    assert item["fitment"][0]["model"] == "F-150"
    other = c.get("/api/v1/vehicles/makes").json()
    honda = next(m["id"] for m in other if m["name"] == "Honda")
    listing(
        c,
        title="Honda-only alternator",
        fitment=[{"make_id": honda, "year_from": 2010, "year_to": 2015}],
    )
    listing(c, title="Universal jumper cables", category="tools", condition="new")

    found = c.get(f"{API}/listings", params={"vehicle_id": vid}).json()
    titles = {i["title"] for i in found["items"]}
    assert titles == {"Alternator, 2015 F-150", "Universal jumper cables"}  # not the Honda part
    assert c.get(f"{API}/listings", params={"q": "fl3t10300"}).json()["total"] == 1  # part no.
    assert c.get(f"{API}/listings", params={"category": "tools"}).json()["total"] == 1

    # Public seller page never shows the ZIP code.
    c.cookies.clear()
    pub = c.get(f"{API}/sellers/{s['id']}").json()
    assert pub["postal_code"] is None and pub["active_listings"] == 3
    assert c.get(f"{API}/listings/{item['id']}").json()["is_owner"] is False


@pytest.mark.parametrize(
    ("kw", "code"),
    [
        ({"title": "EGR delete kit 6.7 Cummins"}, "listing_prohibited_defeat"),
        ({"description": "Brand new DPF delete pipe, off road only"}, "listing_prohibited_defeat"),
        ({"title": "O2 sensor simulator for cat"}, "listing_prohibited_defeat"),
        ({"title": "Driver airbag module", "category": "airbag_srs"}, "listing_prohibited_used_srs"),
        ({"title": "New driver airbag", "category": "airbag_srs", "condition": "new"},
         "listing_requires_verified_seller"),
        ({"title": "Catalytic converter", "category": "catalytic_converter", "condition": "new"},
         "listing_needs_emissions_compliance"),
        ({"title": "Catalytic converter", "category": "catalytic_converter", "condition": "new",
          "emissions_compliance": "carb"}, "listing_needs_carb_eo"),
        ({"title": "OEM catalytic converter", "category": "catalytic_converter"},
         "listing_requires_verified_seller"),
        ({"accept_rules": False}, "listing_rules_not_accepted"),
        ({"category": "rocket_parts"}, "listing_invalid"),
    ],
)  # fmt: skip
def test_prohibited_items_are_refused(mclient, db_session_factory, kw, code):
    user(mclient, db_session_factory, "sam@example.com")
    seller(mclient)
    r = listing(mclient, **kw)
    assert r.status_code in (403, 422), r.text
    assert r.json()["error"]["code"] == code


def test_legal_emissions_parts_allowed(mclient, db_session_factory):
    user(mclient, db_session_factory, "sam@example.com")
    seller(mclient)
    assert (
        listing(mclient, title="EGR valve, new", category="emissions", condition="new").status_code
        == 201
    )
    r = listing(mclient, title="Direct-fit converter", category="catalytic_converter",
                condition="new", emissions_compliance="carb", carb_eo_number="D-193-145")  # fmt: skip
    assert r.status_code == 201 and r.json()["carb_eo_number"] == "D-193-145"


def test_verified_recycler_can_list_used_converter(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "mod@example.com", role=Role.moderator)
    user(c, db_session_factory, "yard@example.com")
    seller(c, name="Valley Auto Recycling")
    used_cat = {"title": "OEM catalytic converter", "category": "catalytic_converter"}
    assert listing(c, **used_cat).status_code == 403
    v = c.post(f"{API}/seller/me/verifications", headers=csrf(c), json={
        "kind": "dismantler_license", "license_number": "DL-12345", "issuing_state": "OH",
        "business_name": "Valley Auto Recycling LLC"}).json()  # fmt: skip
    assert v["status"] == "pending"
    assert c.get(f"{API}/mod/queue").status_code == 403  # sellers can't review themselves

    login(c, "mod@example.com")
    q = c.get(f"{API}/mod/queue").json()
    assert q["verifications"][0]["license_number"] == "DL-12345"
    r = c.post(f"{API}/mod/verifications/{v['id']}", json={"action": "approve"}, headers=csrf(c))
    assert r.status_code == 200

    login(c, "yard@example.com")
    r = listing(c, **used_cat)
    assert r.status_code == 201 and r.json()["seller_verified"]


def test_new_sellers_listings_wait_for_review(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "mod@example.com", role=Role.moderator)
    user(c, db_session_factory, "newbie@example.com", status=UserStatus.probation)
    seller(c)
    item = listing(c).json()
    assert item["status"] == "pending"
    assert c.get(f"{API}/listings/{item['id']}").status_code == 200  # owner can see it
    c.cookies.clear()
    assert c.get(f"{API}/listings").json()["total"] == 0
    assert c.get(f"{API}/listings/{item['id']}").status_code == 404

    login(c, "mod@example.com")
    assert c.get(f"{API}/mod/queue").json()["pending_listings"][0]["id"] == item["id"]
    c.post(f"{API}/mod/listings/{item['id']}", json={"action": "approve"}, headers=csrf(c))
    c.cookies.clear()
    assert c.get(f"{API}/listings").json()["total"] == 1


def test_owner_controls_status_and_edits(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "other@example.com")
    user(c, db_session_factory, "sam@example.com")
    seller(c)
    item = listing(c).json()
    r = c.post(f"{API}/listings/{item['id']}/status", json={"status": "sold"}, headers=csrf(c))
    assert r.json()["status"] == "sold"
    assert c.get(f"{API}/listings").json()["total"] == 0  # sold items leave the search

    login(c, "other@example.com")
    body = {"title": "Hijacked", "description": "xxxxxxxxxxxx", "category": "other",
            "condition": "new", "price_cents": 1, "shipping": "ships", "accept_rules": True}  # fmt: skip
    r = c.put(f"{API}/listings/{item['id']}", json=body, headers=csrf(c))
    assert r.status_code == 404


def test_messages_between_buyer_and_seller(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "nosy@example.com")
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    seller(c, name="Dayton Pull-A-Part")
    item = listing(c).json()
    r = c.post(f"{API}/listings/{item['id']}/messages", json={"body": "hi"}, headers=csrf(c))
    assert r.json()["error"]["code"] == "cannot_message_self"

    login(c, "buyer@example.com")
    r = c.post(f"{API}/listings/{item['id']}/messages", json={"body": "Still available?"},
               headers=csrf(c))  # fmt: skip
    assert r.status_code == 201, r.text
    conv = r.json()
    assert conv["role"] == "buyer" and conv["other_name"] == "Dayton Pull-A-Part"

    login(c, "sam@example.com")
    inbox = c.get(f"{API}/conversations").json()
    assert inbox[0]["unread"] == 1 and inbox[0]["other_name"] == "buyer"
    c.post(f"{API}/conversations/{conv['id']}/messages", json={"body": "Yes, $85 firm."},
           headers=csrf(c))  # fmt: skip
    thread = c.get(f"{API}/conversations/{conv['id']}").json()
    assert [m["mine"] for m in thread["messages"]] == [False, True]
    assert c.get(f"{API}/conversations").json()[0]["unread"] == 0

    login(c, "nosy@example.com")
    assert c.get(f"{API}/conversations/{conv['id']}").status_code == 404
    assert c.get(f"{API}/conversations").json() == []


def test_reports_reach_moderators_and_removal_hides_listing(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "mod@example.com", role=Role.moderator)
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    seller(c)
    item = listing(c).json()

    login(c, "buyer@example.com")
    r = c.post(f"{API}/listings/{item['id']}/report", json={"reason": "stolen", "details": "VIN ground off"},
               headers=csrf(c))  # fmt: skip
    assert r.status_code == 201

    login(c, "mod@example.com")
    rep = c.get(f"{API}/mod/queue").json()["reports"][0]
    assert rep["reason"] == "stolen" and rep["listing_id"] == item["id"]
    c.post(f"{API}/mod/listings/{item['id']}", json={"action": "remove", "reason": "stolen"},
           headers=csrf(c))  # fmt: skip
    c.post(f"{API}/mod/reports/{rep['id']}", json={"action": "resolve"}, headers=csrf(c))
    assert c.get(f"{API}/mod/queue").json()["reports"] == []

    login(c, "sam@example.com")
    got = c.get(f"{API}/listings/{item['id']}").json()
    assert got["status"] == "removed" and got["status_reason"] == "stolen"
    body = {"title": "Alternator again", "description": "Pulled from a running truck.",
            "category": "electrical", "condition": "used", "price_cents": 1, "shipping": "ships",
            "accept_rules": True}  # fmt: skip
    r = c.put(f"{API}/listings/{item['id']}", json=body, headers=csrf(c))
    assert r.json()["error"]["code"] == "listing_removed"


def test_photos_must_belong_to_seller(mclient, db_session_factory, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "storage_local_dir", str(tmp_path))  # keep repo clean
    c = mclient
    user(c, db_session_factory, "amy@example.com")
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "PNG")
    pid = c.post("/api/v1/photos", files={"file": ("p.png", buf.getvalue(), "image/png")},
                 headers=csrf(c)).json()["id"]  # fmt: skip
    user(c, db_session_factory, "sam@example.com")
    seller(c)
    assert listing(c, photo_ids=[pid]).json()["error"]["code"] == "photo_not_found"

    login(c, "amy@example.com")
    seller(c, name="A's Parts")
    r = listing(c, photo_ids=[pid])
    assert r.status_code == 201 and r.json()["photo_url"] == f"/api/v1/photos/{pid}"


def test_export_and_delete_account(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "sam@example.com")
    seller(c)
    listing(c)
    data = c.get("/api/v1/me/export").json()
    assert data["marketplace"]["seller"]["postal_code"] == "45402"
    assert len(data["marketplace"]["listings"]) == 1

    assert c.delete("/api/v1/me", headers=csrf(c)).status_code == 204
    with db_session_factory() as db:
        assert db.scalar(select(Seller)) is None
        assert db.scalar(select(Listing)) is None


# ---- whole vehicles, watch list, message emails -------------------------------------

from app.core.email import OUTBOX  # noqa: E402
from app.modules.vehicles.vin import compute_check_digit  # noqa: E402


def _vin(serial: str) -> str:
    base = f"1FTEW1EG0FK{serial}"  # check digit (9th character) filled in below
    return base[:8] + compute_check_digit(base) + base[9:]


def vehicle_listing(client, **vehicle):
    ford = next(m["id"] for m in client.get("/api/v1/vehicles/makes").json() if m["name"] == "Ford")
    v = {"year": 2015, "make_id": ford, "title_status": "clean", "running": "runs_drives",
         "odometer": 148000, **vehicle}  # fmt: skip
    return listing(client, title="2015 F-150 XLT 3.5 EcoBoost", category="vehicle",
                   description="Runs and drives great, new tires.", price_cents=1650000,
                   shipping="pickup", vehicle=v)  # fmt: skip


def test_whole_vehicle_listing_uses_vin(mclient, db_session_factory, vpic):
    c = mclient
    user(c, db_session_factory, "sam@example.com")
    seller(c, seller_type="individual")
    assert vehicle_listing(c).json()["error"]["code"] == "listing_vin_required"
    good = _vin("A12345")
    bad = good[:8] + ("X" if good[8] != "X" else "0") + good[9:]  # wrong check digit
    assert vehicle_listing(c, vin=bad).json()["error"]["code"] == "listing_vin_invalid"

    r = vehicle_listing(c, vin=_vin("A12345"), model_id=None, year=1999)  # VIN wins
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["kind"] == "vehicle" and item["fits_all"] is False
    veh = item["vehicle"]
    assert (veh["year"], veh["make"], veh["model"]) == (2015, "Ford", "F-150")
    assert veh["vehicle_id"] and veh["vin"] == _vin("A12345")
    # Same VIN can't be listed twice at once.
    assert vehicle_listing(c, vin=_vin("A12345")).json()["error"]["code"] == "listing_vin_duplicate"

    # Parts search and vehicle search are separate; filters work.
    listing(c)  # an alternator
    assert c.get(f"{API}/listings", params={"kind": "vehicle"}).json()["total"] == 1
    assert c.get(f"{API}/listings", params={"kind": "part"}).json()["total"] == 1
    got = c.get(f"{API}/listings", params={"kind": "vehicle", "year_min": 2014, "year_max": 2016,
                                           "title_status": "clean", "q": "f-150"}).json()  # fmt: skip
    assert got["total"] == 1
    assert (
        c.get(f"{API}/listings", params={"kind": "vehicle", "running": "not_running"}).json()[
            "total"
        ]
        == 0
    )

    # Pre-1981 classics have no 17-character VIN.
    r = vehicle_listing(c, year=1965, title_status="salvage", running="not_running")
    assert r.status_code == 201 and r.json()["vehicle"]["vin"] is None

    # Yard facts (row/stock #, arrival date, keys, damage, lien sale) show on the search card.
    r = vehicle_listing(c, vin=_vin("A12399"), stock_number="Row 4 · #A1043",
                        arrived_on="2026-11-01", has_keys=False, damage="Front end",
                        lien_sale_after="2026-11-20")  # fmt: skip
    assert r.status_code == 201, r.text
    card = next(i for i in c.get(f"{API}/listings").json()["items"] if i["id"] == r.json()["id"])
    v = card["vehicle"]
    assert (
        v["stock_number"],
        v["arrived_on"],
        v["has_keys"],
        v["damage"],
        v["lien_sale_after"],
    ) == ("Row 4 · #A1043", "2026-11-01", False, "Front end", "2026-11-20")


def test_private_seller_vehicle_limit(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "sam@example.com")
    seller(c, seller_type="individual")
    for i in range(5):
        assert vehicle_listing(c, vin=_vin(f"B1234{i}")).status_code == 201
    r = vehicle_listing(c, vin=_vin("B12399"))
    assert r.status_code == 403 and r.json()["error"]["code"] == "listing_vehicle_limit"


def test_watch_list(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    seller(c)
    item = listing(c).json()
    login(c, "buyer@example.com")
    assert c.post(f"{API}/listings/{item['id']}/save", headers=csrf(c)).status_code == 204
    c.post(f"{API}/listings/{item['id']}/save", headers=csrf(c))  # twice is fine
    saved = c.get(f"{API}/saved").json()
    assert [s["id"] for s in saved] == [item["id"]] and saved[0]["saved"]
    assert c.get(f"{API}/listings").json()["items"][0]["saved"] is True
    c.delete(f"{API}/listings/{item['id']}/save", headers=csrf(c))
    assert c.get(f"{API}/saved").json() == []


def test_message_email_is_one_per_unread_batch(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    seller(c)
    item = listing(c).json()
    login(c, "buyer@example.com")
    OUTBOX.clear()
    conv = c.post(f"{API}/listings/{item['id']}/messages", json={"body": "Is it still there? Call me 555-0100"},
                  headers=csrf(c)).json()  # fmt: skip
    c.post(f"{API}/conversations/{conv['id']}/messages", json={"body": "Hello?"}, headers=csrf(c))
    mails = [m.get_content() for m in OUTBOX if m["To"] == "sam@example.com"]
    assert len(mails) == 1  # second message while the first is unread: no extra email
    assert "555-0100" not in mails[0]  # the message text never goes out by email
    assert f"/market/messages/{conv['id']}" in mails[0]


# ---- distance search, reviews --------------------------------------------------------

from app.modules.marketplace import zips  # noqa: E402
from app.modules.marketplace.models import ZipPoint  # noqa: E402


def test_zip_file_loads_once(db_session_factory):
    with db_session_factory() as db:
        n = zips.load(db)
        assert n > 30000  # every US ZIP code area
        assert zips.load(db) == 0
        dayton, cincy = db.get(ZipPoint, "45402"), db.get(ZipPoint, "45202")
        assert 40 < zips.miles(dayton, cincy) < 55  # Dayton -> Cincinnati is roughly 47 miles


def test_search_near_zip(mclient, db_session_factory):
    c = mclient
    with db_session_factory() as db:
        db.add_all([ZipPoint(zip="45402", lat=39.7589, lon=-84.1916),
                    ZipPoint(zip="45202", lat=39.1072, lon=-84.5021),
                    ZipPoint(zip="90012", lat=34.0614, lon=-118.2385)])  # fmt: skip
        db.commit()
    user(c, db_session_factory, "dayton@example.com")
    seller(c, name="Dayton Parts", postal_code="45402")
    listing(c, title="Dayton alternator")
    user(c, db_session_factory, "cincy@example.com")
    seller(c, name="Cincy Parts", city="Cincinnati", postal_code="45202")
    listing(c, title="Cincinnati alternator")
    user(c, db_session_factory, "la@example.com")
    seller(c, name="LA Parts", city="Los Angeles", state="CA", postal_code="90012")
    listing(c, title="LA alternator")

    near = c.get(f"{API}/listings", params={"near_zip": "45402", "radius_mi": 25}).json()
    assert [i["title"] for i in near["items"]] == ["Dayton alternator"]
    assert near["items"][0]["distance_mi"] == 0
    wider = c.get(
        f"{API}/listings", params={"near_zip": "45402", "radius_mi": 100, "sort": "nearest"}
    ).json()
    assert [i["title"] for i in wider["items"]] == ["Dayton alternator", "Cincinnati alternator"]
    assert 40 < wider["items"][1]["distance_mi"] < 55
    assert (
        c.get(f"{API}/listings", params={"near_zip": "00000"}).json()["error"]["code"]
        == "zip_not_found"
    )


def test_reviews_only_from_real_buyers(mclient, db_session_factory):
    c = mclient
    user(c, db_session_factory, "mod@example.com", role=Role.moderator)
    user(c, db_session_factory, "lurker@example.com")
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    s = seller(c)
    item = listing(c).json()

    login(c, "buyer@example.com")
    conv = c.post(
        f"{API}/listings/{item['id']}/messages", json={"body": "I'll take it"}, headers=csrf(c)
    ).json()
    review = {"rating": 5, "comment": "Part was exactly as described."}
    assert (
        c.post(f"{API}/listings/{item['id']}/review", json=review, headers=csrf(c)).status_code
        == 403
    )

    login(c, "sam@example.com")
    c.post(
        f"{API}/conversations/{conv['id']}/messages",
        json={"body": "Sold, see you at 5"},
        headers=csrf(c),
    )
    c.post(f"{API}/listings/{item['id']}/status", json={"status": "sold"}, headers=csrf(c))
    # Sellers can't review themselves.
    assert (
        c.post(f"{API}/listings/{item['id']}/review", json=review, headers=csrf(c)).status_code
        == 403
    )

    login(c, "lurker@example.com")  # never talked to the seller
    r = c.post(f"{API}/listings/{item['id']}/review", json=review, headers=csrf(c))
    assert r.json()["error"]["code"] == "review_not_allowed"

    login(c, "buyer@example.com")
    assert c.get(f"{API}/listings/{item['id']}/can-review").json()["can_review"] is True
    r = c.post(f"{API}/listings/{item['id']}/review", json=review, headers=csrf(c))
    assert r.status_code == 201, r.text
    assert (
        c.post(f"{API}/listings/{item['id']}/review", json=review, headers=csrf(c)).json()["error"][
            "code"
        ]
        == "review_exists"
    )
    pub = c.get(f"{API}/sellers/{s['id']}").json()
    assert (pub["rating"], pub["rating_count"]) == (5.0, 1)

    login(c, "mod@example.com")
    c.post(f"{API}/mod/reviews/{r.json()['id']}/hide", headers=csrf(c))
    assert c.get(f"{API}/sellers/{s['id']}/reviews").json() == []
    assert c.get(f"{API}/sellers/{s['id']}").json()["rating_count"] == 0


def test_demo_stock_is_labeled_and_removable(db_session_factory, monkeypatch):
    from app.modules.marketplace import demo
    from app.modules.vehicles.vin import check_digit_valid

    with db_session_factory() as db:
        assert demo.load(db) == len(demo.LISTINGS)
        assert demo.load(db) == 0  # idempotent
        db.commit()
        rows = db.scalars(select(Listing)).all()
        assert rows and all(r.title.startswith("DEMO —") for r in rows)
        newest = sorted(rows, key=lambda r: r.created_at, reverse=True)  # the market's default sort
        assert [r.title for r in newest] == [
            t[0] for t in demo.LISTINGS
        ]  # vehicles, then transmissions
        seller = db.scalar(select(Seller))
        assert seller.display_name == demo.DEMO_NAME and seller.seller_type.value == "recycler"
        for *_head, vin, _miles, _running, _title in demo.DONORS.values():
            assert check_digit_valid(vin) and vin.endswith("000000")
        parts = [r for r in rows if r.kind.value == "part"]
        assert all(r.source_vin and r.mileage for r in parts)  # donor VIN + mileage on every part
        vehicles = [r.vehicle for r in rows if r.vehicle]
        assert all(v.stock_number and v.arrived_on for v in vehicles)
        assert sum(1 for v in vehicles if v.lien_sale_after) == 1  # one tow-yard lien-sale example
        assert demo.remove(db)
        db.commit()
        assert db.scalar(select(Listing)) is None and db.scalar(select(Seller)) is None
