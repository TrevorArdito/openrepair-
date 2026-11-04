"""Vehicle lookups: VIN decode, year/make/model/engine, find-or-create vehicles."""

import re
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFound
from app.modules.vehicles.models import Make, Model, ModelYear, Vehicle, VinDecode, VpicFetch
from app.modules.vehicles.schemas import EngineOut, NamedRef, VehicleOut, VinDecodeOut
from app.modules.vehicles.vin import check_digit_valid, validate_vin
from app.modules.vehicles.vpic import VpicApi

# Other modules (recalls, guides, ...) register a counter so the vehicle profile
# can show "3 recalls, 12 guides" without this module knowing about them.
ProfileCounter = Callable[[Session, Vehicle], int]
PROFILE_COUNTERS: dict[str, ProfileCounter] = {}

FUEL_MAP = {
    "gasoline": "gasoline",
    "diesel": "diesel",
    "electric": "electric",
    "flexible fuel vehicle (ffv)": "gasoline",
    "ethanol (e85)": "gasoline",
    "compressed natural gas (cng)": "cng",
    "liquefied petroleum gas (propane or lpg)": "lpg",
}
LAYOUT_MAP = {"v-shaped": "v", "in-line": "inline", "horizontally opposed (boxer)": "flat"}
LAYOUT_PREFIX = {"v": "V", "inline": "I", "flat": "H"}
DETAIL_FIELDS = {
    "trim": "Trim",
    "series": "Series",
    "body_class": "BodyClass",
    "drive_type": "DriveType",
    "transmission": "TransmissionStyle",
    "engine_model": "EngineModel",
    "engine_hp": "EngineHP",
    "vehicle_type": "VehicleType",
    "manufacturer": "Manufacturer",
    "plant_country": "PlantCountry",
}
NA_VALUES = {"", "Not Applicable", "null", None}


def make_display_name(raw: str) -> str:
    keep_upper = {"BMW", "GMC", "MINI", "AMC", "MG", "BYD"}
    raw = raw.strip()
    if raw.upper() in keep_upper:
        return raw.upper()
    return "-".join(part.title() for part in raw.split("-"))


ASPIRATION_SUFFIX = {"turbo": "T", "supercharged": "S", "twincharged": "TS"}


def config_key(year, model_id, displacement, cylinders, fuel, aspiration=None) -> str:
    """Identity of a year/model/engine. Turbo/supercharged engines get a suffix so a
    3.5L turbo V6 and a 3.5L non-turbo V6 in the same truck stay separate."""
    disp = f"{displacement:.1f}" if displacement else ""
    key = f"{year}|{model_id}|{disp}|{cylinders or ''}|{fuel or ''}"
    return f"{key}|{ASPIRATION_SUFFIX[aspiration]}" if aspiration in ASPIRATION_SUFFIX else key


def engine_label(v: Vehicle) -> str | None:
    parts = []
    if v.engine_displacement_l:
        parts.append(f"{v.engine_displacement_l:.1f}L")
    if v.cylinders:
        parts.append(f"{LAYOUT_PREFIX.get(v.engine_layout or '', '')}{v.cylinders}".strip())
        if not v.engine_layout:
            parts[-1] = f"{v.cylinders}-cyl"
    if v.aspiration == "turbo":
        parts.append("Turbo")
    elif v.aspiration == "supercharged":
        parts.append("Supercharged")
    elif v.aspiration == "twincharged":
        parts.append("Turbo + Supercharged")
    if v.fuel_type in ("diesel", "electric", "hybrid", "cng", "lpg", "hydrogen"):
        parts.append(v.fuel_type.capitalize())
    return " ".join(parts) or None


def vehicle_out(v: Vehicle) -> VehicleOut:
    model = v.model
    make = model.make
    elabel = engine_label(v)
    label = " ".join(x for x in (str(v.year), make.name, model.name, elabel) if x)
    return VehicleOut(
        id=v.id,
        year=v.year,
        make=NamedRef(id=make.id, name=make.name),
        model=NamedRef(id=model.id, name=model.name),
        engine=EngineOut(
            displacement_l=v.engine_displacement_l,
            cylinders=v.cylinders,
            layout=v.engine_layout,
            fuel_type=v.fuel_type,
            engine_code=v.engine_code,
            aspiration=v.aspiration,
            label=elabel,
            family=NamedRef(id=v.engine_family.id, name=v.engine_family.name)
            if v.engine_family
            else None,
        ),
        label=label,
    )


def get_or_create_make(db: Session, vpic_id: int | None, name: str) -> Make:
    make = db.scalar(select(Make).where(Make.vpic_make_id == vpic_id)) if vpic_id else None
    if make is None:
        make = db.scalar(select(Make).where(Make.name == make_display_name(name)))
        if make is not None and vpic_id and make.vpic_make_id is None:
            make.vpic_make_id = vpic_id
    if make is None:
        make = Make(name=make_display_name(name), vpic_make_id=vpic_id)
        db.add(make)
        db.flush()
    return make


def _name_key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def get_or_create_model(db: Session, make: Make, vpic_id: int | None, name: str) -> Model:
    model = db.scalar(select(Model).where(Model.vpic_model_id == vpic_id)) if vpic_id else None
    if model is None:
        # Match ignoring punctuation/spaces: NHTSA "F-250" == EPA "F250".
        key = _name_key(name)
        model = next(
            (
                m
                for m in db.scalars(select(Model).where(Model.make_id == make.id))
                if _name_key(m.name) == key
            ),
            None,
        )
        if model is not None and vpic_id and model.vpic_model_id is None:
            model.vpic_model_id = vpic_id  # e.g. a seeded model we can now link to NHTSA
    if model is None:
        model = Model(make_id=make.id, name=name.strip(), vpic_model_id=vpic_id)
        db.add(model)
        db.flush()
    return model


def ensure_model_year(db: Session, model: Model, year: int) -> None:
    exists = db.scalar(
        select(ModelYear.id).where(ModelYear.model_id == model.id, ModelYear.year == year)
    )
    if not exists:
        db.add(ModelYear(model_id=model.id, make_id=model.make_id, year=year))
        db.flush()


def get_or_create_vehicle(
    db: Session,
    *,
    year: int,
    model: Model,
    displacement_l: float | None = None,
    cylinders: int | None = None,
    fuel_type: str | None = None,
    engine_layout: str | None = None,
    engine_code: str | None = None,
    aspiration: str | None = None,
    source: str | None = None,
) -> Vehicle:
    if displacement_l:
        displacement_l = round(displacement_l, 1)
    if fuel_type == "flex":  # flex-fuel engines are gasoline engines that also take E85
        fuel_type = "gasoline"
    key = config_key(year, model.id, displacement_l, cylinders, fuel_type, aspiration)
    vehicle = db.scalar(select(Vehicle).where(Vehicle.config_key == key))
    if vehicle is None and aspiration is None and displacement_l:
        # Turbo unknown (common in VIN data): use the only matching engine if there is one.
        base = config_key(year, model.id, displacement_l, cylinders, fuel_type)
        candidates = db.scalars(
            select(Vehicle).where(Vehicle.config_key.startswith(base + "|"))
        ).all()
        if len(candidates) == 1:
            vehicle = candidates[0]
    if vehicle is None:
        vehicle = Vehicle(
            config_key=key,
            year=year,
            model_id=model.id,
            engine_displacement_l=displacement_l,
            cylinders=cylinders,
            fuel_type=fuel_type,
            engine_layout=engine_layout,
            engine_code=engine_code,
            aspiration=aspiration,
            source=source,
        )
        db.add(vehicle)
        db.flush()
    else:
        vehicle.engine_layout = vehicle.engine_layout or engine_layout
        vehicle.engine_code = vehicle.engine_code or engine_code
    ensure_model_year(db, model, year)
    return vehicle


def _clean(raw: dict[str, Any]) -> dict[str, str]:
    return {k: str(v).strip() for k, v in raw.items() if v not in NA_VALUES and str(v).strip()}


def _float(v: str | None) -> float | None:
    try:
        return float(v) if v else None
    except ValueError:
        return None


def _int(v: str | None) -> int | None:
    try:
        return int(float(v)) if v else None
    except ValueError:
        return None


def _decode_result(vin: str, record: VinDecode) -> VinDecodeOut:
    raw = record.raw
    warnings = []
    codes = {c.strip() for c in raw.get("ErrorCode", "0").split(",")}
    if codes - {"0"} and raw.get("ErrorText"):
        warnings.append(raw["ErrorText"])
    if raw.get("AdditionalErrorText"):
        warnings.append(raw["AdditionalErrorText"])
    return VinDecodeOut(
        vin=vin,
        check_digit_valid=check_digit_valid(vin),
        vehicle=vehicle_out(record.vehicle),
        details={k: raw[src] for k, src in DETAIL_FIELDS.items() if raw.get(src)},
        warnings=warnings,
    )


def decode_vin(db: Session, vpic: VpicApi, raw_vin: str) -> VinDecodeOut:
    vin = validate_vin(raw_vin)
    cached = db.scalar(select(VinDecode).where(VinDecode.vin == vin))
    if cached:
        return _decode_result(vin, cached)

    raw = _clean(vpic.decode_vin(vin))
    year = _int(raw.get("ModelYear"))
    if not (raw.get("Make") and raw.get("Model") and year):
        raise AppError("vin_not_decodable", 422)

    make = get_or_create_make(db, _int(raw.get("MakeID")), raw["Make"])
    model = get_or_create_model(db, make, _int(raw.get("ModelID")), raw["Model"])
    fuel = raw.get("FuelTypePrimary", "").lower()
    if "electric" in raw.get("ElectrificationLevel", "").lower() and fuel != "electric":
        fuel = "hybrid"
    vehicle = get_or_create_vehicle(
        db,
        year=year,
        model=model,
        displacement_l=_float(raw.get("DisplacementL")),
        cylinders=_int(raw.get("EngineCylinders")),
        fuel_type=FUEL_MAP.get(fuel, "other" if fuel and fuel != "hybrid" else fuel or None),
        engine_layout=LAYOUT_MAP.get(raw.get("EngineConfiguration", "").lower()),
        engine_code=raw.get("EngineModel"),
        aspiration="turbo" if raw.get("Turbo", "").lower() == "yes" else None,
        source="vin",
    )
    record = VinDecode(vin=vin, vehicle_id=vehicle.id, raw=raw)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _decode_result(vin, record)


def list_models(db: Session, vpic: VpicApi, year: int, make_id: int) -> list[Model]:
    make = db.get(Make, make_id)
    if make is None:
        raise NotFound("make_not_found")

    def query():
        return db.scalars(
            select(Model)
            .join(ModelYear, ModelYear.model_id == Model.id)
            .where(ModelYear.make_id == make_id, ModelYear.year == year)
            .order_by(Model.name)
        ).all()

    models = query()
    # Ask NHTSA once per make+year; after that the list comes from our database.
    if make.vpic_make_id and not _fetched(db, make_id, year):
        for row in vpic.models_for_make_year(make.vpic_make_id, year):
            model = get_or_create_model(db, make, int(row["Model_ID"]), row["Model_Name"])
            ensure_model_year(db, model, year)
        _mark_fetched(db, make_id, year)
        db.commit()
        models = query()
    return list(models)


def _fetched(db: Session, make_id: int, year: int) -> bool:
    return bool(
        db.scalar(select(VpicFetch.id).where(VpicFetch.make_id == make_id, VpicFetch.year == year))
    )


def _mark_fetched(db: Session, make_id: int, year: int) -> None:
    db.add(VpicFetch(make_id=make_id, year=year))
