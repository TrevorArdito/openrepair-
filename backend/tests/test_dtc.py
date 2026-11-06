"""DTC lookup tests."""

import json
from pathlib import Path

import pytest

from app.core.errors import AppError
from app.modules.dtc.structure import explain, is_generic, validate_code

SEED = json.loads((Path(__file__).parents[1] / "app/seed/data/dtcs.json").read_text())


def test_lookup_known_code(client):
    body = client.get("/api/v1/dtcs/P0420").json()
    assert body["known"] is True
    assert body["title"].startswith("Catalytic converter efficiency")
    assert body["severity"] == "low"
    assert body["structure"] == {
        "system": "powertrain",
        "generic": True,
        "subsystem": "aux_emissions",
    }
    assert len(body["diagnostic_steps"]) >= 3
    assert body["source_license"] == "River Valley Auto Sales and Market proprietary"


def test_lookup_normalizes_input(client):
    assert client.get("/api/v1/dtcs/p0301").json()["code"] == "P0301"
    assert client.get("/api/v1/dtcs/p 0301").json()["code"] == "P0301"


def test_cylinder_codes_are_specific(client):
    body = client.get("/api/v1/dtcs/P0304").json()
    assert "Cylinder 4" in body["title"]
    assert any("cylinder 4" in step for step in body["diagnostic_steps"])


def test_unknown_but_valid_code_still_explained(client):
    body = client.get("/api/v1/dtcs/P1450").json()
    assert body["known"] is False
    assert body["structure"]["generic"] is False  # P1xxx = manufacturer-specific
    assert body["structure"]["subsystem"] == "aux_emissions"


@pytest.mark.parametrize("bad", ["X0420", "P042", "P04200", "P5420", "", "P04G0"])
def test_invalid_codes_rejected(bad):
    with pytest.raises(AppError) as exc:
        validate_code(bad)
    assert exc.value.code == "dtc_invalid"


def test_invalid_code_api(client):
    r = client.get("/api/v1/dtcs/HELLO")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "dtc_invalid"


def test_generic_vs_manufacturer():
    assert is_generic("P0420") and is_generic("P2096") and is_generic("U0100")
    assert not is_generic("P1450") and not is_generic("B1234") and not is_generic("U1000")
    assert explain("C0035")["system"] == "chassis"
    assert explain("B0001")["subsystem"] is None


def test_search_by_code_prefix(client):
    codes = [d["code"] for d in client.get("/api/v1/dtcs", params={"q": "P030"}).json()]
    assert codes[0] == "P0300"
    assert "P0308" in codes
    assert all(c.startswith("P030") for c in codes)


def test_search_by_words(client):
    codes = [d["code"] for d in client.get("/api/v1/dtcs", params={"q": "lean"}).json()]
    assert {"P0171", "P0174"} <= set(codes)
    assert client.get("/api/v1/dtcs", params={"q": "zzzz-nothing"}).json() == []


def test_seed_content_is_complete_and_licensed():
    codes = [row["code"] for row in SEED]
    assert len(codes) == len(set(codes))
    for row in SEED:
        validate_code(row["code"])
        assert row["severity"] in {"low", "medium", "high"}
        assert row["title"] and row["description"]
        assert row["symptoms"] and row["causes"] and row["diagnostic_steps"], row["code"]
        assert (
            row["source"]
            and row["source_license"] == "River Valley Auto Sales and Market proprietary"
        )
