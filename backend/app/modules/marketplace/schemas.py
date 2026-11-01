from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.community.schemas import AppliesTo
from app.modules.marketplace.models import (
    Condition,
    ListingReportReason,
    ListingStatus,
    SellerType,
    Shipping,
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
    source_vin: Annotated[str, Field(pattern=r"^[A-HJ-NPR-Z0-9]{17}$")] | None = None
    mileage: Annotated[int, Field(ge=0, le=2_000_000)] | None = None
    emissions_compliance: Literal["epa", "carb"] | None = None
    carb_eo_number: Annotated[str, Field(max_length=30)] | None = None
    fitment: Annotated[list[AppliesTo], Field(max_length=30)] = []  # empty = universal
    photo_ids: Annotated[list[int], Field(max_length=12)] = []
    accept_rules: bool  # must be true: not stolen, not counterfeit, no open recall, legal

    @field_validator("source_vin", mode="before")
    @classmethod
    def _vin(cls, v):
        return v.strip().upper() or None if isinstance(v, str) else v


class ListingSummary(BaseModel):
    id: int
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
    created_at: datetime


class ListingOut(ListingSummary):
    description: str
    brand: str | None
    part_number: str | None
    quantity: int
    shipping: Shipping
    shipping_note: str | None
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
