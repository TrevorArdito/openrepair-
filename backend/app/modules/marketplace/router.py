"""Marketplace API (/api/v1/market/...). Loaded only when ENABLE_MARKETPLACE=true."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.deps import current_user, optional_user, require_role, verify_csrf
from app.core.errors import NotFound
from app.core.ratelimit import rate_limit
from app.db import get_db
from app.modules.accounts.models import Role, User
from app.modules.accounts.router import EXPORT_HOOKS
from app.modules.marketplace import rules, service
from app.modules.marketplace.models import (
    Conversation,
    Listing,
    ListingReport,
    ListingStatus,
    Seller,
    SellerStatus,
    SellerVerification,
    VerificationStatus,
)
from app.modules.marketplace.schemas import (
    ConversationOut,
    ListingIn,
    ListingOut,
    MessageIn,
    ModListingIn,
    ModReportIn,
    ModSellerIn,
    ModVerificationIn,
    ReportIn,
    SellerIn,
    SellerOut,
    StatusIn,
    VerificationIn,
    VerificationOut,
)
from app.modules.vehicles.models import Vehicle

router = APIRouter(prefix="/market", tags=["marketplace"])
EXPORT_HOOKS.append(service.export_for)
moderator = require_role(Role.moderator)


def _listing(db: Session, listing_id: int, viewer: User | None) -> Listing:
    listing = db.get(Listing, listing_id)
    if listing is None or not service.can_view(listing, viewer):
        raise NotFound("listing_not_found")
    return listing


@router.get("/categories")
def categories():
    return [{"slug": c, "system": s} for c, s in rules.CATEGORIES.items()]


# ---- seller profile ----------------------------------------------------------------


@router.get("/seller/me", response_model=SellerOut | None)
def my_seller(user: User = Depends(current_user), db: Session = Depends(get_db)):
    seller = service.seller_for(db, user)
    return service.seller_out(db, seller, private=True) if seller else None


@router.put("/seller/me", response_model=SellerOut, dependencies=[Depends(verify_csrf)])
def save_my_seller(
    data: SellerIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    seller = service.save_seller(db, user, data)
    db.commit()
    return service.seller_out(db, seller, private=True)


@router.get("/seller/me/verifications", response_model=list[VerificationOut])
def my_verifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    seller = service.seller_for(db, user)
    if seller is None:
        return []
    rows = db.scalars(
        select(SellerVerification)
        .where(SellerVerification.seller_id == seller.id)
        .order_by(SellerVerification.id.desc())
    )
    return [VerificationOut.model_validate(v, from_attributes=True) for v in rows]


@router.post(
    "/seller/me/verifications",
    response_model=VerificationOut,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_verify", 5, 86400))],
)
def request_verification(
    data: VerificationIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    seller = service.require_seller(db, user)
    v = SellerVerification(seller_id=seller.id, **data.model_dump())
    db.add(v)
    db.commit()
    return VerificationOut.model_validate(v, from_attributes=True)


@router.get("/sellers/{seller_id}", response_model=SellerOut)
def public_seller(seller_id: int, db: Session = Depends(get_db)):
    seller = db.get(Seller, seller_id)
    if seller is None or seller.status != SellerStatus.active:
        raise NotFound("seller_not_found")
    return service.seller_out(db, seller)


# ---- listings ----------------------------------------------------------------------


@router.get("/listings")
def browse(
    q: str | None = Query(None, max_length=100),
    category: str | None = None,
    condition: str | None = None,
    vehicle_id: int | None = None,
    seller_id: int | None = None,
    state: str | None = Query(None, max_length=2),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    sort: str = "newest",
    limit: int = Query(24, ge=1, le=service.PAGE_MAX),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    vehicle = db.get(Vehicle, vehicle_id) if vehicle_id else None
    if vehicle_id and vehicle is None:
        raise NotFound("vehicle_not_found")
    total, rows = service.search(
        db, q=q, category=category, condition=condition, vehicle=vehicle, state=state,
        min_price=min_price, max_price=max_price, sort=sort, limit=limit, offset=offset,
        seller_id=seller_id,
    )  # fmt: skip
    return {"total": total, "items": [service.summary(db, ls) for ls in rows]}


@router.get("/my/listings")
def my_listings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    seller = service.seller_for(db, user)
    if seller is None:
        return []
    rows = db.scalars(
        select(Listing).where(Listing.seller_id == seller.id).order_by(Listing.updated_at.desc())
    )
    return [service.summary(db, ls) for ls in rows]


@router.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(
    listing_id: int, user: User | None = Depends(optional_user), db: Session = Depends(get_db)
):
    return service.detail(db, _listing(db, listing_id, user), user)


@router.post(
    "/listings",
    response_model=ListingOut,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_list", 30, 3600))],
)
def create_listing(
    data: ListingIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    listing = service.save_listing(db, user, data, None)
    db.commit()
    return service.detail(db, listing, user)


@router.put(
    "/listings/{listing_id}",
    response_model=ListingOut,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_list", 30, 3600))],
)
def update_listing(
    listing_id: int,
    data: ListingIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    listing = db.get(Listing, listing_id)
    if listing is None or listing.seller.user_id != user.id:
        raise NotFound("listing_not_found")
    service.save_listing(db, user, data, listing)
    db.commit()
    return service.detail(db, listing, user)


@router.post(
    "/listings/{listing_id}/status", response_model=ListingOut, dependencies=[Depends(verify_csrf)]
)
def change_status(
    listing_id: int,
    data: StatusIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    listing = db.get(Listing, listing_id)
    if listing is None or listing.seller.user_id != user.id:
        raise NotFound("listing_not_found")
    service.set_status(db, user, listing, data.status)
    db.commit()
    return service.detail(db, listing, user)


@router.post(
    "/listings/{listing_id}/report",
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_report", 20, 3600))],
)
def report_listing(
    listing_id: int,
    data: ReportIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    listing = _listing(db, listing_id, user)
    db.add(ListingReport(listing_id=listing.id, reporter_id=user.id, **data.model_dump()))
    db.commit()
    return {"status": "received"}


# ---- messages ----------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/messages",
    response_model=ConversationOut,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_msg", 60, 3600))],
)
def message_seller(
    listing_id: int,
    data: MessageIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    listing = _listing(db, listing_id, user)
    conv = service.start_or_continue(db, user, listing, data.body)
    db.commit()
    return service.conversation_out(db, conv, user, with_messages=True)


@router.get("/conversations", response_model=list[ConversationOut])
def conversations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [service.conversation_out(db, c, user) for c in service.my_conversations(db, user)]


def _conversation(db: Session, conv_id: int, user: User) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if conv is None or service.participant_role(conv, user) is None:
        raise NotFound("conversation_not_found")
    return conv


@router.get("/conversations/{conv_id}", response_model=ConversationOut)
def conversation(conv_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    conv = _conversation(db, conv_id, user)
    out = service.conversation_out(db, conv, user, with_messages=True)
    for m in conv.messages:  # opening the thread marks the other person's messages read
        if m.sender_id != user.id and not m.read:
            m.read = True
    db.commit()
    return out


@router.post(
    "/conversations/{conv_id}/messages",
    response_model=ConversationOut,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_msg", 60, 3600))],
)
def reply(
    conv_id: int,
    data: MessageIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    conv = _conversation(db, conv_id, user)
    service.add_message(db, user, conv, data.body)
    db.commit()
    db.refresh(conv)
    return service.conversation_out(db, conv, user, with_messages=True)


# ---- moderation --------------------------------------------------------------------


@router.get("/mod/queue")
def mod_queue(_: User = Depends(moderator), db: Session = Depends(get_db)):
    pending = db.scalars(
        select(Listing).where(Listing.status == ListingStatus.pending).order_by(Listing.id)
    ).all()
    reports = db.scalars(
        select(ListingReport).where(ListingReport.status == "open").order_by(ListingReport.id)
    ).all()
    verifs = db.scalars(
        select(SellerVerification)
        .where(SellerVerification.status == VerificationStatus.pending)
        .order_by(SellerVerification.id)
    ).all()
    return {
        "pending_listings": [service.summary(db, ls) for ls in pending],
        "reports": [
            {
                "id": r.id,
                "listing_id": r.listing_id,
                "listing_title": db.get(Listing, r.listing_id).title,
                "reason": r.reason,
                "details": r.details,
                "created_at": r.created_at,
            }
            for r in reports
        ],
        "verifications": [
            {
                **VerificationOut.model_validate(v, from_attributes=True).model_dump(),
                "seller_id": v.seller_id,
                "seller_name": db.get(Seller, v.seller_id).display_name,
            }
            for v in verifs
        ],
    }


@router.post("/mod/listings/{listing_id}", dependencies=[Depends(verify_csrf)])
def mod_listing(
    listing_id: int,
    data: ModListingIn,
    mod: User = Depends(moderator),
    db: Session = Depends(get_db),
):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise NotFound("listing_not_found")
    listing.status = {
        "approve": ListingStatus.active,
        "remove": ListingStatus.removed,
        "restore": ListingStatus.active,
    }[data.action]
    listing.status_reason = data.reason if data.action == "remove" else None
    log_action(db, mod, f"listing_{data.action}", "listing", listing.id, data.reason)
    db.commit()
    return {"status": listing.status}


@router.post("/mod/reports/{report_id}", dependencies=[Depends(verify_csrf)])
def mod_report(
    report_id: int,
    data: ModReportIn,
    mod: User = Depends(moderator),
    db: Session = Depends(get_db),
):
    report = db.get(ListingReport, report_id)
    if report is None:
        raise NotFound("report_not_found")
    report.status = "resolved" if data.action == "resolve" else "dismissed"
    report.resolved_by_id = mod.id
    report.resolved_at = datetime.now(UTC)
    log_action(db, mod, f"listing_report_{data.action}", "listing_report", report.id)
    db.commit()
    return {"status": report.status}


@router.post("/mod/verifications/{verification_id}", dependencies=[Depends(verify_csrf)])
def mod_verification(
    verification_id: int,
    data: ModVerificationIn,
    mod: User = Depends(moderator),
    db: Session = Depends(get_db),
):
    v = db.get(SellerVerification, verification_id)
    if v is None:
        raise NotFound("verification_not_found")
    v.status = (
        VerificationStatus.approved if data.action == "approve" else VerificationStatus.rejected
    )
    v.note = data.note
    v.reviewed_by_id = mod.id
    v.reviewed_at = datetime.now(UTC)
    log_action(db, mod, f"seller_verification_{data.action}", "seller", v.seller_id, data.note)
    db.commit()
    return {"status": v.status}


@router.post("/mod/sellers/{seller_id}", dependencies=[Depends(verify_csrf)])
def mod_seller(
    seller_id: int,
    data: ModSellerIn,
    mod: User = Depends(moderator),
    db: Session = Depends(get_db),
):
    seller = db.get(Seller, seller_id)
    if seller is None:
        raise NotFound("seller_not_found")
    seller.status = SellerStatus.suspended if data.action == "suspend" else SellerStatus.active
    log_action(db, mod, f"seller_{data.action}", "seller", seller.id, data.reason)
    db.commit()
    return {"status": seller.status}
