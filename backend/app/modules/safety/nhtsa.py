"""Client for api.nhtsa.gov (recalls and complaints by vehicle). Public domain data."""

from typing import Any, Protocol

import httpx

from app.config import get_settings
from app.core.errors import AppError


class NhtsaApi(Protocol):
    def recalls(self, make: str, model: str, year: int) -> list[dict[str, Any]]: ...
    def complaints(self, make: str, model: str, year: int) -> list[dict[str, Any]]: ...


class NhtsaClient:
    def __init__(self, base_url: str | None = None, client: httpx.Client | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.nhtsa_api_base_url).rstrip("/")
        self.client = client or httpx.Client(
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": "ChrystalClear/0.1 (+open-source repair info)"},
        )

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            r = self.client.get(f"{self.base_url}/{path}", params=params)
            if r.status_code == 400:  # NHTSA answers 400 for unknown make/model combos
                return {"results": []}
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError("upstream_unavailable", 503, source="nhtsa_api") from exc

    def recalls(self, make: str, model: str, year: int) -> list[dict[str, Any]]:
        data = self._get(
            "recalls/recallsByVehicle", {"make": make, "model": model, "modelYear": year}
        )
        return data.get("results") or data.get("Results") or []

    def complaints(self, make: str, model: str, year: int) -> list[dict[str, Any]]:
        data = self._get(
            "complaints/complaintsByVehicle", {"make": make, "model": model, "modelYear": year}
        )
        return data.get("results") or []


_default: NhtsaClient | None = None


def get_nhtsa() -> NhtsaApi:
    global _default
    if _default is None:
        _default = NhtsaClient()
    return _default
