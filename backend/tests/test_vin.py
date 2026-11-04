"""VIN decoder tests: validation, check digit, decoding and caching."""

import pytest

from app.core.errors import AppError
from app.modules.vehicles.vin import (
    check_digit_valid,
    compute_check_digit,
    normalize_vin,
    validate_vin,
)

VALID_VIN = "1HGCM82633A004352"  # widely published example; check digit "3"
VALID_X_VIN = "1M8GDM9AXKP042788"  # check digit "X"
F150_VIN = "1FTEW1EG5FFA00000"


def test_normalize_strips_spaces_dashes_and_uppercases():
    assert normalize_vin(" 1hgcm8-2633a 004352 ") == VALID_VIN


@pytest.mark.parametrize("vin", [VALID_VIN, VALID_X_VIN, "11111111111111111"])
def test_check_digit_valid(vin):
    assert check_digit_valid(vin)


def test_check_digit_x():
    assert compute_check_digit(VALID_X_VIN) == "X"


def test_check_digit_mismatch_detected():
    assert not check_digit_valid("1HGCM82643A004352")


@pytest.mark.parametrize(
    ("vin", "code"),
    [
        ("1HGCM82633A00435", "vin_wrong_length"),
        ("1HGCM82633A0043521", "vin_wrong_length"),
        ("1HGCM82633A00435O", "vin_invalid_letters"),
        ("IHGCM82633A004352", "vin_invalid_letters"),
        ("1HGCM82633A00435!", "vin_invalid_characters"),
    ],
)
def test_validate_rejects_bad_vins(vin, code):
    with pytest.raises(AppError) as exc:
        validate_vin(vin)
    assert exc.value.code == code


def test_decode_endpoint_creates_vehicle(client, vpic):
    r = client.get(f"/api/v1/vehicles/decode/{F150_VIN}")
    assert r.status_code == 200, r.text
    body = r.json()
    v = body["vehicle"]
    assert v["year"] == 2015
    assert v["make"]["name"] == "Ford"
    assert v["model"]["name"] == "F-150"
    assert v["engine"]["displacement_l"] == 3.5
    assert v["engine"]["cylinders"] == 6
    assert v["engine"]["fuel_type"] == "gasoline"
    assert v["label"] == "2015 Ford F-150 3.5L V6 Turbo"
    assert body["details"]["trim"] == "XLT"
    assert body["warnings"] == []
    assert body["source"] == "NHTSA vPIC"
    # Our fake VIN has a wrong check digit; we flag it instead of refusing.
    assert body["check_digit_valid"] is False


def test_decode_matches_seeded_vehicle(client):
    """The seeded 2015 F-150 3.5L should be reused, not duplicated."""
    engines = client.get("/api/v1/vehicles/engines", params={"year": 2015, "model_id": 0})
    assert engines.status_code == 422  # model_id must be >= 1
    v = client.get(f"/api/v1/vehicles/decode/{F150_VIN}").json()["vehicle"]
    engines = client.get(
        "/api/v1/vehicles/engines", params={"year": 2015, "model_id": v["model"]["id"]}
    ).json()
    assert len(engines) == 2  # seeded 3.5L and 5.0L
    assert v["id"] in [e["id"] for e in engines]


def test_decode_is_cached(client, vpic):
    client.get(f"/api/v1/vehicles/decode/{F150_VIN}")
    client.get(f"/api/v1/vehicles/decode/{F150_VIN.lower()}")
    assert vpic.decode_calls == 1


def test_decode_invalid_vin_never_calls_nhtsa(client, vpic):
    r = client.get("/api/v1/vehicles/decode/123")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "vin_wrong_length"
    assert vpic.decode_calls == 0


def test_decode_reports_nhtsa_warnings(client, vpic):
    vpic.decode_result |= {"ErrorCode": "1", "ErrorText": "1 - Check Digit does not calculate"}
    body = client.get(f"/api/v1/vehicles/decode/{F150_VIN}").json()
    assert body["warnings"] == ["1 - Check Digit does not calculate"]


def test_decode_undecodable(client, vpic):
    vpic.decode_result = {"ErrorCode": "11", "ErrorText": "Incorrect Model Year"}
    r = client.get(f"/api/v1/vehicles/decode/{VALID_VIN}")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "vin_not_decodable"


def test_decode_upstream_down(client, vpic):
    vpic.fail = True
    r = client.get(f"/api/v1/vehicles/decode/{VALID_VIN}")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "upstream_unavailable"


def test_vpic_client_parses_and_handles_errors():
    """The real NHTSA client, pointed at a fake HTTP server."""
    import httpx

    from app.modules.vehicles.vpic import VpicClient

    def handler(request: httpx.Request) -> httpx.Response:
        if "DecodeVinValuesExtended" in request.url.path:
            assert request.url.params["format"] == "json"
            return httpx.Response(200, json={"Results": [{"Make": "FORD"}]})
        if "GetModelsForMakeIdYear" in request.url.path:
            # Same model returned for car + truck lists -> de-duplicated.
            return httpx.Response(200, json={"Results": [{"Model_ID": 1, "Model_Name": "X"}]})
        return httpx.Response(500)

    c = VpicClient("https://vpic.test/api", httpx.Client(transport=httpx.MockTransport(handler)))
    assert c.decode_vin(VALID_VIN) == {"Make": "FORD"}
    assert c.models_for_make_year(460, 2015) == [{"Model_ID": 1, "Model_Name": "X"}]

    broken = VpicClient(
        "https://vpic.test/api",
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
    )
    with pytest.raises(AppError) as exc:
        broken.decode_vin(VALID_VIN)
    assert exc.value.code == "upstream_unavailable"
