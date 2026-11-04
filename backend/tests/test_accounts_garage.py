from tests.conftest import csrf, register


def test_register_login_me_logout(client):
    register(client)
    me = client.get("/api/v1/me").json()
    assert me["email"] == "tech@example.com"
    assert me["role"] == "user"
    assert me["status"] == "probation"
    assert "password_hash" not in me

    assert client.post("/api/v1/auth/logout", headers=csrf(client)).status_code == 204
    client.cookies.clear()
    assert client.get("/api/v1/me").status_code == 401

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "TECH@example.com", "password": "correct-horse-battery"},
    )
    assert r.status_code == 200


def test_login_wrong_password(client):
    register(client)
    client.cookies.clear()
    r = client.post("/api/v1/auth/login", json={"email": "tech@example.com", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


def test_register_rules(client):
    base = {"email": "a@example.com", "password": "long-enough-pw", "display_name": "Al"}
    assert (
        client.post("/api/v1/auth/register", json={**base, "accept_terms": False}).json()["error"][
            "code"
        ]
        == "terms_not_accepted"
    )
    honeypot = {**base, "accept_terms": True, "website": "http://spam.example"}
    assert client.post("/api/v1/auth/register", json=honeypot).status_code == 400
    short = {**base, "accept_terms": True, "password": "short"}
    assert client.post("/api/v1/auth/register", json=short).status_code == 422
    register(client, email="a@example.com")
    client.cookies.clear()
    dup = client.post("/api/v1/auth/register", json={**base, "accept_terms": True})
    assert dup.status_code == 409


def test_password_is_hashed_with_argon2(client, db_session_factory):
    from sqlalchemy import select

    from app.modules.accounts.models import User

    register(client)
    with db_session_factory() as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")


def test_login_rate_limited(client):
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "x"})
    r = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "x"})
    assert r.status_code == 429


def test_preferences_update(client):
    register(client)
    r = client.patch(
        "/api/v1/me", json={"unit_pref": "metric", "theme": "dark"}, headers=csrf(client)
    )
    assert r.json()["unit_pref"] == "metric"
    bad = client.patch("/api/v1/me", json={"unit_pref": "furlongs"}, headers=csrf(client))
    assert bad.status_code == 422


def _a_vehicle_id(client):
    return client.get("/api/v1/vehicles/decode/1FTEW1EG5FFA00000").json()["vehicle"]["id"]


def test_garage_requires_login(client):
    assert client.get("/api/v1/garage").status_code == 401


def test_garage_requires_csrf(client):
    register(client)
    r = client.post("/api/v1/garage", json={"vehicle_id": _a_vehicle_id(client)})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"


def test_garage_crud(client):
    register(client)
    vid = _a_vehicle_id(client)
    r = client.post(
        "/api/v1/garage",
        json={"vehicle_id": vid, "nickname": "Shop truck", "vin": "1ftew1eg5ffa00000"},
        headers=csrf(client),
    )
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["vin"] == "1FTEW1EG5FFA00000"
    assert item["vehicle"]["label"] == "2015 Ford F-150 3.5L V6 Turbo"

    r = client.patch(
        f"/api/v1/garage/{item['id']}", json={"notes": "Needs plugs"}, headers=csrf(client)
    )
    assert r.json()["notes"] == "Needs plugs"
    assert len(client.get("/api/v1/garage").json()) == 1
    assert client.delete(f"/api/v1/garage/{item['id']}", headers=csrf(client)).status_code == 204
    assert client.get("/api/v1/garage").json() == []


def test_garage_rejects_bad_vin(client):
    register(client)
    r = client.post(
        "/api/v1/garage",
        json={"vehicle_id": _a_vehicle_id(client), "vin": "BAD"},
        headers=csrf(client),
    )
    assert r.status_code == 422


def test_garage_is_private(client):
    register(client, email="one@example.com")
    item = client.post(
        "/api/v1/garage", json={"vehicle_id": _a_vehicle_id(client)}, headers=csrf(client)
    ).json()
    client.cookies.clear()
    register(client, email="two@example.com")
    assert client.get("/api/v1/garage").json() == []
    r = client.delete(f"/api/v1/garage/{item['id']}", headers=csrf(client))
    assert r.status_code == 404


def test_export_and_delete_account(client):
    register(client)
    client.post("/api/v1/garage", json={"vehicle_id": _a_vehicle_id(client)}, headers=csrf(client))
    export = client.get("/api/v1/me/export").json()
    assert export["account"]["email"] == "tech@example.com"
    assert len(export["garage"]) == 1
    assert client.delete("/api/v1/me", headers=csrf(client)).status_code == 204
    client.cookies.clear()
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "tech@example.com", "password": "correct-horse-battery"},
    )
    assert r.status_code == 401
