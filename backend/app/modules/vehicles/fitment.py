"""Vehicle fitment: "which vehicles does this apply to?"

One shape and one matching rule shared by everything that targets vehicles —
community guides/specs today; parts, marketplace listings and tunes later
(see docs/COMMERCE_DESIGN.md). Empty columns mean "any".
"""

from sqlalchemy import Float, ForeignKey, Integer, and_, func, or_
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.vehicles.models import Vehicle


class FitmentMixin:
    """Columns for one fitment range: make, optional model, years, optional engine size."""

    make_id: Mapped[int] = mapped_column(ForeignKey("makes.id"), index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id"), index=True)
    year_from: Mapped[int] = mapped_column(Integer)
    year_to: Mapped[int] = mapped_column(Integer)
    displacement_l: Mapped[float | None] = mapped_column(Float)


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
    )
