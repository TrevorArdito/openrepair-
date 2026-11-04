from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RecallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_number: str
    manufacturer: str | None
    component: str | None
    summary: str | None
    consequence: str | None
    remedy: str | None
    notes: str | None
    report_date: date | None
    park_it: bool
    park_outside: bool
    over_the_air: bool


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    odi_number: str
    components: str | None
    summary: str | None
    crash: bool
    fire: bool
    injuries: int
    deaths: int
    incident_date: date | None
    filed_date: date | None


class TsbOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nhtsa_id: int
    bulletin_number: str | None
    bulletin_date: date | None
    comm_type: str | None
    components: str | None
    summary: str | None


class Freshness(BaseModel):
    source: str = "NHTSA"
    source_url: str
    fetched_at: datetime | None = None
    stale: bool = False


class RecallList(Freshness):
    total: int
    items: list[RecallOut]


class ComplaintList(Freshness):
    total: int
    items: list[ComplaintOut]
    components: dict[str, int]


class TsbList(Freshness):
    total: int
    items: list[TsbOut]
    last_import: datetime | None = None
