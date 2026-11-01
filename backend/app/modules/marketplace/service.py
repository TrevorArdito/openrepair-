from datetime import UTC, datetime

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFound
from app.modules.accounts.models import Role, User, UserStatus
from app.modules.community.models import Photo
from app.modules.community.service import ensure_can_contribute
from app.modules.marketplace import rules
from app.modules.marketplace.models import (
    Conversation,
    Listing,
    ListingFitment,
    ListingPhoto,
    ListingStatus,
    Message,
    Seller,
    SellerStatus,
    SellerVerification,
    VerificationStatus,
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
from app.modules.vehicles.fitment import fitment_display, fits, validate_fitment
from app.modules.vehicles.models import Vehicle

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


def seller_out(db: Session, seller: Seller, private: bool = False) -> SellerOut:
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
    )


# ---- listings --------------------------------------------------------------------


def _search_text(listing: Listing) -> str:
    parts = [listing.title, listing.description, listing.brand, listing.part_number]
    if listing.part_number:  # "BR-900 1234" also findable as "br9001234"
        parts.append("".join(c for c in listing.part_number if c.isalnum()))
    return " ".join(p for p in parts if p).lower()


def save_listing(db: Session, user: User, data: ListingIn, listing: Listing | None) -> Listing:
    ensure_can_contribute(user)
    seller = require_seller(db, user)
    if not data.accept_rules:
        raise AppError("listing_rules_not_accepted", 422)
    if listing is not None and listing.status == ListingStatus.removed:
        raise AppError("listing_removed", 403)
    rules.check_listing(
        category=data.category,
        condition=data.condition,
        text=" ".join(filter(None, [data.title, data.description, data.part_number])),
        emissions_compliance=data.emissions_compliance,
        carb_eo_number=data.carb_eo_number,
        seller_verified=bool(verified_kinds(db, seller)),
    )
    validate_fitment(db, data.fitment, "listing_invalid")
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

    fields = data.model_dump(exclude={"fitment", "photo_ids", "accept_rules"})
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
    listing.fitment = [ListingFitment(**f.model_dump()) for f in data.fitment]
    listing.photos = [ListingPhoto(photo_id=p.id, position=i) for i, p in enumerate(photos)]
    listing.search_text = _search_text(listing)
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


def summary(db: Session, listing: Listing, verified: bool | None = None) -> ListingSummary:
    seller = listing.seller
    if verified is None:
        verified = bool(verified_kinds(db, seller))
    return ListingSummary(
        id=listing.id,
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
        fits_all=not listing.fitment,
        created_at=listing.created_at,
    )


def detail(db: Session, listing: Listing, viewer: User | None) -> ListingOut:
    base = summary(db, listing).model_dump()
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
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
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
    msg = Message(conversation_id=conv.id, sender_id=user.id, body=body)
    db.add(msg)
    conv.updated_at = datetime.now(UTC)
    db.flush()
    return msg


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
