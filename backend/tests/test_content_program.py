"""Content Research Program: DTC guide pages, per-value sources/UNVERIFIED, reviewer sign-off
gate for team content, report-a-mistake section + owner alert."""

import json

import pytest
from sqlalchemy import select

from app.core.email import OUTBOX
from app.modules.community.kinds import DtcGuideData, unverified_count
from app.modules.community.models import Entry, Kind
from app.seed import content
from app.seed.__main__ import team_user
from tests.conftest import csrf

GUIDE = {
    "code": "P0300",
    "definition": "Random or multiple-cylinder misfire detected.",
    "monitor": "The engine computer watches crankshaft speed; a misfiring cylinder slows it briefly.",
    "applications": "Example engine, example years (test data)",
    "causes": [
        {"cause": "Worn spark plugs", "rank": 1, "source_refs": [0]},
        {"cause": "Collapsed lifter", "rank": 2, "pattern_failure": True, "source_refs": [0]},
    ],
    "tests": [
        {
            "title": "Check spark plug gap",
            "how": "Remove the plugs and measure the gap.",
            "specs": [
                {"name": "Gap", "value": 1.0, "unit": "mm", "unverified": True, "source_refs": [0]}
            ],
            "good": "Within spec",
            "bad": "Worn electrode, wide gap",
        }
    ],
    "sources": [{"type": "industry_standard", "citation": "Test source"}],
}
FC = {"written_by": "writer-agent", "reviewed_by": "reviewer-agent", "reviewed_at": "2026-11-06",
      "checklist": {k: True for k in content.CHECKLIST}}  # fmt: skip


def test_dtc_guide_validates_and_counts_unverified():
    g = DtcGuideData.model_validate(GUIDE).model_dump(mode="json", exclude_none=True)
    assert unverified_count(g) == 1
    bad = {**GUIDE, "causes": [{"cause": "x", "rank": 1, "source_refs": [5]}]}
    with pytest.raises(ValueError):
        DtcGuideData.model_validate(bad)  # points at a source that doesn't exist
    with pytest.raises(ValueError):
        DtcGuideData.model_validate({**GUIDE, "sources": []})  # sources are required


def _write(tmp_path, name, fc):
    doc = {"kind": "dtc_guide", "title": f"P0300 — test page {name}",
           "applies_to": [{"make": "Ford", "model": "F-150", "year_from": 2015, "year_to": 2017}],
           "systems": ["engine.ignition"], "data": GUIDE, "fact_check": fc}  # fmt: skip
    (tmp_path / f"{name}.json").write_text(json.dumps(doc))


def test_content_loader_needs_independent_signoff(db_session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(content, "CANDIDATES", [tmp_path])
    _write(tmp_path, "ok", FC)
    _write(tmp_path, "self", {**FC, "reviewed_by": "writer-agent"})  # writer reviewed own page
    _write(tmp_path, "unchecked", {**FC, "checklist": {**FC["checklist"], "no_copied_text": False}})
    _write(tmp_path, "none", None)
    with db_session_factory() as db:
        counts = content.load_all(db, team_user(db))
        assert counts == {"added": 1, "waiting_for_review": 3}
        assert content.load_all(db, team_user(db)) == {"unchanged": 1, "waiting_for_review": 3}
        entry = db.scalar(select(Entry).where(Entry.kind == Kind.dtc_guide))
        assert entry.title == "P0300 — test page ok"


def test_guide_page_shows_signoff_unverified_and_code_link(
    client, db_session_factory, tmp_path, monkeypatch
):
    monkeypatch.setattr(content, "CANDIDATES", [tmp_path])
    _write(tmp_path, "ok", FC)
    with db_session_factory() as db:
        content.load_all(db, team_user(db))
        eid = db.scalar(select(Entry.id).where(Entry.kind == Kind.dtc_guide))
    page = client.get(f"/api/v1/entries/{eid}").json()
    assert page["revision"]["fact_check"]["reviewed_by"] == "reviewer-agent"
    assert page["revision"]["unverified"] == 1
    assert "P0300" in page["revision"]["tags"]["dtcs"]  # tagged with its own code automatically
    related = client.get("/api/v1/dtcs/P0300").json()
    assert any(r["id"] == eid for r in related.get("related_entries", related.get("guides", [])))


def test_report_a_mistake_with_section_alerts_owner(
    client, db_session_factory, tmp_path, monkeypatch
):
    from app.config import get_settings
    from tests.conftest import register

    monkeypatch.setattr(get_settings(), "admin_emails", "owner@example.com")
    monkeypatch.setattr(content, "CANDIDATES", [tmp_path])
    _write(tmp_path, "ok", FC)
    with db_session_factory() as db:
        content.load_all(db, team_user(db))
        eid = db.scalar(select(Entry.id).where(Entry.kind == Kind.dtc_guide))
    register(client, email="reader@example.com", name="reader")
    OUTBOX.clear()
    r = client.post(f"/api/v1/entries/{eid}/reports", headers=csrf(client),
                    json={"reason": "wrong_info", "section": "Test 1", "details": "Gap spec looks wrong."})  # fmt: skip
    assert r.status_code == 201, r.text
    mail = [m for m in OUTBOX if m["To"] == "owner@example.com"]
    assert mail and "Test 1" in mail[0].get_content()
    assert client.get(f"/api/v1/entries/{eid}").json()["under_review"] is True
