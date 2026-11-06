from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.community.models import Kind, LaborBasis, ReportReason, RustLevel
from app.modules.dtc.structure import validate_code
from app.modules.vehicles.schemas import MIN_YEAR, max_year


class AppliesTo(BaseModel):
    """A range of vehicles: make, optional model, year range, optional engine size."""

    make_id: int
    model_id: int | None = None
    year_from: int
    year_to: int
    displacement_l: Annotated[float, Field(ge=0.5, le=10)] | None = None
    engine_family_id: int | None = None

    @field_validator("year_from", "year_to")
    @classmethod
    def _year(cls, v: int) -> int:
        if not MIN_YEAR - 31 <= v <= max_year():  # allow pre-1981 classics too
            raise ValueError("year out of range")
        return v


class Tags(BaseModel):
    applies_to: Annotated[list[AppliesTo], Field(max_length=50)] = []  # empty = all vehicles
    systems: Annotated[list[str], Field(max_length=10)] = []
    dtcs: Annotated[list[str], Field(max_length=30)] = []

    @field_validator("dtcs")
    @classmethod
    def _codes(cls, v: list[str]) -> list[str]:
        return sorted({validate_code(c) for c in v})


class EntryIn(BaseModel):
    kind: Kind
    title: Annotated[str, Field(min_length=3, max_length=200)]
    data: dict
    tags: Tags = Tags()
    edit_summary: Annotated[str, Field(max_length=300)] | None = None


class EntryEdit(BaseModel):
    base_revision: int  # the revision number you started editing from (conflict check)
    title: Annotated[str, Field(min_length=3, max_length=200)]
    data: dict
    tags: Tags = Tags()
    edit_summary: Annotated[str, Field(min_length=1, max_length=300)]


class Person(BaseModel):
    id: int | None
    display_name: str
    role: str | None = None


class RevisionOut(BaseModel):
    id: int
    number: int
    title: str
    data: dict
    tags: dict
    edit_summary: str | None
    status: str
    author: Person
    created_at: datetime
    fact_check: dict | None = None
    unverified: int = 0  # values marked UNVERIFIED in this version


class Verification(BaseModel):
    state: Literal["verified", "verified_older", "none"]
    by: Person | None = None
    at: datetime | None = None
    revision_number: int | None = None


class EntryOut(BaseModel):
    id: int
    kind: Kind
    status: str
    title: str
    score: int
    my_vote: int = 0
    safety_critical: bool
    verification: Verification
    open_reports: int
    under_review: bool = False  # someone reported a mistake; being checked
    pending_revisions: int
    revision: RevisionOut | None
    tags_display: dict
    labor: dict | None = None
    created_at: datetime
    updated_at: datetime


class EntrySummary(BaseModel):
    id: int
    kind: Kind
    title: str
    score: int
    verified: bool
    safety_critical: bool
    generic: bool
    summary: str | None = None
    data: dict | None = None  # spec values, so lists can show them without opening each entry
    updated_at: datetime


class EntryList(BaseModel):
    total: int
    items: list[EntrySummary]


class VoteIn(BaseModel):
    value: Literal[-1, 0, 1]


class ReportIn(BaseModel):
    reason: ReportReason
    section: Annotated[str, Field(max_length=120)] | None = None  # e.g. "Test 3" or "Causes"
    details: Annotated[str, Field(max_length=2000)] | None = None


class LaborReportIn(BaseModel):
    basis: LaborBasis
    hours: Annotated[float, Field(gt=0, le=200)]
    rust: RustLevel = RustLevel.none
    note: Annotated[str, Field(max_length=300)] | None = None


class PhotoOut(BaseModel):
    id: int
    url: str
    width: int
    height: int


class SystemOut(BaseModel):
    slug: str
    parent: str | None
    safety_critical: bool
