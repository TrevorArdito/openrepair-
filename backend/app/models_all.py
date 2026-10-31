"""Import every module's models so Alembic and tests see all tables."""

from app.modules.accounts import models as accounts_models  # noqa: F401
from app.modules.safety import models as safety_models  # noqa: F401
from app.modules.vehicles import models as vehicles_models  # noqa: F401
