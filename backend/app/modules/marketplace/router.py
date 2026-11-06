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
    Review,
    SavedListing,
    Seller,
    SellerStatus,
    SellerVerification,
    VerificationStatus,
)
from app.modules.marketplace.schemas import (
    BulkVinIn,
    BulkVinResult,
    ConversationOut,
    ListingIn,
    ListingOut,
    MessageIn,
    ModListingIn,
    ModReportIn,
    ModSellerIn,
    ModVerificationIn,
    ReportIn,
    ReviewIn,
    ReviewOut,
    SellerIn,
    SellerOut,
    StatusIn,
    VerificationIn,
    VerificationOut,
)
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.vpic import VpicApi, get_vpic

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
    kind: str | None = Query(None, pattern="^(part|vehicle)$"),
    make_id: int | None = None,
    model_id: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    title_status: str | None = None,
    running: str | None = None,
    near_zip: str | None = Query(None, pattern=r"^\d{5}$"),
    radius_mi: int = Query(50, ge=1, le=500),
    sort: str = "newest",
    limit: int = Query(24, ge=1, le=service.PAGE_MAX),
    offset: int = Query(0, ge=0),
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    vehicle = db.get(Vehicle, vehicle_id) if vehicle_id else None
    if vehicle_id and vehicle is None:
        raise NotFound("vehicle_not_found")
    near = service.zip_point(db, near_zip)
    if near_zip and near is None:
        raise NotFound("zip_not_found")
    total, rows = service.search(
        db, q=q, category=category, condition=condition, vehicle=vehicle, state=state,
        min_price=min_price, max_price=max_price, sort=sort, limit=limit, offset=offset,
        seller_id=seller_id, kind=kind, make_id=make_id, model_id=model_id, year_min=year_min,
        year_max=year_max, title_status=title_status, running=running, near=near,
        radius_mi=radius_mi,
    )  # fmt: skip
    saved = service.saved_ids(db, user)
    miles = service.distances(db, near, rows)
    items = []
    for ls in rows:
        item = service.summary(db, ls, saved=saved)
        item.distance_mi = miles.get(ls.id)
        items.append(item)
    return {"total": total, "items": items}


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
    data: ListingIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    vpic: VpicApi = Depends(get_vpic),
):
    listing = service.save_listing(db, user, data, None, vpic)
    db.commit()
    return service.detail(db, listing, user)


@router.post(
    "/listings/bulk-vins",
    response_model=list[BulkVinResult],
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_bulk", 10, 3600))],
)
def bulk_vins(
    data: BulkVinIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    vpic: VpicApi = Depends(get_vpic),
):
    results = service.bulk_add_vehicles(db, user, data, vpic)
    db.commit()
    return results


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
    vpic: VpicApi = Depends(get_vpic),
):
    listing = db.get(Listing, listing_id)
    if listing is None or listing.seller.user_id != user.id:
        raise NotFound("listing_not_found")
    service.save_listing(db, user, data, listing, vpic)
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


# ---- reviews ----------------------------------------------------------------------


@router.get("/listings/{listing_id}/can-review")
def can_review(listing_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    listing = _listing(db, listing_id, user)
    done = db.scalar(
        select(Review.id).where(Review.listing_id == listing.id, Review.reviewer_id == user.id)
    )
    return {
        "can_review": not done and service.can_review(db, user, listing),
        "reviewed": bool(done),
    }


@router.post(
    "/listings/{listing_id}/review",
    response_model=ReviewOut,
    status_code=201,
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_review", 20, 86400))],
)
def review_seller(
    listing_id: int,
    data: ReviewIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    listing = _listing(db, listing_id, user)
    r = service.add_review(db, user, listing, data.rating, data.comment)
    db.commit()
    return _review_out(db, r)


def _review_out(db: Session, r: Review) -> ReviewOut:
    reviewer = db.get(User, r.reviewer_id)
    listing = db.get(Listing, r.listing_id)
    return ReviewOut(
        id=r.id, rating=r.rating, comment=r.comment,
        reviewer_name=reviewer.display_name if reviewer else "—",
        listing_title=listing.title if listing else "—", created_at=r.created_at,
    )  # fmt: skip


@router.get("/sellers/{seller_id}/reviews", response_model=list[ReviewOut])
def seller_reviews(seller_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Review)
        .where(Review.seller_id == seller_id, Review.hidden.is_(False))
        .order_by(Review.id.desc())
        .limit(100)
    )
    return [_review_out(db, r) for r in rows]


@router.post("/mod/reviews/{review_id}/hide", dependencies=[Depends(verify_csrf)])
def mod_hide_review(review_id: int, mod: User = Depends(moderator), db: Session = Depends(get_db)):
    r = db.get(Review, review_id)
    if r is None:
        raise NotFound("review_not_found")
    r.hidden = True
    log_action(db, mod, "review_hide", "market_review", r.id)
    db.commit()
    return {"status": "hidden"}


# ---- watch list ------------------------------------------------------------------


@router.post("/listings/{listing_id}/save", status_code=204, dependencies=[Depends(verify_csrf)])
def save_listing(
    listing_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    listing = _listing(db, listing_id, user)
    if not db.scalar(
        select(SavedListing.id).where(
            SavedListing.user_id == user.id, SavedListing.listing_id == listing.id
        )
    ):
        db.add(SavedListing(user_id=user.id, listing_id=listing.id))
        db.commit()


@router.delete("/listings/{listing_id}/save", status_code=204, dependencies=[Depends(verify_csrf)])
def unsave_listing(
    listing_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = db.scalar(
        select(SavedListing).where(
            SavedListing.user_id == user.id, SavedListing.listing_id == listing_id
        )
    )
    if row is not None:
        db.delete(row)
        db.commit()


@router.get("/saved")
def saved_listings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Listing)
        .join(SavedListing, SavedListing.listing_id == Listing.id)
        .where(SavedListing.user_id == user.id)
        .order_by(SavedListing.created_at.desc())
    ).all()
    ids = {ls.id for ls in rows}
    return [service.summary(db, ls, saved=ids) for ls in rows if service.can_view(ls, user)]


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
