"""Production mode: the API server also serves the built app."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_serves_spa_and_keeps_api_404s(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<title>ChrystalClear</title>")
    (tmp_path / "sw.js").write_text("// sw")
    client = TestClient(create_app(Settings(frontend_dist_dir=str(tmp_path))))

    assert "ChrystalClear" in client.get("/garage").text  # app routes -> index.html
    assert client.get("/sw.js").text == "// sw"
    assert client.get("/api/v1/health").json()["status"] == "ok"
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    # Path traversal never escapes the dist folder.
    assert "ChrystalClear" in client.get("/..%2f..%2fetc%2fpasswd").text


def test_production_requires_real_secret():
    import pytest

    with pytest.raises(ValueError):
        Settings(app_env="production", secret_key="change-me-dev-only")
    Settings(app_env="production", secret_key="x" * 40)
