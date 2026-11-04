from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin, utcnow


class Make(Base):
    __tablename__ = "makes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    vpic_make_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    popular: Mapped[bool] = mapped_column(default=False)


class Model(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    make_id: Mapped[int] = mapped_column(ForeignKey("makes.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    vpic_model_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    # Content priority (1 = highest) from the owner's top-vehicle list; None = normal.
    priority: Mapped[int | None] = mapped_column(Integer)

    make: Mapped[Make] = relationship()


class ModelYear(Base):
    """Which model years exist for a model (filled from vPIC on demand)."""

    __tablename__ = "model_years"
    __table_args__ = (UniqueConstraint("model_id", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    make_id: Mapped[int] = mapped_column(ForeignKey("makes.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)


class VpicFetch(Base):
    """Remembers that we already downloaded the model list for a make+year."""

    __tablename__ = "vpic_fetches"
    __table_args__ = (UniqueConstraint("make_id", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    make_id: Mapped[int] = mapped_column(ForeignKey("makes.id"))
    year: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EngineFamily(TimestampMixin, Base):
    """An engine design used across many vehicles (e.g. "GM 5.3L V8", "Cummins 6.7L I6").

    Engines are first-class so guides/specs can target an engine, and so non-car engines
    (heavy equipment, generators, marine) can be added later (`applications`)."""

    __tablename__ = "engine_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    manufacturer: Mapped[str] = mapped_column(String(80))
    displacement_l: Mapped[float | None] = mapped_column(Float)
    cylinders: Mapped[int | None] = mapped_column(Integer)
    layout: Mapped[str | None] = mapped_column(String(20))
    fuel_type: Mapped[str | None] = mapped_column(String(20))
    aspiration: Mapped[str | None] = mapped_column(String(20))  # None/"na", "turbo", "supercharged"
    codes: Mapped[str | None] = mapped_column(String(200))  # common engine codes, comma separated
    year_from: Mapped[int | None] = mapped_column(Integer)
    year_to: Mapped[int | None] = mapped_column(Integer)
    applications: Mapped[list] = mapped_column(
        JSON, default=list
    )  # ["light_duty", "heavy_duty", "off_road", ...]
    notes: Mapped[str | None] = mapped_column(Text)


class Vehicle(TimestampMixin, Base):
    """Year + model + engine. Guides, specs, recalls etc. attach to this.

    Engine fields may all be empty = "engine not specified"."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_key: Mapped[str] = mapped_column(String(120), unique=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    engine_displacement_l: Mapped[float | None] = mapped_column(Float)
    cylinders: Mapped[int | None] = mapped_column(Integer)
    engine_layout: Mapped[str | None] = mapped_column(String(20))
    fuel_type: Mapped[str | None] = mapped_column(String(20))
    engine_code: Mapped[str | None] = mapped_column(String(60))
    aspiration: Mapped[str | None] = mapped_column(String(20))  # "turbo", "supercharged", or None
    engine_family_id: Mapped[int | None] = mapped_column(
        ForeignKey("engine_families.id"), index=True
    )
    source: Mapped[str | None] = mapped_column(String(20))  # epa | vin | seed | catalog | manual

    model: Mapped[Model] = relationship()
    engine_family: Mapped["EngineFamily | None"] = relationship()


class VinDecode(Base):
    __tablename__ = "vin_decodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    vin: Mapped[str] = mapped_column(String(17), unique=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    raw: Mapped[dict] = mapped_column(JSON)
    decoded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    vehicle: Mapped[Vehicle] = relationship()


class GarageVehicle(TimestampMixin, Base):
    __tablename__ = "garage_vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    vin: Mapped[str | None] = mapped_column(String(17))
    nickname: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(Text)

    vehicle: Mapped[Vehicle] = relationship()


class EngineFamilyApplication(Base):
    """Where an engine family was used: make, optional model, model years.
    (Same idea as fitment; a model of None means every model of that make.)"""

    __tablename__ = "engine_family_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    engine_family_id: Mapped[int] = mapped_column(
        ForeignKey("engine_families.id", ondelete="CASCADE"), index=True
    )
    make_id: Mapped[int] = mapped_column(ForeignKey("makes.id"))
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id"))
    year_from: Mapped[int] = mapped_column(Integer)
    year_to: Mapped[int] = mapped_column(Integer)
    creates_vehicles: Mapped[bool] = mapped_column(default=False)
