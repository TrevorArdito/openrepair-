"""What each kind of community entry contains. Validated on every save.

All measurements are stored in metric (SI) and converted for display.
Specs carry their sources so readers can judge how trustworthy a number is."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.community.models import Kind

Text = Annotated[str, Field(min_length=1, max_length=4000)]
Short = Annotated[str, Field(min_length=1, max_length=200)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Source(Strict):
    """Where a number or procedure came from."""

    type: Literal[
        "owner_manual",  # the vehicle's owner's manual (public)
        "oem_public",  # other public manufacturer document (recall/TSB notice, spec sheet)
        "measured",  # contributor measured it themselves
        "experience",  # contributor's professional experience
        "industry_standard",  # standard practice / published standard (SAE, ASE study guides)
        "other",
    ]
    citation: Annotated[str, Field(max_length=300)] = ""


# ---- Procedure (repair guide) -----------------------------------------------


class Step(Strict):
    text: Text
    caution: Annotated[str, Field(max_length=500)] | None = None
    torque_nm: Annotated[float, Field(gt=0, le=5000)] | None = None
    torque_label: Annotated[str, Field(max_length=120)] | None = None
    photo_id: int | None = None
    diagram: Annotated[str, Field(max_length=60)] | None = None  # id of a built-in diagram


class ProcedureData(Strict):
    summary: Text
    difficulty: Annotated[int, Field(ge=1, le=5)] = 3
    time_minutes: Annotated[int, Field(ge=1, le=6000)] | None = None
    tools: list[Short] = []
    parts: list[Short] = []
    warnings: list[Annotated[str, Field(max_length=500)]] = []
    steps: Annotated[list[Step], Field(min_length=1, max_length=200)]
    notes: Annotated[str, Field(max_length=4000)] | None = None
    sources: list[Source] = []


# ---- Torque spec -------------------------------------------------------------


class TorqueStage(Strict):
    """One tightening pass: either a torque value or an extra angle (torque-to-yield)."""

    type: Literal["torque", "angle"]
    value_nm: Annotated[float, Field(gt=0, le=5000)] | None = None
    degrees: Annotated[int, Field(gt=0, le=360)] | None = None

    @model_validator(mode="after")
    def _one_value(self):
        if self.type == "torque" and self.value_nm is None:
            raise ValueError("torque stage needs value_nm")
        if self.type == "angle" and self.degrees is None:
            raise ValueError("angle stage needs degrees")
        return self


class TorqueSpecData(Strict):
    component: Short  # e.g. "Front brake caliper bracket"
    fastener: Annotated[str, Field(max_length=200)] | None = None  # e.g. "M12 bolt, 2 per side"
    stages: Annotated[list[TorqueStage], Field(min_length=1, max_length=8)]
    thread_condition: Literal["dry", "oiled", "threadlocker", "anti_seize", "unspecified"] = (
        "unspecified"
    )
    replace_fasteners: bool = False  # torque-to-yield / one-time-use
    sequence_note: Annotated[str, Field(max_length=1000)] | None = None
    notes: Annotated[str, Field(max_length=2000)] | None = None
    sources: Annotated[list[Source], Field(min_length=1)]

    @model_validator(mode="after")
    def _first_is_torque(self):
        if self.stages[0].type != "torque":
            raise ValueError("first stage must be a torque value")
        return self


# ---- Fluid capacity ------------------------------------------------------------

FluidSystem = Literal[
    "engine_oil",
    "coolant",
    "automatic_transmission",
    "manual_transmission",
    "cvt",
    "transfer_case",
    "front_differential",
    "rear_differential",
    "brake",
    "power_steering",
    "refrigerant",
    "refrigerant_oil",
    "fuel_tank",
    "washer",
    "other",
]


class FluidCapacityData(Strict):
    system: FluidSystem
    amount: Annotated[float, Field(gt=0, le=2000)] | None = (
        None  # None = type only (e.g. brake fluid)
    )
    amount_max: Annotated[float, Field(gt=0, le=2000)] | None = None  # ranges: "2.0–2.1 qt"
    amount_unit: Literal["L", "kg", "g", "mL"] = "L"  # refrigerant is by weight
    condition: Annotated[str, Field(max_length=200)] | None = None  # "with filter", "drain & fill"
    fluid_spec: Annotated[str, Field(max_length=300)] | None = None  # "SAE 0W-20, API SP"
    printed: Annotated[str, Field(max_length=100)] | None = None  # exactly as the source prints it
    notes: Annotated[str, Field(max_length=2000)] | None = None
    sources: Annotated[list[Source], Field(min_length=1)]

    @model_validator(mode="after")
    def _amount_or_type(self):
        if self.amount is None and not self.fluid_spec:
            raise ValueError("give an amount, a fluid type, or both")
        if self.amount_max is not None and (self.amount is None or self.amount_max < self.amount):
            raise ValueError("amount_max needs an amount and must not be smaller than it")
        return self


# ---- Other specs (gaps, pressures, resistances, ...) ---------------------------

Quantity = Literal[
    "length",  # mm (converted to in)
    "pressure",  # kPa (converted to psi)
    "temperature",  # °C (converted to °F)
    "mass",  # kg (converted to lb)
    "volume",  # L (converted to qt)
    "voltage",  # V
    "resistance",  # ohm
    "current",  # A
    "speed_rpm",  # rpm
    "percent",  # %
    "time_s",  # seconds
    "other",
]


class SpecData(Strict):
    name: Short  # e.g. "Spark plug gap"
    quantity: Quantity
    value: float | None = None
    value_max: float | None = None  # for ranges ("0.9–1.1 mm")
    text: Annotated[str, Field(max_length=200)] | None = (
        None  # non-numeric specs: "1-4-2-5-3-6", "10.0:1"
    )
    unit_other: Annotated[str, Field(max_length=20)] | None = None  # only for quantity "other"
    condition: Annotated[str, Field(max_length=200)] | None = None  # "engine warm, at idle"
    printed: Annotated[str, Field(max_length=100)] | None = None  # exactly as the source prints it
    notes: Annotated[str, Field(max_length=2000)] | None = None
    sources: Annotated[list[Source], Field(min_length=1)]

    @model_validator(mode="after")
    def _range(self):
        if self.value is None and not self.text:
            raise ValueError("give a value or a text spec")
        if self.value_max is not None and (self.value is None or self.value_max < self.value):
            raise ValueError("value_max must be >= value")
        return self


# ---- Part note -----------------------------------------------------------------


class PartNoteData(Strict):
    part_name: Short
    oem_numbers: list[Annotated[str, Field(max_length=60)]] = []
    aftermarket: list[Annotated[str, Field(max_length=120)]] = []  # "Brand 12345 (fits, tested)"
    fitment_notes: Annotated[str, Field(max_length=2000)] | None = None
    notes: Annotated[str, Field(max_length=2000)] | None = None
    sources: list[Source] = []


# ---- Labor time ----------------------------------------------------------------


class LaborTimeData(Strict):
    """Describes the job. The hours come from many people's reports (LaborReport),
    shown side by side: warranty time, flat-rate guide time, real pro time, real DIY
    time — each split by rust condition."""

    job: Short  # "Replace front brake pads and rotors (both sides)"
    includes: list[Annotated[str, Field(max_length=200)]] = []
    excludes: list[Annotated[str, Field(max_length=200)]] = []
    notes: Annotated[str, Field(max_length=2000)] | None = None


KIND_SCHEMAS: dict[Kind, type[Strict]] = {
    Kind.procedure: ProcedureData,
    Kind.torque_spec: TorqueSpecData,
    Kind.fluid_capacity: FluidCapacityData,
    Kind.spec: SpecData,
    Kind.part_note: PartNoteData,
    Kind.labor_time: LaborTimeData,
}

# Torque specs always carry the safety disclaimer.
ALWAYS_SAFETY_CRITICAL = {Kind.torque_spec}


def validate_data(kind: Kind, data: dict) -> dict:
    return KIND_SCHEMAS[kind].model_validate(data).model_dump(mode="json", exclude_none=True)
