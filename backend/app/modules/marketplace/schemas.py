from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.community.schemas import AppliesTo
from app.modules.marketplace.models import (
    Condition,
    ListingKind,
    ListingReportReason,
    ListingStatus,
    Running,
    SellerType,
    Shipping,
    TitleStatus,
    VerificationKind,
)

US_STATES = set(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR".split()
)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _state(v: str) -> str:
    v = v.upper()
    if v not in US_STATES:
        raise ValueError("unknown state")
    return v


class SellerIn(Strict):
    seller_type: SellerType
    display_name: Annotated[str, Field(min_length=2, max_length=60)]
    city: Annotated[str, Field(min_length=1, max_length=60)]
    state: str
    postal_code: Annotated[str, Field(pattern=r"^\d{5}$")] | None = None
    about: Annotated[str, Field(max_length=2000)] | None = None

    _st = field_validator("state")(_state)


class SellerOut(BaseModel):
    id: int
    seller_type: SellerType
    display_name: str
    city: str
    state: str
    postal_code: str | None = None  # only shown to the seller themselves
    about: str | None
    status: str
    verified: list[VerificationKind]
    member_since: datetime
    active_listings: int
    rating: float | None = None  # average stars (1-5) from buyers
    rating_count: int = 0


class VerificationIn(Strict):
    kind: VerificationKind
    license_number: Annotated[str, Field(min_length=3, max_length=60)]
    issuing_state: str
    business_name: Annotated[str, Field(min_length=2, max_length=120)]

    _st = field_validator("issuing_state")(_state)


class VerificationOut(BaseModel):
    id: int
    kind: VerificationKind
    license_number: str
    issuing_state: str
    business_name: str
    status: str
    note: str | None
    created_at: datetime


Opt40 = Annotated[str, Field(max_length=40)] | None


class VehicleDetailsIn(Strict):
    """Whole-vehicle facts. With a VIN, year/make/model come from decoding the VIN."""

    vin: Annotated[str, Field(pattern=r"^[A-HJ-NPR-Z0-9]{17}$")] | None = None
    year: Annotated[int, Field(ge=1900, le=2100)]
    make_id: int
    model_id: int | None = None
    odometer: Annotated[int, Field(ge=0, le=3_000_000)] | None = None
    odometer_unit: Literal["mi", "km"] = "mi"
    title_status: TitleStatus
    has_lien: bool = False
    running: Running
    trim: Annotated[str, Field(max_length=60)] | None = None
    drive: Opt40 = None
    transmission: Opt40 = None
    exterior_color: Opt40 = None
    stock_number: Annotated[str, Field(max_length=30)] | None = None
    arrived_on: date | None = None
    has_keys: bool | None = None
    damage: Annotated[str, Field(max_length=60)] | None = None
    lien_sale_after: date | None = None

    @field_validator("vin", mode="before")
    @classmethod
    def _vin(cls, v):
        return v.strip().upper() or None if isinstance(v, str) else v


class ListingIn(Strict):
    title: Annotated[str, Field(min_length=5, max_length=120)]
    description: Annotated[str, Field(min_length=10, max_length=5000)]
    category: str
    condition: Condition
    brand: Annotated[str, Field(max_length=60)] | None = None
    part_number: Annotated[str, Field(max_length=60)] | None = None
    price_cents: Annotated[int, Field(ge=0, le=10_000_000)]
    quantity: Annotated[int, Field(ge=1, le=999)] = 1
    shipping: Shipping
    shipping_note: Annotated[str, Field(max_length=300)] | None = None
    shipping_cents: Annotated[int, Field(ge=0, le=1_000_000)] | None = None  # for Buy now
    source_vin: Annotated[str, Field(pattern=r"^[A-HJ-NPR-Z0-9]{17}$")] | None = None
    mileage: Annotated[int, Field(ge=0, le=2_000_000)] | None = None
    emissions_compliance: Literal["epa", "carb"] | None = None
    carb_eo_number: Annotated[str, Field(max_length=30)] | None = None
    fitment: Annotated[list[AppliesTo], Field(max_length=30)] = []  # empty = universal
    photo_ids: Annotated[list[int], Field(max_length=20)] = []
    vehicle: VehicleDetailsIn | None = None  # required when category == "vehicle"
    accept_rules: bool  # must be true: not stolen, not counterfeit, no open recall, legal

    @field_validator("source_vin", mode="before")
    @classmethod
    def _vin(cls, v):
        return v.strip().upper() or None if isinstance(v, str) else v


class BulkVinLine(Strict):
    vin: Annotated[str, Field(min_length=11, max_length=20)]
    price_cents: Annotated[int, Field(ge=0, le=10_000_000)] | None = None  # none = hidden draft
    stock_number: Annotated[str, Field(max_length=30)] | None = None


class BulkVinIn(Strict):
    """Yards: add many vehicles at once from a pasted VIN list."""

    lines: Annotated[list[BulkVinLine], Field(min_length=1, max_length=25)]
    title_status: TitleStatus
    running: Running
    accept_rules: bool


class BulkVinResult(BaseModel):
    vin: str
    listing_id: int | None = None
    title: str | None = None
    published: bool = False
    error: str | None = None  # stable error code when this VIN couldn't be added


class ListingSummary(BaseModel):
    id: int
    kind: ListingKind
    title: str
    category: str
    condition: Condition
    price_cents: int
    currency: str
    status: ListingStatus
    city: str
    state: str
    seller_id: int
    seller_name: str
    seller_verified: bool
    photo_url: str | None
    fits_all: bool  # no fitment rows = universal part
    vehicle: dict | None = None  # whole-vehicle listings: year, make, model, odometer, title...
    saved: bool = False
    distance_mi: int | None = None  # when searching near a ZIP code
    buy_now: bool = False  # in-app payment available (shipped items, seller set up)
    created_at: datetime


class ListingOut(ListingSummary):
    description: str
    brand: str | None
    part_number: str | None
    quantity: int
    shipping: Shipping
    shipping_note: str | None
    shipping_cents: int | None = None
    buy_now_reason: str | None = None
    source_vin: str | None
    mileage: int | None
    emissions_compliance: str | None
    carb_eo_number: str | None
    status_reason: str | None
    fitment: list[dict]
    photos: list[dict]
    is_owner: bool
    updated_at: datetime


class StatusIn(Strict):
    status: Literal["active", "sold", "withdrawn"]


class ReportIn(Strict):
    reason: ListingReportReason
    details: Annotated[str, Field(max_length=2000)] | None = None


class MessageIn(Strict):
    body: Annotated[str, Field(min_length=1, max_length=2000)]


class MessageOut(BaseModel):
    id: int
    mine: bool
    body: str
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    listing_id: int
    listing_title: str
    other_name: str
    role: Literal["buyer", "seller"]
    unread: int
    last_message: str | None
    updated_at: datetime
    messages: list[MessageOut] | None = None


class ModListingIn(Strict):
    action: Literal["approve", "remove", "restore"]
    reason: Annotated[str, Field(max_length=500)] | None = None


class ModReportIn(Strict):
    action: Literal["resolve", "dismiss"]


class ModVerificationIn(Strict):
    action: Literal["approve", "reject"]
    note: Annotated[str, Field(max_length=500)] | None = None


class ModSellerIn(Strict):
    action: Literal["suspend", "reinstate"]
    reason: Annotated[str, Field(max_length=500)] | None = None


class ReviewIn(Strict):
    rating: Annotated[int, Field(ge=1, le=5)]
    comment: Annotated[str, Field(max_length=1000)] | None = None


class ReviewOut(BaseModel):
    id: int
    rating: int
    comment: str | None
    reviewer_name: str
    listing_title: str
    created_at: datetime
