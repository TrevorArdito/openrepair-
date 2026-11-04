"""ZIP code centre points for distance search (US Census Bureau ZCTA gazetteer, public domain)."""

import csv
import gzip
import math
from pathlib import Path

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.modules.marketplace.models import ZipPoint

FILE = Path(__file__).resolve().parents[2] / "seed" / "data" / "zip_points.csv.gz"
MILES_PER_DEG_LAT = 69.0


def load(db: Session) -> int:
    """Load the ZIP file once (skipped when the table already has rows)."""
    if db.scalar(select(func.count()).select_from(ZipPoint)):
        return 0
    with gzip.open(FILE, "rt", newline="") as f:
        rows = [
            {"zip": r["zip"], "lat": float(r["lat"]), "lon": float(r["lon"])}
            for r in csv.DictReader(f)
        ]
    for i in range(0, len(rows), 5000):
        db.execute(insert(ZipPoint), rows[i : i + 5000])
    db.flush()
    return len(rows)


def miles(a: ZipPoint, b: ZipPoint) -> float:
    """Great-circle distance in miles (haversine)."""
    la1, lo1, la2, lo2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = (
        math.sin((la2 - la1) / 2) ** 2
        + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    )
    return 3958.8 * 2 * math.asin(math.sqrt(h))
