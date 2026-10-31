"""ChrystalClear API — free, open-source auto repair information (AGPL-3.0)."""

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import __version__, seo
from app.config import Settings, get_settings
from app.core.errors import NotFound, install_error_handlers
from app.db import get_db
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
    """Production: serve the built PWA from the same server (one container, one bill),
    with Google-friendly titles/descriptions/content filled in for public pages."""
    index = dist / "index.html"
    app.mount("/assets", StaticFiles(directory=dist / "assets", check_dir=False), name="assets")
    template = (
        index.read_text(encoding="utf-8")
        if index.is_file()
        else "<html><head></head><body></body></html>"
    )

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap_xml(db: Session = Depends(get_db)):
        return Response(seo.sitemap(db), media_type="application/xml")

    @app.get("/robots.txt", include_in_schema=False)
    def robots_txt():
        return PlainTextResponse(seo.robots())

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, db: Session = Depends(get_db)):
        if path == "api" or path.startswith("api/"):
            raise NotFound()
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        page = seo.page_for_path(db, path)
        return HTMLResponse(seo.render(template, page, path), headers={"Cache-Control": "no-cache"})


app = create_app()
