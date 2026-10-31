"""Feature module registry.

Each module is a folder under app/modules/ that exposes `router`. Modules can be
switched on/off with environment flags, so future features (hardware/OBD-II,
wiring diagrams, key programming, ECU tuning, parts prices, and any optional paid
business tools) plug in without touching the free core.
"""

from dataclasses import dataclass
from importlib import import_module

from app.config import Settings


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    import_path: str
    enabled_flag: str | None = None  # Settings attribute; None = always on (core)
    attr: str = "router"


MODULES: list[ModuleSpec] = [
    ModuleSpec("accounts", "app.modules.accounts.router"),
    ModuleSpec("vehicles", "app.modules.vehicles.router"),
    ModuleSpec("safety", "app.modules.safety.router"),
    ModuleSpec("dtc", "app.modules.dtc.router"),
    ModuleSpec("community", "app.modules.community.router"),
    ModuleSpec("moderation", "app.modules.community.router", attr="mod"),
    # Off by default. See app/modules/hardware/README.md.
    ModuleSpec("hardware", "app.modules.hardware.router", enabled_flag="enable_hardware"),
]


def enabled_modules(settings: Settings) -> list[ModuleSpec]:
    return [m for m in MODULES if m.enabled_flag is None or getattr(settings, m.enabled_flag)]


def load_router(spec: ModuleSpec):
    return getattr(import_module(spec.import_path), spec.attr)
