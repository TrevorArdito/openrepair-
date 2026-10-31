"""Client for the free NHTSA vPIC API (https://vpic.nhtsa.dot.gov/api/).

US government data — public domain. We cache results in our own database so we
don't ask NHTSA the same question twice."""

from typing import Any, Protocol

import httpx

from app.config import get_settings
from app.core.errors import AppError

VEHICLE_TYPES = ("car", "truck", "multipurpose passenger vehicle (mpv)")


class VpicApi(Protocol):
    def decode_vin(self, vin: str) -> dict[str, Any]: ...
    def models_for_make_year(self, vpic_make_id: int, year: int) -> list[dict[str, Any]]: ...


class VpicClient:
    def __init__(self, base_url: str | None = None, client: httpx.Client | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.nhtsa_vpic_base_url).rstrip("/")
        self.client = client or httpx.Client(
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": "ChrystalClear/0.1 (+open-source repair info)"},
        )

    def _get(self, path: str) -> dict[str, Any]:
        try:
            r = self.client.get(f"{self.base_url}/{path}", params={"format": "json"})
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError("upstream_unavailable", 503, source="nhtsa_vpic") from exc

    def decode_vin(self, vin: str) -> dict[str, Any]:
        data = self._get(f"DecodeVinValuesExtended/{vin}")
        results = data.get("Results") or []
        if not results:
            raise AppError("vin_not_decodable", 422)
        return results[0]

    def models_for_make_year(self, vpic_make_id: int, year: int) -> list[dict[str, Any]]:
        seen: dict[int, dict[str, Any]] = {}
        for vtype in VEHICLE_TYPES:
            path = (
                f"GetModelsForMakeIdYear/makeId/{vpic_make_id}/modelyear/{year}/vehicletype/{vtype}"
            )
            for row in self._get(path).get("Results") or []:
                seen.setdefault(int(row["Model_ID"]), row)
        return list(seen.values())


_default_client: VpicClient | None = None


def get_vpic() -> VpicApi:
    global _default_client
    if _default_client is None:
        _default_client = VpicClient()
    return _default_client
