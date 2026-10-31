"""Community content: one shared system for guides, torque specs, fluid capacities,
other specs, part notes and labor times — so history, voting, reporting and
"verified by a pro" work the same everywhere."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin, utcnow
from app.modules.vehicles.fitment import FitmentMixin


class Kind(enum.StrEnum):
    procedure = "procedure"
    torque_spec = "torque_spec"
    fluid_capacity = "fluid_capacity"
    spec = "spec"  # other measured specs: gaps, pressures, resistances, clearances...
    part_note = "part_note"
    labor_time = "labor_time"


class EntryStatus(enum.StrEnum):
    published = "published"
    pending = "pending"  # first version waiting for review
    hidden = "hidden"  # removed by a moderator


class RevisionStatus(enum.StrEnum):
    approved = "approved"
    pending = "pending"
    rejected = "rejected"


def _enum(e):
    return Enum(e, native_enum=False, length=20)


class System(Base):
    """Category tree: engine > cooling, brakes > hydraulics, ..."""

    __tablename__ = "systems"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("systems.id"))
    safety_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Entry(TimestampMixin, Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[Kind] = mapped_column(_enum(Kind), index=True)
    status: Mapped[EntryStatus] = mapped_column(_enum(EntryStatus), default=EntryStatus.pending)
    title: Mapped[str] = mapped_column(String(200))  # copy of current revision title (for lists)
    current_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("entry_revisions.id", use_alter=True, ondelete="SET NULL")
    )
    verified_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("entry_revisions.id", use_alter=True, ondelete="SET NULL")
    )
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int] = mapped_column(Integer, default=0)
    safety_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    current_revision: Mapped["EntryRevision | None"] = relationship(
        foreign_keys=[current_revision_id], post_update=True
    )
    revisions: Mapped[list["EntryRevision"]] = relationship(
        foreign_keys="EntryRevision.entry_id",
        back_populates="entry",
        order_by="EntryRevision.number",
        cascade="all, delete-orphan",
    )


class EntryRevision(Base):
    """A full snapshot of an entry at one point in time (easy history, diff and revert)."""

    __tablename__ = "entry_revisions"
    __table_args__ = (UniqueConstraint("entry_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    data: Mapped[dict] = mapped_column(JSON)  # validated per kind (see kinds.py)
    tags: Mapped[dict] = mapped_column(JSON)  # applies_to, systems, dtcs
    edit_summary: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[RevisionStatus] = mapped_column(_enum(RevisionStatus))
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    entry: Mapped[Entry] = relationship(foreign_keys=[entry_id], back_populates="revisions")


# ---- Tags of the current approved revision, copied into tables for fast lookups ----


class EntryVehicle(FitmentMixin, Base):
    __tablename__ = "entry_vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)


class EntrySystem(Base):
    __tablename__ = "entry_systems"
    __table_args__ = (UniqueConstraint("entry_id", "system_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id"), index=True)


class EntryDtc(Base):
    __tablename__ = "entry_dtcs"
    __table_args__ = (UniqueConstraint("entry_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(5), index=True)


# ---- Feedback ----------------------------------------------------------------


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("entry_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    value: Mapped[int] = mapped_column(Integer)


class ReportReason(enum.StrEnum):
    wrong_info = "wrong_info"
    unsafe = "unsafe"
    spam = "spam"
    copyright = "copyright"
    other = "other"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("entry_revisions.id", ondelete="SET NULL")
    )
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[ReportReason] = mapped_column(_enum(ReportReason))
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | resolved | dismissed
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LaborBasis(enum.StrEnum):
    """Where a labor-time number comes from. Several sources are shown side by side."""

    warranty = "warranty"  # what the manufacturer's warranty time pays (as reported by a tech)
    flat_rate = "flat_rate"  # what a customer-pay labor guide pays (as reported by a tech)
    pro_actual = "pro_actual"  # real clock time, professional with shop tools/lift
    diy_actual = "diy_actual"  # real clock time, DIY in a driveway/garage


class RustLevel(enum.StrEnum):
    none = "none"
    light = "light"
    heavy = "heavy"


class LaborReport(Base):
    """One person's labor-time data point for a labor_time entry."""

    __tablename__ = "labor_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    basis: Mapped[LaborBasis] = mapped_column(_enum(LaborBasis))
    hours: Mapped[float] = mapped_column(Float)
    rust: Mapped[RustLevel] = mapped_column(_enum(RustLevel), default=RustLevel.none)
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int | None] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"))
    uploader_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="visible")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
