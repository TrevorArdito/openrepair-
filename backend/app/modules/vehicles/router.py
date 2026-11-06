from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import current_user, verify_csrf
from app.core.errors import AppError, NotFound
from app.db import get_db
from app.modules.accounts.models import User
from app.modules.vehicles import service
from app.modules.vehicles.models import GarageVehicle, Make, Model, Vehicle
from app.modules.vehicles.schemas import (
    MIN_YEAR,
    GarageIn,
    GarageOut,
    GarageUpdate,
    MakeOut,
    NamedRef,
    VehicleOut,
    VehicleProfileOut,
    VehicleResolveIn,
    VinDecodeOut,
)
from app.modules.vehicles.vpic import VpicApi, get_vpic

router = APIRouter(tags=["vehicles"])
GARAGE_LIMIT = 50


@router.get("/vehicles/decode/{vin}", response_model=VinDecodeOut)
def decode(vin: str, db: Session = Depends(get_db), vpic: VpicApi = Depends(get_vpic)):
    return service.decode_vin(db, vpic, vin)


@router.get("/vehicles/years", response_model=list[int])
def years():
    return list(range(date.today().year + 1, MIN_YEAR - 1, -1))


# Makes most US shops see, roughly by vehicles on the road: shown first in make pickers.
COMMON_MAKES = (
    "Ford", "Chevrolet", "Toyota", "Honda", "Nissan", "Jeep", "Ram", "GMC", "Dodge", "Hyundai",
    "Kia", "Subaru", "Mazda", "Volkswagen", "Chrysler", "Buick", "Lexus", "Tesla", "BMW",
    "Mercedes-Benz",
)  # fmt: skip


@router.get("/vehicles/makes", response_model=list[MakeOut])
def makes(popular_only: bool = False, db: Session = Depends(get_db)):
    """All makes A–Z; the most common ones carry a rank so pickers can list them first."""
    q = select(Make).order_by(Make.name)
    if popular_only:
        q = q.where(Make.popular.is_(True))
    rank = {name.lower(): i for i, name in enumerate(COMMON_MAKES, start=1)}
    return [MakeOut(id=m.id, name=m.name, common=rank.get(m.name.lower())) for m in db.scalars(q)]


@router.get("/vehicles/models", response_model=list[NamedRef])
def models(
    year: int = Query(ge=MIN_YEAR),
    make_id: int = Query(ge=1),
    db: Session = Depends(get_db),
    vpic: VpicApi = Depends(get_vpic),
):
    return [NamedRef(id=m.id, name=m.name) for m in service.list_models(db, vpic, year, make_id)]


@router.get("/vehicles/engines", response_model=list[VehicleOut])
def engines(
    year: int = Query(ge=MIN_YEAR), model_id: int = Query(ge=1), db: Session = Depends(get_db)
):
    """Known engine options for a year+model (from VIN decodes, seed data and the community)."""
    rows = db.scalars(
        select(Vehicle)
        .where(Vehicle.year == year, Vehicle.model_id == model_id)
        .order_by(Vehicle.engine_displacement_l, Vehicle.cylinders)
    ).all()
    return [service.vehicle_out(v) for v in rows]


@router.post("/vehicles", response_model=VehicleOut)
def resolve_vehicle(data: VehicleResolveIn, db: Session = Depends(get_db)):
    """Find (or create) the vehicle for a manual year/make/model/engine pick."""
    model = db.get(Model, data.model_id)
    if model is None:
        raise NotFound("model_not_found")
    v = service.get_or_create_vehicle(
        db,
        year=data.year,
        model=model,
        displacement_l=data.displacement_l,
        cylinders=data.cylinders,
        fuel_type=data.fuel_type,
    )
    db.commit()
    return service.vehicle_out(v)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleProfileOut)
def vehicle_profile(vehicle_id: int, db: Session = Depends(get_db)):
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise NotFound("vehicle_not_found")
    counts = {name: fn(db, v) for name, fn in service.PROFILE_COUNTERS.items()}
    return VehicleProfileOut(**service.vehicle_out(v).model_dump(), counts=counts)


# ---- My Garage -------------------------------------------------------------


def _garage_out(g: GarageVehicle) -> GarageOut:
    return GarageOut(
        id=g.id,
        vehicle=service.vehicle_out(g.vehicle),
        vin=g.vin,
        nickname=g.nickname,
        notes=g.notes,
    )


def _own(db: Session, user: User, garage_id: int) -> GarageVehicle:
    g = db.get(GarageVehicle, garage_id)
    if g is None or g.user_id != user.id:
        raise NotFound("garage_vehicle_not_found")
    return g


@router.get("/garage", response_model=list[GarageOut])
def garage_list(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(GarageVehicle)
        .where(GarageVehicle.user_id == user.id)
        .order_by(GarageVehicle.created_at.desc())
    ).all()
    return [_garage_out(g) for g in rows]


@router.post(
    "/garage", response_model=GarageOut, status_code=201, dependencies=[Depends(verify_csrf)]
)
def garage_add(data: GarageIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.get(Vehicle, data.vehicle_id) is None:
        raise NotFound("vehicle_not_found")
    count = len(db.scalars(select(GarageVehicle.id).where(GarageVehicle.user_id == user.id)).all())
    if count >= GARAGE_LIMIT:
        raise AppError("garage_full", 409, limit=GARAGE_LIMIT)
    g = GarageVehicle(user_id=user.id, **data.model_dump())
    db.add(g)
    db.commit()
    db.refresh(g)
    return _garage_out(g)


@router.patch("/garage/{garage_id}", response_model=GarageOut, dependencies=[Depends(verify_csrf)])
def garage_update(
    garage_id: int,
    data: GarageUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    g = _own(db, user, garage_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(g, field, value)
    db.commit()
    return _garage_out(g)


@router.delete("/garage/{garage_id}", status_code=204, dependencies=[Depends(verify_csrf)])
def garage_delete(
    garage_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.delete(_own(db, user, garage_id))
    db.commit()
