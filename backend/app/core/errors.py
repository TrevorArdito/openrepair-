"""Errors return stable machine-readable codes (not English sentences) so the
frontend can translate them (English now, Spanish later)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, status_code: int = 400, **details):
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(code)


class NotFound(AppError):
    def __init__(self, code: str = "not_found", **details):
        super().__init__(code, 404, **details)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_req: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_req: Request, exc: RequestValidationError):
        fields = [
            {"loc": [str(p) for p in e.get("loc", [])], "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "details": {"fields": fields}}},
        )
