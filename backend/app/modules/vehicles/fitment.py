"""Vehicle fitment: "which vehicles does this apply to?"

One shape and one matching rule shared by everything that targets vehicles —
community guides/specs today; parts, marketplace listings and tunes later
(see docs/COMMERCE_DESIGN.md). Empty columns mean "any".
"""

from sqlalchemy import Float, ForeignKey, Integer, and_, func, or_
from sqlalchemy.orm import Mapped, mapped_column

from app.core.errors import AppError, NotFound
from app.modules.vehicles.models import EngineFamily, Make, Model, Vehicle


class FitmentMixin:
    """Columns for one fitment range: make, optional model, years, optional engine size."""

    make_id: Mapped[int] = mapped_column(ForeignKey("makes.id"), index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id"), index=True)
    year_from: Mapped[int] = mapped_column(Integer)
    year_to: Mapped[int] = mapped_column(Integer)
    displacement_l: Mapped[float | None] = mapped_column(Float)
    # Optional exact engine (e.g. 3.5L EcoBoost vs 3.5L non-turbo in the same truck).
    engine_family_id: Mapped[int | None] = mapped_column(ForeignKey("engine_families.id"))


def fits(table, v: Vehicle):
    """SQL condition: rows of `table` (a FitmentMixin model) that fit vehicle `v`."""
    return and_(
        table.make_id == v.model.make_id,
        or_(table.model_id.is_(None), table.model_id == v.model_id),
        table.year_from <= v.year,
        table.year_to >= v.year,
        or_(
            table.displacement_l.is_(None),
            v.engine_displacement_l is None,
            func.abs(table.displacement_l - (v.engine_displacement_l or 0)) < 0.05,
        ),
        or_(table.engine_family_id.is_(None), table.engine_family_id == v.engine_family_id),
    )


def validate_fitment(db, rows, error_code: str) -> None:
    """Check fitment rows (objects with make_id, model_id, year_from, year_to,
    engine_family_id): years in order, and every id exists and belongs together."""
    for a in rows:
        if a.year_from > a.year_to:
            raise AppError(error_code, 422, fields=[{"loc": ["fitment", "years"]}])
        if db.get(Make, a.make_id) is None:
            raise NotFound("make_not_found")
        if a.model_id is not None:
            model = db.get(Model, a.model_id)
            if model is None or model.make_id != a.make_id:
                raise NotFound("model_not_found")
        if a.engine_family_id is not None and db.get(EngineFamily, a.engine_family_id) is None:
            raise NotFound("engine_not_found")


def fitment_display(db, row: dict) -> dict:
    """A fitment row with names filled in, for showing to people."""
    make = db.get(Make, row["make_id"])
    model = db.get(Model, row["model_id"]) if row.get("model_id") else None
    fam = db.get(EngineFamily, row["engine_family_id"]) if row.get("engine_family_id") else None
    return {
        **row,
        "make": make.name if make else "?",
        "model": model.name if model else None,
        "engine": fam.name if fam else None,
    }
