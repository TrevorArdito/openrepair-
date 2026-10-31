"""Production mode: the API server also serves the built app, with Google-friendly pages."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import get_db
from app.main import create_app

INDEX = """<!doctype html><html><head><meta charset="UTF-8" />
<meta name="description" content="Default description" />
<title>ChrystalClear</title></head><body><div id="root"></div></body></html>"""


@pytest.fixture
def prod(tmp_path, db_session_factory, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "public_base_url", "https://cc.example")
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX)
    (tmp_path / "sw.js").write_text("// sw")
    app = create_app(Settings(frontend_dist_dir=str(tmp_path)))

    def _db():
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    return TestClient(app)


def test_serves_spa_and_keeps_api_404s(prod):
    assert "<title>" in prod.get("/garage").text  # app routes -> index.html
    assert prod.get("/sw.js").text == "// sw"
    assert prod.get("/api/v1/health").json()["status"] == "ok"
    r = prod.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    # Path traversal never escapes the dist folder.
    assert "ChrystalClear" in prod.get("/..%2f..%2fetc%2fpasswd").text


def test_code_page_is_google_friendly(prod):
    html = prod.get("/codes/P0420").text
    assert (
        "<title>P0420: Catalytic converter efficiency below threshold (bank 1) | ChrystalClear</title>"
        in html
    )
    assert 'content="Default description"' not in html  # replaced, not duplicated
    assert html.count('name="description"') == 1
    assert '<link rel="canonical" href="https://cc.example/codes/P0420" />' in html
    assert "<h2>How to diagnose</h2>" in html and "<ol><li>" in html
    assert '"@type": "TechArticle"' in html
    assert 'name="robots"' not in html


def test_entry_page_and_privacy(prod, client, db_session_factory):
    from app.modules.accounts.models import Role
    from tests.test_community import TORQUE, create, login_as

    login_as(client, db_session_factory, "pro@example.com", Role.pro)
    eid = create(client, "torque_spec", {**TORQUE, "stages": [{"type": "torque", "value_nm": 203.4}]},
                 title="Lug nut torque <script>alert(1)</script>").json()["id"]  # fmt: skip
    html = prod.get(f"/entries/{eid}").text
    assert "Wheel lug nuts: 150 lb·ft (203 N·m)" in html
    assert "<script>alert(1)</script>" not in html  # escaped
    assert "&lt;script&gt;" in html

    client.cookies.clear()
    login_as(client, db_session_factory, "new@example.com")
    pending = create(client, title="Secret pending guide").json()["id"]
    html = prod.get(f"/entries/{pending}").text
    assert "Secret pending guide" not in html  # pending content never leaks
    assert 'name="robots" content="noindex"' in html


def test_vehicle_and_index_pages(prod):
    html = prod.get("/vehicle/1").text
    assert "recalls, TSBs &amp; repair info" in html
    index = prod.get("/codes").text
    assert '<a href="/codes/P0420">' in index
    assert 'name="robots" content="noindex"' in prod.get("/account").text


def test_google_verification_tag(prod, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "google_site_verification", "abc123")
    assert '<meta name="google-site-verification" content="abc123" />' in prod.get("/").text


def test_engine_pages_are_google_friendly(prod, client):
    eid = next(e["id"] for e in client.get("/api/v1/engines").json() if e["slug"] == "cummins-6-7")
    html = prod.get(f"/engines/{eid}").text
    assert (
        "<title>Cummins 6.7L I6 Turbo Diesel — vehicles, codes &amp; repair info | ChrystalClear</title>"
        in html
    )
    assert "Ram 2500 (2011–" in html
    assert f"<loc>https://cc.example/engines/{eid}</loc>" in prod.get("/sitemap.xml").text


def test_sitemap_and_robots(prod):
    sm = prod.get("/sitemap.xml")
    assert sm.headers["content-type"].startswith("application/xml")
    assert "<loc>https://cc.example/codes/P0420</loc>" in sm.text
    assert "<loc>https://cc.example/vehicle/1</loc>" in sm.text
    robots = prod.get("/robots.txt").text
    assert "Sitemap: https://cc.example/sitemap.xml" in robots
    assert "Disallow: /api/" in robots


def test_production_requires_real_secret():
    with pytest.raises(ValueError):
        Settings(app_env="production", secret_key="change-me-dev-only")
    Settings(app_env="production", secret_key="x" * 40)


def test_database_url_from_hosts_is_normalized():
    s = Settings(database_url="postgres://u:p@host:5432/db?sslmode=require")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db?sslmode=require"
    assert Settings(database_url="postgresql://u@h/d").database_url.startswith(
        "postgresql+psycopg://"
    )
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"
