import logging
import math
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.email import send_email
from app.core.errors import AppError, NotFound
from app.modules.accounts.models import Role, User, UserStatus
from app.modules.community.models import Photo
from app.modules.community.service import ensure_can_contribute
from app.modules.marketplace import rules, zips
from app.modules.marketplace.models import (
    Conversation,
    Listing,
    ListingFitment,
    ListingKind,
    ListingPhoto,
    ListingStatus,
    Message,
    Review,
    SavedListing,
    Seller,
    SellerStatus,
    SellerVerification,
    VehicleDetails,
    VerificationStatus,
    ZipPoint,
)
from app.modules.marketplace.schemas import (
    ConversationOut,
    ListingIn,
    ListingOut,
    ListingSummary,
    MessageOut,
    SellerIn,
    SellerOut,
)
from app.modules.search.service import words
from app.modules.vehicles import service as vehicles_service
from app.modules.vehicles.fitment import fitment_display, fits, validate_fitment
from app.modules.vehicles.models import Make, Model, Vehicle
from app.modules.vehicles.vin import check_digit_valid

MILES_PER_DEG_LAT = zips.MILES_PER_DEG_LAT

log = logging.getLogger(__name__)
# Private sellers selling many vehicles may need a dealer license in their state
# ("curbstoning" laws), so more than this many active vehicle listings needs a verified license.
PRIVATE_VEHICLE_LIMIT = 5
VIN_REQUIRED_FROM = 1981  # 17-character VINs became standard for the 1981 model year
OPEN = (ListingStatus.active, ListingStatus.pending)

PAGE_MAX = 50


# ---- sellers ---------------------------------------------------------------------


def seller_for(db: Session, user: User) -> Seller | None:
    return db.scalar(select(Seller).where(Seller.user_id == user.id))


def require_seller(db: Session, user: User) -> Seller:
    seller = seller_for(db, user)
    if seller is None:
        raise AppError("seller_profile_required", 409)
    if seller.status != SellerStatus.active:
        raise AppError("seller_suspended", 403)
    return seller


def verified_kinds(db: Session, seller: Seller) -> list:
    return sorted(
        set(
            db.scalars(
                select(SellerVerification.kind).where(
                    SellerVerification.seller_id == seller.id,
                    SellerVerification.status == VerificationStatus.approved,
                )
            )
        )
    )


def save_seller(db: Session, user: User, data: SellerIn) -> Seller:
    ensure_can_contribute(user)
    seller = seller_for(db, user)
    if seller is None:
        seller = Seller(user_id=user.id, **data.model_dump())
        db.add(seller)
    else:
        for k, v in data.model_dump().items():
            setattr(seller, k, v)
    db.flush()
    return seller


def rating(db: Session, seller: Seller) -> tuple[float | None, int]:
    avg, count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.seller_id == seller.id, Review.hidden.is_(False)
        )
    ).one()
    return (round(float(avg), 1) if avg is not None else None), count or 0


def seller_out(db: Session, seller: Seller, private: bool = False) -> SellerOut:
    avg, count = rating(db, seller)
    active = db.scalar(
        select(func.count())
        .select_from(Listing)
        .where(Listing.seller_id == seller.id, Listing.status == ListingStatus.active)
    )
    return SellerOut(
        id=seller.id,
        seller_type=seller.seller_type,
        display_name=seller.display_name,
        city=seller.city,
        state=seller.state,
        postal_code=seller.postal_code if private else None,
        about=seller.about,
        status=seller.status.value,
        verified=verified_kinds(db, seller),
        member_since=seller.created_at,
        active_listings=active or 0,
        rating=avg,
        rating_count=count,
    )


# ---- listings --------------------------------------------------------------------


def _search_text(db: Session, listing: Listing) -> str:
    parts = [listing.title, listing.description, listing.brand, listing.part_number]
    if (vd := listing.vehicle) is not None:
        make, model = db.get(Make, vd.make_id), db.get(Model, vd.model_id) if vd.model_id else None
        parts += [str(vd.year), make.name if make else None, model.name if model else None]
        parts += [vd.trim, vd.vin]
    if listing.part_number:  # "BR-900 1234" also findable as "br9001234"
        parts.append("".join(c for c in listing.part_number if c.isalnum()))
    return " ".join(p for p in parts if p).lower()


def _vehicle_fields(
    db: Session, vpic, seller: Seller, data: ListingIn, listing: Listing | None, verified: bool
) -> dict:
    v = data.vehicle
    if v is None:
        raise AppError("listing_vehicle_details_required", 422)
    fields = v.model_dump()
    fields["vehicle_id"] = None
    if v.year >= VIN_REQUIRED_FROM and not v.vin:
        raise AppError("listing_vin_required", 422)
    if v.vin:
        if not check_digit_valid(v.vin):
            raise AppError("listing_vin_invalid", 422)
        if vpic is not None:
            try:  # the VIN is the truth: year/make/model come from NHTSA's decoder
                dec = vehicles_service.decode_vin(db, vpic, v.vin).vehicle
                fields.update(
                    year=dec.year, make_id=dec.make.id, model_id=dec.model.id, vehicle_id=dec.id
                )
            except AppError:
                pass  # NHTSA down or VIN unknown: keep what the seller picked
        dup = db.scalar(
            select(Listing.id)
            .join(VehicleDetails, VehicleDetails.listing_id == Listing.id)
            .where(
                VehicleDetails.vin == v.vin,
                Listing.status.in_(OPEN),
                Listing.id != (listing.id if listing else -1),
            )
        )
        if dup:
            raise AppError("listing_vin_duplicate", 409)
    one = SimpleNamespace(
        make_id=fields["make_id"], model_id=fields["model_id"], year_from=fields["year"],
        year_to=fields["year"], engine_family_id=None,
    )  # fmt: skip
    validate_fitment(db, [one], "listing_invalid")
    if not verified:
        open_vehicles = db.scalar(
            select(func.count())
            .select_from(Listing)
            .where(
                Listing.seller_id == seller.id,
                Listing.kind == ListingKind.vehicle,
                Listing.status.in_(OPEN),
                Listing.id != (listing.id if listing else -1),
            )
        )
        if (open_vehicles or 0) >= PRIVATE_VEHICLE_LIMIT:
            raise AppError("listing_vehicle_limit", 403, limit=PRIVATE_VEHICLE_LIMIT)
    return fields


def save_listing(
    db: Session, user: User, data: ListingIn, listing: Listing | None, vpic=None
) -> Listing:
    ensure_can_contribute(user)
    seller = require_seller(db, user)
    if not data.accept_rules:
        raise AppError("listing_rules_not_accepted", 422)
    if listing is not None and listing.status == ListingStatus.removed:
        raise AppError("listing_removed", 403)
    from app.modules.marketplace.orders import ensure_inform_ok

    ensure_inform_ok(db, seller)  # INFORM Consumers Act: high-volume sellers must be verified
    verified = bool(verified_kinds(db, seller))
    is_vehicle = data.category == "vehicle"
    vfields = _vehicle_fields(db, vpic, seller, data, listing, verified) if is_vehicle else None
    if not is_vehicle and data.vehicle is not None:
        raise AppError("listing_invalid", 422, fields=[{"loc": ["vehicle"]}])
    rules.check_listing(
        category=data.category,
        condition=data.condition,
        text=" ".join(filter(None, [data.title, data.description, data.part_number])),
        emissions_compliance=data.emissions_compliance,
        carb_eo_number=data.carb_eo_number,
        seller_verified=verified,
    )
    fitment = [] if is_vehicle else data.fitment  # a whole vehicle *is* its fitment
    validate_fitment(db, fitment, "listing_invalid")
    photos = []
    for pid in dict.fromkeys(data.photo_ids):
        photo = db.get(Photo, pid)
        if (
            photo is None
            or photo.uploader_id != user.id
            or photo.entry_id is not None
            or photo.status != "visible"
        ):
            raise NotFound("photo_not_found")
        photos.append(photo)

    fields = data.model_dump(exclude={"fitment", "photo_ids", "accept_rules", "vehicle"})
    fields["kind"] = ListingKind.vehicle if is_vehicle else ListingKind.part
    if fields["emissions_compliance"] != "carb":
        fields["carb_eo_number"] = None
    if listing is None:
        listing = Listing(seller_id=seller.id, **fields)
        db.add(listing)
    else:
        for k, v in fields.items():
            setattr(listing, k, v)
    listing.rules_accepted_at = datetime.now(UTC)
    # New sellers' listings (and their edits) wait for a moderator first.
    trusted = user.status == UserStatus.active or user.has_role(Role.pro)
    if not trusted and listing.status != ListingStatus.sold:
        listing.status = ListingStatus.pending
    elif listing.status in (None, ListingStatus.pending):
        listing.status = ListingStatus.active
    listing.status_reason = None
    listing.fitment = [ListingFitment(**f.model_dump()) for f in fitment]
    listing.photos = [ListingPhoto(photo_id=p.id, position=i) for i, p in enumerate(photos)]
    if vfields is None:
        listing.vehicle = None
    elif listing.vehicle is None:
        listing.vehicle = VehicleDetails(**vfields)
    else:
        for k, v in vfields.items():
            setattr(listing.vehicle, k, v)
    listing.search_text = _search_text(db, listing)
    db.flush()
    return listing


def set_status(db: Session, user: User, listing: Listing, status: str) -> None:
    if listing.seller.user_id != user.id:
        raise AppError("forbidden", 403)
    if listing.status in (ListingStatus.removed, ListingStatus.pending):
        raise AppError("listing_status_locked", 409)
    listing.status = ListingStatus(status)
    db.flush()


def _photo_url(photo_id: int) -> str:
    return f"/api/v1/photos/{photo_id}"


def _vehicle_dict(db: Session, vd: VehicleDetails, full: bool) -> dict:
    make, model = db.get(Make, vd.make_id), db.get(Model, vd.model_id) if vd.model_id else None
    out = {
        "year": vd.year,
        "make": make.name if make else "?",
        "model": model.name if model else None,
        "trim": vd.trim,
        "odometer": vd.odometer,
        "odometer_unit": vd.odometer_unit,
        "title_status": vd.title_status.value,
        "has_lien": vd.has_lien,
        "running": vd.running.value,
        "vehicle_id": vd.vehicle_id,
        "stock_number": vd.stock_number,
        "arrived_on": vd.arrived_on.isoformat() if vd.arrived_on else None,
        "has_keys": vd.has_keys,
        "damage": vd.damage,
        "lien_sale_after": vd.lien_sale_after.isoformat() if vd.lien_sale_after else None,
    }
    if full:
        out.update(
            vin=vd.vin, make_id=vd.make_id, model_id=vd.model_id, drive=vd.drive,
            transmission=vd.transmission, exterior_color=vd.exterior_color,
        )  # fmt: skip
    return out


def saved_ids(db: Session, user: User | None) -> set[int]:
    if user is None:
        return set()
    return set(db.scalars(select(SavedListing.listing_id).where(SavedListing.user_id == user.id)))


def summary(
    db: Session,
    listing: Listing,
    verified: bool | None = None,
    saved: set[int] | None = None,
    full: bool = False,
) -> ListingSummary:
    seller = listing.seller
    if verified is None:
        verified = bool(verified_kinds(db, seller))
    return ListingSummary(
        id=listing.id,
        kind=listing.kind,
        title=listing.title,
        category=listing.category,
        condition=listing.condition,
        price_cents=listing.price_cents,
        currency=listing.currency,
        status=listing.status,
        city=seller.city,
        state=seller.state,
        seller_id=seller.id,
        seller_name=seller.display_name,
        seller_verified=verified,
        photo_url=_photo_url(listing.photos[0].photo_id) if listing.photos else None,
        fits_all=not listing.fitment and listing.kind == ListingKind.part,
        vehicle=_vehicle_dict(db, listing.vehicle, full) if listing.vehicle else None,
        saved=listing.id in (saved or ()),
        buy_now=_buy_now_reason(listing) is None,
        created_at=listing.created_at,
    )


def detail(db: Session, listing: Listing, viewer: User | None) -> ListingOut:
    base = summary(db, listing, saved=saved_ids(db, viewer), full=True).model_dump()
    fit = [
        fitment_display(
            db,
            {
                "make_id": f.make_id,
                "model_id": f.model_id,
                "year_from": f.year_from,
                "year_to": f.year_to,
                "displacement_l": f.displacement_l,
                "engine_family_id": f.engine_family_id,
            },
        )
        for f in listing.fitment
    ]
    return ListingOut(
        **base,
        description=listing.description,
        brand=listing.brand,
        part_number=listing.part_number,
        quantity=listing.quantity,
        shipping=listing.shipping,
        shipping_note=listing.shipping_note,
        shipping_cents=listing.shipping_cents,
        buy_now_reason=_buy_now_reason(listing),
        source_vin=listing.source_vin,
        mileage=listing.mileage,
        emissions_compliance=listing.emissions_compliance,
        carb_eo_number=listing.carb_eo_number,
        status_reason=listing.status_reason,
        fitment=fit,
        photos=[{"id": p.photo_id, "url": _photo_url(p.photo_id)} for p in listing.photos],
        is_owner=viewer is not None and listing.seller.user_id == viewer.id,
        updated_at=listing.updated_at,
    )


def can_view(listing: Listing, viewer: User | None) -> bool:
    if listing.status in (ListingStatus.active, ListingStatus.sold):
        return listing.seller.status == SellerStatus.active or _is_mod(viewer)
    return viewer is not None and (listing.seller.user_id == viewer.id or _is_mod(viewer))


def _is_mod(user: User | None) -> bool:
    return user is not None and user.has_role(Role.moderator)


def search(
    db: Session,
    *,
    q: str | None,
    category: str | None,
    condition: str | None,
    vehicle: Vehicle | None,
    state: str | None,
    min_price: int | None,
    max_price: int | None,
    sort: str,
    limit: int,
    offset: int,
    seller_id: int | None = None,
    kind: str | None = None,
    make_id: int | None = None,
    model_id: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    title_status: str | None = None,
    running: str | None = None,
    near: ZipPoint | None = None,
    radius_mi: int = 50,
) -> tuple[int, list[Listing]]:
    stmt = (
        select(Listing)
        .join(Seller, Seller.id == Listing.seller_id)
        .where(Listing.status == ListingStatus.active, Seller.status == SellerStatus.active)
    )
    if q and (ws := words(q)):
        stmt = stmt.where(and_(*[Listing.search_text.like(f"%{w}%") for w in ws]))
    if seller_id is not None:
        stmt = stmt.where(Listing.seller_id == seller_id)
    if kind:
        stmt = stmt.where(Listing.kind == kind)
    vfilters = [
        (make_id, lambda x: VehicleDetails.make_id == x),
        (model_id, lambda x: VehicleDetails.model_id == x),
        (year_min, lambda x: VehicleDetails.year >= x),
        (year_max, lambda x: VehicleDetails.year <= x),
        (title_status, lambda x: VehicleDetails.title_status == x),
        (running, lambda x: VehicleDetails.running == x),
    ]
    if any(v is not None for v, _ in vfilters):
        stmt = stmt.join(VehicleDetails, VehicleDetails.listing_id == Listing.id)
        stmt = stmt.where(*[cond(v) for v, cond in vfilters if v is not None])
    if category:
        stmt = stmt.where(Listing.category == category)
    if condition:
        stmt = stmt.where(Listing.condition == condition)
    if state:
        stmt = stmt.where(Seller.state == state.upper())
    if min_price is not None:
        stmt = stmt.where(Listing.price_cents >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.price_cents <= max_price)
    if vehicle is not None:  # fits this vehicle, or a universal part
        has_fit = exists().where(ListingFitment.listing_id == Listing.id)
        fit_ok = exists().where(
            ListingFitment.listing_id == Listing.id, fits(ListingFitment, vehicle)
        )
        stmt = stmt.where(or_(fit_ok, ~has_fit))
    dist2 = None
    if near is not None:  # flat-earth distance is accurate enough within a few hundred miles
        kx = MILES_PER_DEG_LAT * math.cos(math.radians(near.lat))
        dy = (ZipPoint.lat - near.lat) * MILES_PER_DEG_LAT
        dx = (ZipPoint.lon - near.lon) * kx
        dist2 = dy * dy + dx * dx
        span = radius_mi / MILES_PER_DEG_LAT
        stmt = stmt.join(ZipPoint, ZipPoint.zip == Seller.postal_code).where(
            ZipPoint.lat.between(near.lat - span, near.lat + span), dist2 <= radius_mi * radius_mi
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if sort == "nearest" and dist2 is not None:
        rows = db.scalars(
            stmt.order_by(dist2, Listing.id.desc()).limit(min(limit, PAGE_MAX)).offset(offset)
        ).all()
        return total, list(rows)
    order = {
        "price_low": (Listing.price_cents.asc(), Listing.id.desc()),
        "price_high": (Listing.price_cents.desc(), Listing.id.desc()),
    }.get(sort, (Listing.created_at.desc(), Listing.id.desc()))
    rows = db.scalars(stmt.order_by(*order).limit(min(limit, PAGE_MAX)).offset(offset)).all()
    return total, list(rows)


# ---- messages --------------------------------------------------------------------


def start_or_continue(db: Session, user: User, listing: Listing, body: str) -> Conversation:
    ensure_can_contribute(user)
    if listing.seller.user_id == user.id:
        raise AppError("cannot_message_self", 409)
    conv = db.scalar(
        select(Conversation).where(
            Conversation.listing_id == listing.id, Conversation.buyer_id == user.id
        )
    )
    if conv is None:
        if listing.status != ListingStatus.active:
            raise AppError("listing_not_available", 409)
        conv = Conversation(listing_id=listing.id, buyer_id=user.id)
        db.add(conv)
        db.flush()
    add_message(db, user, conv, body)
    return conv


def participant_role(conv: Conversation, user: User) -> str | None:
    if conv.buyer_id == user.id:
        return "buyer"
    if conv.listing.seller.user_id == user.id:
        return "seller"
    return None


def add_message(db: Session, user: User, conv: Conversation, body: str) -> Message:
    ensure_can_contribute(user)
    if participant_role(conv, user) is None:
        raise NotFound("conversation_not_found")
    if conv.listing.status == ListingStatus.removed:
        raise AppError("listing_not_available", 409)
    already_waiting = any(m.sender_id == user.id and not m.read for m in conv.messages)
    msg = Message(conversation_id=conv.id, sender_id=user.id, body=body)
    db.add(msg)
    conv.updated_at = datetime.now(UTC)
    db.flush()
    if not already_waiting:  # one email per batch of unread messages, not one per message
        _notify(conv, user)
    return msg


def _notify(conv: Conversation, sender: User) -> None:
    """Email the other person a link (never the message text or anyone's email address)."""
    recipient = conv.listing.seller.user if conv.buyer_id == sender.id else conv.buyer
    link = f"{get_settings().public_base_url}/market/messages/{conv.id}"
    try:
        send_email(
            recipient.email,
            f'New message about "{conv.listing.title}"',
            f"Hi {recipient.display_name},\n\n{sender.display_name} sent you a message about "
            f'"{conv.listing.title}" on ChrystalClear.\n\nRead and reply here:\n{link}\n',
        )
    except Exception:  # noqa: BLE001 - a mail outage must never block messaging
        log.exception("message notification email failed")


def conversation_out(
    db: Session, conv: Conversation, user: User, with_messages: bool = False
) -> ConversationOut:
    role = participant_role(conv, user)
    other = conv.listing.seller.display_name if role == "buyer" else conv.buyer.display_name
    msgs = conv.messages
    unread = sum(1 for m in msgs if not m.read and m.sender_id != user.id)
    return ConversationOut(
        id=conv.id,
        listing_id=conv.listing_id,
        listing_title=conv.listing.title,
        other_name=other,
        role=role,
        unread=unread,
        last_message=msgs[-1].body[:140] if msgs else None,
        updated_at=conv.updated_at,
        messages=[
            MessageOut(id=m.id, mine=m.sender_id == user.id, body=m.body, created_at=m.created_at)
            for m in msgs
        ]
        if with_messages
        else None,
    )


def my_conversations(db: Session, user: User) -> list[Conversation]:
    seller = seller_for(db, user)
    cond = Conversation.buyer_id == user.id
    if seller is not None:
        cond = or_(cond, Listing.seller_id == seller.id)
    return list(
        db.scalars(
            select(Conversation)
            .join(Listing, Listing.id == Conversation.listing_id)
            .where(cond)
            .order_by(Conversation.updated_at.desc())
            .limit(200)
        )
    )


# ---- privacy: "download my data" -------------------------------------------------


def export_for(db: Session, user: User) -> dict:
    seller = seller_for(db, user)
    out: dict = {"marketplace": {"seller": None, "listings": [], "messages_sent": []}}
    if seller is not None:
        out["marketplace"]["seller"] = seller_out(db, seller, private=True).model_dump(mode="json")
        out["marketplace"]["listings"] = [
            detail(db, ls, user).model_dump(mode="json")
            for ls in db.scalars(select(Listing).where(Listing.seller_id == seller.id))
        ]
    out["marketplace"]["messages_sent"] = [
        {
            "conversation_id": m.conversation_id,
            "body": m.body,
            "created_at": m.created_at.isoformat(),
        }
        for m in db.scalars(select(Message).where(Message.sender_id == user.id))
    ]
    return out


# ---- distance -------------------------------------------------------------------


def zip_point(db: Session, code: str | None) -> ZipPoint | None:
    return db.get(ZipPoint, code) if code else None


def distances(db: Session, near: ZipPoint | None, listings: list[Listing]) -> dict[int, int]:
    """Whole miles from `near` to each listing's seller (when the seller gave a ZIP)."""
    if near is None:
        return {}
    out = {}
    for ls in listings:
        p = zip_point(db, ls.seller.postal_code)
        if p is not None:
            out[ls.id] = round(zips.miles(near, p))
    return out


# ---- reviews ----------------------------------------------------------------------


def can_review(db: Session, user: User, listing: Listing) -> bool:
    """Only someone who talked with the seller about this listing (and got a reply) can
    review, once it's sold. With payments later: only the actual buyer."""
    if listing.status != ListingStatus.sold or listing.seller.user_id == user.id:
        return False
    conv = db.scalar(
        select(Conversation).where(
            Conversation.listing_id == listing.id, Conversation.buyer_id == user.id
        )
    )
    seller_user = listing.seller.user_id
    return conv is not None and any(m.sender_id == seller_user for m in conv.messages)


def add_review(
    db: Session, user: User, listing: Listing, stars: int, comment: str | None
) -> Review:
    ensure_can_contribute(user)
    if not can_review(db, user, listing):
        raise AppError("review_not_allowed", 403)
    if db.scalar(
        select(Review.id).where(Review.listing_id == listing.id, Review.reviewer_id == user.id)
    ):
        raise AppError("review_exists", 409)
    review = Review(
        seller_id=listing.seller_id, listing_id=listing.id, reviewer_id=user.id,
        rating=stars, comment=comment,
    )  # fmt: skip
    db.add(review)
    db.flush()
    return review


def _buy_now_reason(listing: Listing) -> str | None:
    from app.modules.marketplace.orders import buy_now_reason

    return buy_now_reason(listing)
