"""Parts marketplace: sellers, listings (new and used) with vehicle fitment, photos,
buyer-seller messages, reports and seller verification.

Design: docs/COMMERCE_DESIGN.md §4. Off by default (ENABLE_MARKETPLACE). No payments yet —
buyers and sellers arrange payment and pickup/shipping themselves; card data will only ever
be handled by a payment provider. Minimal personal data: city/state/ZIP, never a street
address; seller verification stores license numbers only (no document uploads).
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin, utcnow
from app.modules.vehicles.fitment import FitmentMixin


def _enum(e):
    return Enum(e, native_enum=False, length=20)


class SellerType(enum.StrEnum):
    individual = "individual"
    shop = "shop"  # repair shop
    recycler = "recycler"  # salvage yard / auto recycler / dismantler
    retailer = "retailer"  # parts store


class SellerStatus(enum.StrEnum):
    active = "active"
    suspended = "suspended"


class Condition(enum.StrEnum):
    new = "new"
    used = "used"
    reman = "reman"  # remanufactured / rebuilt
    for_parts = "for_parts"  # not working, for parts or repair


class ListingStatus(enum.StrEnum):
    pending = "pending"  # waiting for moderator review (new sellers' first listings)
    active = "active"
    sold = "sold"
    withdrawn = "withdrawn"  # seller took it down
    removed = "removed"  # moderator took it down


class Shipping(enum.StrEnum):
    pickup = "pickup"
    ships = "ships"
    pickup_or_ships = "pickup_or_ships"


class VerificationKind(enum.StrEnum):
    business_license = "business_license"
    dismantler_license = "dismantler_license"  # auto recycler / salvage dealer license
    dealer_license = "dealer_license"  # motor vehicle dealer license


class ListingKind(enum.StrEnum):
    part = "part"
    vehicle = "vehicle"  # a whole vehicle, any condition


class TitleStatus(enum.StrEnum):
    clean = "clean"
    rebuilt = "rebuilt"  # rebuilt / reconstructed (was salvage, repaired, inspected)
    salvage = "salvage"
    non_repairable = "non_repairable"  # junk / parts-only certificate


class Running(enum.StrEnum):
    runs_drives = "runs_drives"
    runs_not_drives = "runs_not_drives"
    not_running = "not_running"


class VerificationStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ListingReportReason(enum.StrEnum):
    stolen = "stolen"
    prohibited = "prohibited"
    scam = "scam"
    counterfeit = "counterfeit"
    wrong_fitment = "wrong_fitment"
    other = "other"


class Seller(TimestampMixin, Base):
    __tablename__ = "market_sellers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    seller_type: Mapped[SellerType] = mapped_column(_enum(SellerType))
    display_name: Mapped[str] = mapped_column(String(60))
    city: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(2), index=True)  # US state / DC code
    postal_code: Mapped[str | None] = mapped_column(String(10))
    about: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SellerStatus] = mapped_column(_enum(SellerStatus), default=SellerStatus.active)

    user = relationship("User")


class SellerVerification(Base):
    """A seller's license, checked by a moderator against the issuing state's public lookup.
    Only the license number and state are stored — no document images."""

    __tablename__ = "market_seller_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("market_sellers.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[VerificationKind] = mapped_column(_enum(VerificationKind))
    license_number: Mapped[str] = mapped_column(String(60))
    issuing_state: Mapped[str] = mapped_column(String(2))
    business_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus), default=VerificationStatus.pending
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Listing(TimestampMixin, Base):
    __tablename__ = "market_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("market_sellers.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    kind: Mapped[ListingKind] = mapped_column(
        _enum(ListingKind), default=ListingKind.part, index=True
    )
    category: Mapped[str] = mapped_column(String(30), index=True)  # "vehicle" for whole vehicles
    condition: Mapped[Condition] = mapped_column(_enum(Condition))
    brand: Mapped[str | None] = mapped_column(String(60))
    part_number: Mapped[str | None] = mapped_column(String(60), index=True)
    price_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    shipping: Mapped[Shipping] = mapped_column(_enum(Shipping))
    shipping_note: Mapped[str | None] = mapped_column(String(300))
    # Used parts: where they came from (helps fitment and fights theft).
    source_vin: Mapped[str | None] = mapped_column(String(17))
    mileage: Mapped[int | None] = mapped_column(Integer)
    # Emissions parts (catalytic converters): legal status.
    emissions_compliance: Mapped[str | None] = mapped_column(String(20))  # epa | carb
    carb_eo_number: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[ListingStatus] = mapped_column(_enum(ListingStatus), index=True)
    status_reason: Mapped[str | None] = mapped_column(String(500))
    rules_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    search_text: Mapped[str] = mapped_column(Text, default="")

    seller: Mapped[Seller] = relationship()
    fitment: Mapped[list["ListingFitment"]] = relationship(
        cascade="all, delete-orphan", order_by="ListingFitment.id"
    )
    photos: Mapped[list["ListingPhoto"]] = relationship(
        cascade="all, delete-orphan", order_by="ListingPhoto.position"
    )
    vehicle: Mapped["VehicleDetails | None"] = relationship(
        cascade="all, delete-orphan", uselist=False
    )


class VehicleDetails(Base):
    """Extra facts for a whole-vehicle listing."""

    __tablename__ = "market_vehicle_details"

    listing_id: Mapped[int] = mapped_column(
        ForeignKey("market_listings.id", ondelete="CASCADE"), primary_key=True
    )
    year: Mapped[int] = mapped_column(Integer, index=True)
    make_id: Mapped[int] = mapped_column(ForeignKey("makes.id"), index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id"), index=True)
    # Our vehicle record (year + model + engine) when known — links to repair info and recalls.
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"))
    vin: Mapped[str | None] = mapped_column(String(17), index=True)
    odometer: Mapped[int | None] = mapped_column(Integer)
    odometer_unit: Mapped[str] = mapped_column(String(2), default="mi")
    title_status: Mapped[TitleStatus] = mapped_column(_enum(TitleStatus))
    has_lien: Mapped[bool] = mapped_column(Boolean, default=False)
    running: Mapped[Running] = mapped_column(_enum(Running))
    trim: Mapped[str | None] = mapped_column(String(60))
    drive: Mapped[str | None] = mapped_column(String(40))
    transmission: Mapped[str | None] = mapped_column(String(40))
    exterior_color: Mapped[str | None] = mapped_column(String(40))


class SavedListing(Base):
    """A buyer's watch list."""

    __tablename__ = "market_saved"
    __table_args__ = (UniqueConstraint("user_id", "listing_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("market_listings.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ListingFitment(FitmentMixin, Base):
    __tablename__ = "market_listing_fitment"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("market_listings.id", ondelete="CASCADE"), index=True
    )


class ListingPhoto(Base):
    __tablename__ = "market_listing_photos"
    __table_args__ = (UniqueConstraint("listing_id", "photo_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("market_listings.id", ondelete="CASCADE"), index=True
    )
    photo_id: Mapped[int] = mapped_column(ForeignKey("photos.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0)


class ListingReport(Base):
    __tablename__ = "market_listing_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("market_listings.id", ondelete="CASCADE"), index=True
    )
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[ListingReportReason] = mapped_column(_enum(ListingReportReason))
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|resolved|dismissed
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Conversation(TimestampMixin, Base):
    """One buyer asking one seller about one listing."""

    __tablename__ = "market_conversations"
    __table_args__ = (UniqueConstraint("listing_id", "buyer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("market_listings.id", ondelete="CASCADE"), index=True
    )
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    listing: Mapped[Listing] = relationship()
    buyer = relationship("User")
    messages: Mapped[list["Message"]] = relationship(
        cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "market_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("market_conversations.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
