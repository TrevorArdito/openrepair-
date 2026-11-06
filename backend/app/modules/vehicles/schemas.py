from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.vehicles.vin import validate_vin

FuelType = Literal[
    "gasoline", "diesel", "electric", "hybrid", "flex", "cng", "lpg", "hydrogen", "other"
]
MIN_YEAR = 1981  # 17-character VINs became standard for model year 1981


def max_year() -> int:
    return date.today().year + 2


class NamedRef(BaseModel):
    id: int
    name: str


class MakeOut(NamedRef):
    common: int | None = None  # rank among the most common US makes (1 = most common)


class EngineOut(BaseModel):
    displacement_l: float | None = None
    cylinders: int | None = None
    layout: str | None = None
    fuel_type: str | None = None
    engine_code: str | None = None
    aspiration: str | None = None
    label: str | None = None
    family: "NamedRef | None" = None


class VehicleOut(BaseModel):
    id: int
    year: int
    make: NamedRef
    model: NamedRef
    engine: EngineOut
    label: str


class VehicleProfileOut(VehicleOut):
    counts: dict[str, int]


class VinDecodeOut(BaseModel):
    vin: str
    check_digit_valid: bool
    vehicle: VehicleOut
    details: dict[str, str]
    warnings: list[str]
    source: str = "NHTSA vPIC"


class VehicleResolveIn(BaseModel):
    year: int
    model_id: int
    displacement_l: float | None = Field(default=None, ge=0.5, le=10.0)
    cylinders: int | None = Field(default=None, ge=1, le=16)
    fuel_type: FuelType | None = None

    @field_validator("year")
    @classmethod
    def _year(cls, v: int) -> int:
        if not MIN_YEAR <= v <= max_year():
            raise ValueError("year out of range")
        return v


class GarageIn(BaseModel):
    vehicle_id: int
    vin: str | None = None
    nickname: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("vin")
    @classmethod
    def _vin(cls, v: str | None) -> str | None:
        return validate_vin(v) if v else None


class GarageUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=2000)


class GarageOut(BaseModel):
    id: int
    vehicle: VehicleOut
    vin: str | None
    nickname: str | None
    notes: str | None
