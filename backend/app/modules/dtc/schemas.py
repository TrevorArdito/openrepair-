from pydantic import BaseModel, ConfigDict


class DtcSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    severity: str


class Structure(BaseModel):
    system: str
    generic: bool
    subsystem: str | None


class DtcOut(BaseModel):
    code: str
    known: bool
    structure: Structure
    title: str | None = None
    description: str | None = None
    symptoms: list[str] = []
    causes: list[str] = []
    diagnostic_steps: list[str] = []
    severity: str | None = None
    systems: list[str] = []
    source: str | None = None
    source_license: str | None = None
    related_entries: list[dict] = []
