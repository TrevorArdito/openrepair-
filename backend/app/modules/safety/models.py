"""NHTSA safety data: recalls, complaints, and the TSB (manufacturer communications) index.

All of it is US government data (public domain). NHTSA identifies vehicles by
make/model/year text, so we store normalized "keys" to match our vehicles."""

import re
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow


def name_key(text: str) -> str:
    """'F-150' -> 'F150', 'Mercedes-Benz' -> 'MERCEDESBENZ' (for matching NHTSA text)."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


class Recall(Base):
    __tablename__ = "recalls"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    component: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    consequence: Mapped[str | None] = mapped_column(Text)
    remedy: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    report_date: Mapped[date | None] = mapped_column(Date)
    park_it: Mapped[bool] = mapped_column(Boolean, default=False)
    park_outside: Mapped[bool] = mapped_column(Boolean, default=False)
    over_the_air: Mapped[bool] = mapped_column(Boolean, default=False)

    vehicles: Mapped[list["RecallVehicle"]] = relationship(cascade="all, delete-orphan")


class RecallVehicle(Base):
    __tablename__ = "recall_vehicles"
    __table_args__ = (UniqueConstraint("recall_id", "make_key", "model_key", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recall_id: Mapped[int] = mapped_column(ForeignKey("recalls.id", ondelete="CASCADE"))
    make_key: Mapped[str] = mapped_column(String(80), index=True)
    model_key: Mapped[str] = mapped_column(String(120), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    odi_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    components: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    crash: Mapped[bool] = mapped_column(Boolean, default=False)
    fire: Mapped[bool] = mapped_column(Boolean, default=False)
    injuries: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    incident_date: Mapped[date | None] = mapped_column(Date)
    filed_date: Mapped[date | None] = mapped_column(Date, index=True)

    vehicles: Mapped[list["ComplaintVehicle"]] = relationship(cascade="all, delete-orphan")


class ComplaintVehicle(Base):
    __tablename__ = "complaint_vehicles"
    __table_args__ = (UniqueConstraint("complaint_id", "make_key", "model_key", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"))
    make_key: Mapped[str] = mapped_column(String(80), index=True)
    model_key: Mapped[str] = mapped_column(String(120), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)


class Tsb(Base):
    """Index entry for a manufacturer communication (TSB). We store NHTSA's summary,
    not the manufacturer's full bulletin."""

    __tablename__ = "tsbs"

    id: Mapped[int] = mapped_column(primary_key=True)
    nhtsa_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    bulletin_number: Mapped[str | None] = mapped_column(String(128))
    bulletin_date: Mapped[date | None] = mapped_column(Date, index=True)
    comm_type: Mapped[str | None] = mapped_column(String(60))
    components: Mapped[str | None] = mapped_column(String(600))
    summary: Mapped[str | None] = mapped_column(Text)

    vehicles: Mapped[list["TsbVehicle"]] = relationship(cascade="all, delete-orphan")


class TsbVehicle(Base):
    __tablename__ = "tsb_vehicles"
    __table_args__ = (UniqueConstraint("tsb_id", "make_key", "model_key", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tsb_id: Mapped[int] = mapped_column(ForeignKey("tsbs.id", ondelete="CASCADE"))
    make_key: Mapped[str] = mapped_column(String(80), index=True)
    model_key: Mapped[str] = mapped_column(String(120), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)


class SafetyFetch(Base):
    """When we last asked the NHTSA API about a make/model/year (cache freshness)."""

    __tablename__ = "safety_fetches"
    __table_args__ = (UniqueConstraint("source", "make_key", "model_key", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20))
    make_key: Mapped[str] = mapped_column(String(80))
    model_key: Mapped[str] = mapped_column(String(120))
    year: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DataImport(Base):
    """Log of every data refresh, so admins can see when data was last updated."""

    __tablename__ = "data_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_added: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error: Mapped[str | None] = mapped_column(Text)
