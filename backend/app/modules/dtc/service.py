from collections.abc import Callable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.dtc.models import Dtc
from app.modules.dtc.schemas import DtcOut, Structure
from app.modules.dtc.structure import CODE_RE, explain, normalize_code, validate_code

# The community module registers a function that finds guides tagged with a code.
RelatedFinder = Callable[[Session, str], list[dict]]
RELATED_FINDERS: list[RelatedFinder] = []


def search(db: Session, q: str, limit: int = 30) -> list[Dtc]:
    q = q.strip()
    code = normalize_code(q)
    stmt = select(Dtc).where(Dtc.make_id.is_(None))
    if q and (
        CODE_RE.match(code) or (len(code) <= 5 and code[:1] in "PBCU" and code[1:].isalnum())
    ):
        stmt = stmt.where(Dtc.code.startswith(code))
    elif q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Dtc.title).like(like), func.lower(Dtc.description).like(like))
        )
    return list(db.scalars(stmt.order_by(Dtc.code).limit(limit)))


def lookup(db: Session, raw_code: str) -> DtcOut:
    code = validate_code(raw_code)
    structure = Structure(**explain(code))
    related = [item for finder in RELATED_FINDERS for item in finder(db, code)]
    row = db.scalar(select(Dtc).where(Dtc.code == code, Dtc.make_id.is_(None)))
    if row is None:
        return DtcOut(code=code, known=False, structure=structure, related_entries=related)
    return DtcOut(
        code=code,
        known=True,
        structure=structure,
        title=row.title,
        description=row.description,
        symptoms=row.symptoms,
        causes=row.causes,
        diagnostic_steps=row.diagnostic_steps,
        severity=row.severity,
        systems=row.systems,
        source=row.source,
        source_license=row.source_license,
        related_entries=related,
    )
