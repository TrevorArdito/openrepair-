"""App settings. Every value comes from environment variables (or a local .env file).

Secrets are never hard-coded: SECRET_KEY must be set in production.
"""

from functools import lru_cache

from pydantic import field_validator, model_validator
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
    # Where uploaded photos live: "local" disk (dev) or "database" (free hosts whose disk
    # is wiped on every restart). S3-compatible storage can be added later.
    storage_backend: str = "local"
    storage_local_dir: str = "./data/uploads"
    # Comma-separated emails that become admins when they log in (no command line needed
    # on free hosting). Example: ADMIN_EMAILS=owner@example.com
    admin_emails: str = ""
    # Google Search Console "HTML tag" verification code (just the content="..." value).
    google_site_verification: str = ""

    # Email: "console" prints emails to the server log (development); "smtp" sends them.
    email_backend: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "no-reply@example.org"
    # Anti-spam: require a verified email before contributing (turn on once email works).
    require_verified_email: bool = False
    # Serve the built frontend (frontend/dist) from the API server. Used in production
    # so the whole app runs as one small container.
    frontend_dist_dir: str | None = None

    # Feature modules (later modules plug in here; hardware is OFF by default).
    enable_hardware: bool = False
    # Parts marketplace (new + used parts with fitment). See docs/COMMERCE_DESIGN.md.
    enable_marketplace: bool = False
    # Marketplace payments (Stripe Connect). See docs/PAYMENTS.md. Keys are secrets: env only.
    enable_market_payments: bool = False
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    market_fee_percent: float = 6.0  # our fee on shipped / in-app sales
    market_stripe_fee_percent: float = 2.9  # for showing sellers an estimate only
    market_stripe_fee_fixed_cents: int = 30
    market_tax_enabled: bool = False  # Stripe Tax — turn on after the CPA confirms
    market_release_days_after_delivery: int = 3
    market_release_days_after_ship: int = 30
    market_contact_only_categories: str = "vehicle"  # comma list: no in-app payment
    market_inform_sales: int = 200  # INFORM Consumers Act high-volume thresholds (12 months)
    market_inform_revenue_cents: int = 500_000

    @property
    def market_payments_on(self) -> bool:
        return self.enable_marketplace and self.enable_market_payments

    @property
    def contact_only_categories(self) -> set[str]:
        return {c.strip() for c in self.market_contact_only_categories.split(",") if c.strip()}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Hosts hand out 'postgres://...' URLs; SQLAlchemy needs the driver name."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    @field_validator("public_base_url")
    @classmethod
    def _strip_slash(cls, v: str) -> str:
        return v.rstrip("/")

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
