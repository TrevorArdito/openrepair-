from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.core.ratelimit import rate_limit
from app.db import get_db
from app.modules.search import service
from app.modules.vehicles.models import Vehicle

router = APIRouter(tags=["search"])
TYPES = {"codes", "vehicles", "engines", "entries", "recalls", "tsbs"}


@router.get("/search", dependencies=[Depends(rate_limit("search", 120, 60))])
def search(
    q: str = Query(min_length=1, max_length=100),
    vehicle_id: int | None = None,
    types: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    vehicle = None
    if vehicle_id is not None:
        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle is None:
            raise NotFound("vehicle_not_found")
    return service.search(db, q, vehicle, set(types) & TYPES or None)
