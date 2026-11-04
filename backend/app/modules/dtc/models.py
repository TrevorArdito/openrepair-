from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin


class Dtc(TimestampMixin, Base):
    """A diagnostic trouble code. Text is written in our own words; every row records
    where it came from and under which license."""

    __tablename__ = "dtcs"
    __table_args__ = (UniqueConstraint("code", "make_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(5), index=True)
    make_id: Mapped[int | None] = mapped_column(ForeignKey("makes.id"))  # None = generic code
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    symptoms: Mapped[list[str]] = mapped_column(JSON, default=list)
    causes: Mapped[list[str]] = mapped_column(JSON, default=list)
    diagnostic_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    severity: Mapped[str] = mapped_column(String(10), default="medium")  # low | medium | high
    systems: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(200))
    source_license: Mapped[str] = mapped_column(String(60))
