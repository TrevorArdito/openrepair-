def _make_id(client, name):
    makes = client.get("/api/v1/vehicles/makes").json()
    return next(m["id"] for m in makes if m["name"] == name)


def test_health_and_meta(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    meta = client.get("/api/v1/meta").json()
    assert meta["source_code_url"].startswith("https://")
    assert "hardware" not in meta["modules"]  # off by default


def test_years_start_at_1981(client):
    years = client.get("/api/v1/vehicles/years").json()
    assert years[-1] == 1981
    assert years[0] > 2025


def test_makes_seeded(client):
    names = [m["name"] for m in client.get("/api/v1/vehicles/makes").json()]
    assert {"Ford", "Honda", "Toyota", "BMW", "Mercedes-Benz"} <= set(names)


def test_models_fetched_once_then_cached(client, vpic):
    honda = _make_id(client, "Honda")
    r1 = client.get("/api/v1/vehicles/models", params={"year": 2012, "make_id": honda}).json()
    r2 = client.get("/api/v1/vehicles/models", params={"year": 2012, "make_id": honda}).json()
    assert [m["name"] for m in r1] == ["Accord", "Civic"]
    assert r1 == r2
    assert vpic.model_calls == 1


def test_models_unknown_make(client):
    r = client.get("/api/v1/vehicles/models", params={"year": 2012, "make_id": 99999})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "make_not_found"


def test_manual_pick_resolves_and_is_idempotent(client):
    honda = _make_id(client, "Honda")
    civic = next(
        m
        for m in client.get(
            "/api/v1/vehicles/models", params={"year": 2012, "make_id": honda}
        ).json()
        if m["name"] == "Civic"
    )
    payload = {"year": 2012, "model_id": civic["id"], "displacement_l": 1.8, "cylinders": 4,
               "fuel_type": "gasoline"}  # fmt: skip
    a = client.post("/api/v1/vehicles", json=payload).json()
    b = client.post("/api/v1/vehicles", json=payload).json()
    assert a["id"] == b["id"]
    profile = client.get(f"/api/v1/vehicles/{a['id']}").json()
    assert profile["label"].startswith("2012 Honda Civic 1.8L")
    assert "counts" in profile


def test_manual_pick_without_engine(client):
    honda = _make_id(client, "Honda")
    civic = client.get("/api/v1/vehicles/models", params={"year": 2012, "make_id": honda}).json()[1]
    v = client.post("/api/v1/vehicles", json={"year": 2012, "model_id": civic["id"]}).json()
    assert v["engine"]["label"] is None


def test_manual_pick_validation(client):
    r = client.post("/api/v1/vehicles", json={"year": 1950, "model_id": 1})
    assert r.status_code == 422
    r = client.post("/api/v1/vehicles", json={"year": 2012, "model_id": 1, "cylinders": 40})
    assert r.status_code == 422


def test_vehicle_not_found(client):
    r = client.get("/api/v1/vehicles/999999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "vehicle_not_found"
