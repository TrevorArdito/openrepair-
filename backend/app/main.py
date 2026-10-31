"""ChrystalClear API — free, open-source auto repair information (AGPL-3.0)."""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.modules.registry import enabled_modules, load_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="ChrystalClear API",
        version=__version__,
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
        license_info={"name": "AGPL-3.0", "url": "https://www.gnu.org/licenses/agpl-3.0.html"},
    )
    install_error_handlers(app)

    modules = enabled_modules(settings)
    core = APIRouter()

    @core.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    @core.get("/meta")
    def meta():
        # The source link is required by the AGPL for network users.
        return {
            "name": "ChrystalClear",
            "version": __version__,
            "source_code_url": settings.source_code_url,
            "modules": [m.name for m in modules],
        }

    app.include_router(core, prefix=API_PREFIX)
    for spec in modules:
        app.include_router(load_router(spec), prefix=API_PREFIX)

    if settings.frontend_dist_dir:
        _mount_frontend(app, Path(settings.frontend_dist_dir))
    return app


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Production: serve the built PWA from the same server (one container, one bill)."""
    index = dist / "index.html"
    app.mount("/assets", StaticFiles(directory=dist / "assets", check_dir=False), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
