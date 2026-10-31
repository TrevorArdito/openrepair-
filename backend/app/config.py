"""App settings. Every value comes from environment variables (or a local .env file).

Secrets are never hard-coded: SECRET_KEY must be set in production.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me-dev-only"  # noqa: S105 - dev default; refused in production
    public_base_url: str = "http://localhost:5173"
    source_code_url: str = "https://github.com/TrevorArdito/openrepair-"

    database_url: str = "sqlite:///./chrystalclear.db"

    nhtsa_vpic_base_url: str = "https://vpic.nhtsa.dot.gov/api/vehicles"
    nhtsa_api_base_url: str = "https://api.nhtsa.gov"
    http_timeout_seconds: float = 15.0

    session_days: int = 30
    storage_local_dir: str = "./data/uploads"
    # Serve the built frontend (frontend/dist) from the API server. Used in production
    # so the whole app runs as one small container.
    frontend_dist_dir: str | None = None

    # Feature modules (later modules plug in here; hardware is OFF by default).
    enable_hardware: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        if self.is_production and (
            self.secret_key == "change-me-dev-only"  # noqa: S105
            or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY must be set to a long random value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
