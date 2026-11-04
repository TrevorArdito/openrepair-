from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db import get_db
from app.modules.safety import service
from app.modules.safety.models import Complaint, ComplaintVehicle, DataImport
from app.modules.safety.nhtsa import NhtsaApi, get_nhtsa
from app.modules.safety.schemas import ComplaintList, RecallList, TsbList
from app.modules.vehicles.models import Vehicle

router = APIRouter(prefix="/vehicles/{vehicle_id}", tags=["safety"])
service.register_counters()


def _vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise NotFound("vehicle_not_found")
    return v


def _nhtsa_url(v: Vehicle) -> str:
    make, model = quote(v.model.make.name.upper()), quote(v.model.name.upper())
    return f"https://www.nhtsa.gov/vehicle/{v.year}/{make}/{model}"


@router.get("/recalls", response_model=RecallList)
def recalls(
    q: str | None = Query(default=None, max_length=100),
    v: Vehicle = Depends(_vehicle),
    db: Session = Depends(get_db),
    nhtsa: NhtsaApi = Depends(get_nhtsa),
):
    fresh = service.refresh(db, nhtsa, "recalls", v)
    items = service.list_recalls(db, v, q)
    return RecallList(total=len(items), items=items, source_url=_nhtsa_url(v), **fresh)


@router.get("/complaints", response_model=ComplaintList)
def complaints(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    v: Vehicle = Depends(_vehicle),
    db: Session = Depends(get_db),
    nhtsa: NhtsaApi = Depends(get_nhtsa),
):
    fresh = service.refresh(db, nhtsa, "complaints", v)
    total, items = service.list_complaints(db, v, q, limit, offset)
    mk, mo, year = service.vehicle_keys(v)
    all_components = db.scalars(
        select(Complaint.components)
        .join(ComplaintVehicle)
        .where(
            ComplaintVehicle.make_key == mk,
            ComplaintVehicle.model_key == mo,
            ComplaintVehicle.year == year,
        )
    )
    return ComplaintList(
        total=total,
        items=items,
        components=service.component_counts(all_components),
        source_url=_nhtsa_url(v),
        **fresh,
    )


@router.get("/tsbs", response_model=TsbList)
def tsbs(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    v: Vehicle = Depends(_vehicle),
    db: Session = Depends(get_db),
):
    total, items = service.list_tsbs(db, v, q, limit, offset)
    last = db.scalar(
        select(DataImport.finished_at)
        .where(DataImport.source == "tsbs", DataImport.status == "ok")
        .order_by(DataImport.finished_at.desc())
        .limit(1)
    )
    return TsbList(total=total, items=items, source_url=_nhtsa_url(v), last_import=last)
