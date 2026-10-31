from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.dtc import service
from app.modules.dtc.schemas import DtcOut, DtcSummary

router = APIRouter(prefix="/dtcs", tags=["codes"])


@router.get("", response_model=list[DtcSummary])
def search(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.search(db, q, limit)


@router.get("/{code}", response_model=DtcOut)
def lookup(code: str, db: Session = Depends(get_db)):
    return service.lookup(db, code)
