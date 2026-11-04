"""Marketplace payments API. Loaded only when ENABLE_MARKETPLACE and ENABLE_MARKET_PAYMENTS
are both true. Stripe keys come from environment variables only."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.audit import log_action
from app.core.deps import current_user, require_role, verify_csrf
from app.core.errors import AppError, NotFound
from app.core.ratelimit import rate_limit
from app.db import get_db
from app.modules.accounts.models import Role, User
from app.modules.accounts.router import EXPORT_HOOKS
from app.modules.marketplace import orders, service
from app.modules.marketplace.models import (
    Dispute,
    DisputeStatus,
    Listing,
    Order,
    OrderStatus,
    Seller,
)
from app.modules.marketplace.payments import PaymentProvider, breakdown, get_provider

router = APIRouter(prefix="/market", tags=["marketplace-payments"])
moderator = require_role(Role.moderator)
admin = require_role(Role.admin)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgreementIn(Strict):
    accept: bool
    version: str


class ContactIn(Strict):
    phone: Annotated[str, Field(pattern=r"^\+?[0-9 ().-]{7,20}$")]


class ShipIn(Strict):
    carrier: Annotated[str, Field(min_length=2, max_length=40)]
    tracking_number: Annotated[str, Field(min_length=4, max_length=60)]


class DisputeIn(Strict):
    reason: Literal["not_received", "not_as_described", "damaged", "wrong_part", "other"]
    details: Annotated[str, Field(min_length=10, max_length=2000)]


class RespondIn(Strict):
    response: Annotated[str, Field(min_length=5, max_length=2000)]


class DecideIn(Strict):
    decision: Literal["refund", "release"]
    note: Annotated[str, Field(max_length=1000)] | None = None


def _base_url(request: Request) -> str:
    return get_settings().public_base_url or str(request.base_url).rstrip("/")


def _seller(db: Session, user: User) -> Seller:
    seller = service.seller_for(db, user)
    if seller is None:
        raise AppError("seller_profile_required", 409)
    return seller


# ---- config and fee breakdown -----------------------------------------------------------


@router.get("/payments/config")
def config():
    s = get_settings()
    return {
        "enabled": s.market_payments_on,
        "fee_percent": s.market_fee_percent,
        "stripe_fee_percent": s.market_stripe_fee_percent,
        "stripe_fee_fixed_cents": s.market_stripe_fee_fixed_cents,
        "tax_enabled": s.market_tax_enabled,
        "contact_only_categories": sorted(s.contact_only_categories),
        "release_days_after_delivery": s.market_release_days_after_delivery,
        "agreement_version": orders.SELLER_AGREEMENT_VERSION,
    }


@router.get("/payments/breakdown")
def fee_breakdown(
    price_cents: int = Query(ge=0, le=10_000_000),
    shipping_cents: int = Query(0, ge=0, le=1_000_000),
):
    return breakdown(price_cents, shipping_cents).__dict__


# ---- seller payment setup -----------------------------------------------------------------


def _status(db: Session, seller: Seller) -> dict:
    return {
        "has_account": bool(seller.stripe_account_id),
        "charges_enabled": seller.charges_enabled,
        "payouts_enabled": seller.payouts_enabled,
        "details_submitted": seller.details_submitted,
        "agreement_version": seller.agreement_version,
        "agreement_current": seller.agreement_version == orders.SELLER_AGREEMENT_VERSION,
        "phone": seller.phone,
        "inform": orders.inform_status(db, seller),
    }


@router.get("/payments/me")
def my_payments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    seller = service.seller_for(db, user)
    return _status(db, seller) if seller else None


@router.post("/payments/agreement", dependencies=[Depends(verify_csrf)])
def accept_agreement(
    data: AgreementIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    seller = _seller(db, user)
    if not data.accept or data.version != orders.SELLER_AGREEMENT_VERSION:
        raise AppError("agreement_not_accepted", 422)
    seller.agreement_version = data.version
    seller.agreement_accepted_at = orders.now()
    db.commit()
    return _status(db, seller)


@router.post(
    "/payments/onboard",
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_onboard", 20, 3600))],
)
def onboard(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    seller = service.require_seller(db, user)
    if seller.agreement_version != orders.SELLER_AGREEMENT_VERSION:
        raise AppError("agreement_not_accepted", 422)
    if not seller.stripe_account_id:
        seller.stripe_account_id = provider.create_seller_account(user.email, seller.id)
        db.commit()
    base = _base_url(request)
    url = provider.onboarding_link(
        seller.stripe_account_id,
        f"{base}/market/selling?stripe=done",
        f"{base}/market/selling?stripe=retry",
    )
    return {"url": url}


@router.post("/payments/refresh", dependencies=[Depends(verify_csrf)])
def refresh(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    seller = _seller(db, user)
    if seller.stripe_account_id:
        st = provider.account_status(seller.stripe_account_id)
        seller.charges_enabled, seller.payouts_enabled = st.charges_enabled, st.payouts_enabled
        seller.details_submitted = st.details_submitted
        db.commit()
    return _status(db, seller)


@router.post("/payments/dashboard", dependencies=[Depends(verify_csrf)])
def stripe_dashboard(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    seller = _seller(db, user)
    if not seller.stripe_account_id or not seller.details_submitted:
        raise AppError("payments_not_set_up", 409)
    return {"url": provider.dashboard_link(seller.stripe_account_id)}


@router.put("/payments/contact", dependencies=[Depends(verify_csrf)])
def save_contact(
    data: ContactIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    seller = _seller(db, user)
    seller.phone = data.phone
    db.commit()
    return _status(db, seller)


@router.post("/payments/inform-certify", dependencies=[Depends(verify_csrf)])
def inform_certify(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Seller confirms their identity, bank, tax and contact info is current (yearly)."""
    seller = _seller(db, user)
    if not seller.phone:
        raise AppError("phone_required", 422)
    seller.inform_certified_at = orders.now()
    db.commit()
    return _status(db, seller)


# ---- buying -------------------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/checkout",
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_checkout", 30, 3600))],
)
def checkout(
    listing_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    listing = db.get(Listing, listing_id)
    if listing is None or not service.can_view(listing, user):
        raise NotFound("listing_not_found")
    order, url = orders.start_checkout(db, provider, user, listing, _base_url(request))
    db.commit()
    return {"order_id": order.id, "url": url}


@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    """Stripe → us. No login/CSRF: authenticity is checked with the webhook signing secret."""
    event = provider.parse_webhook(await request.body(), request.headers.get("stripe-signature"))
    result = orders.handle_event(db, provider, event)
    db.commit()
    return {"received": True, "result": result}


# ---- orders -------------------------------------------------------------------------------


def order_out(db: Session, o: Order, user: User | None, full: bool = True) -> dict:
    r = orders.role(db, o, user) if user else None
    disputes = db.scalars(
        select(Dispute).where(Dispute.order_id == o.id).order_by(Dispute.id)
    ).all()
    due = orders.release_due_at(o)
    out = {
        "id": o.id,
        "role": r,
        "listing_id": o.listing_id,
        "listing_title": o.listing_title,
        "seller_id": o.seller_id,
        "seller_name": o.seller_name,
        "status": o.status.value,
        "quantity": o.quantity,
        "item_cents": o.item_cents,
        "shipping_cents": o.shipping_cents,
        "tax_cents": o.tax_cents,
        "total_cents": o.total_cents,
        "currency": o.currency,
        "created_at": o.created_at,
        "paid_at": o.paid_at,
        "shipped_at": o.shipped_at,
        "delivered_at": o.delivered_at,
        "released_at": o.released_at,
        "refunded_at": o.refunded_at,
        "release_due_at": due,
        "carrier": o.carrier,
        "tracking_number": o.tracking_number,
        "note": o.note,
    }
    if full:
        # Seller sees the address to ship to and their fee; buyer sees their own address.
        out["ship_name"], out["ship_address"] = o.ship_name, o.ship_address
        if r == "seller" or (user is not None and user.has_role(Role.moderator)):
            out["fee_cents"], out["fee_percent"] = o.fee_cents, o.fee_percent
        out["disputes"] = [
            {
                "id": d.id,
                "reason": d.reason.value,
                "details": d.details,
                "seller_response": d.seller_response,
                "status": d.status.value,
                "decision_note": d.decision_note,
                "created_at": d.created_at,
            }
            for d in disputes
        ]
    return out


def _my_order(db: Session, order_id: int, user: User) -> Order:
    o = db.get(Order, order_id)
    if o is None or (orders.role(db, o, user) is None and not user.has_role(Role.moderator)):
        raise NotFound("order_not_found")
    return o


@router.get("/orders")
def my_orders(
    as_: Literal["buyer", "seller"] = Query("buyer", alias="as"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if as_ == "buyer":
        cond = Order.buyer_id == user.id
    else:
        seller = service.seller_for(db, user)
        if seller is None:
            return []
        cond = Order.seller_id == seller.id
    rows = db.scalars(
        select(Order)
        .where(cond, Order.status != OrderStatus.canceled)
        .order_by(Order.id.desc())
        .limit(200)
    ).all()
    return [order_out(db, o, user, full=False) for o in rows]


@router.get("/orders/{order_id}")
def get_order(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return order_out(db, _my_order(db, order_id, user), user)


@router.post("/orders/{order_id}/ship", dependencies=[Depends(verify_csrf)])
def ship(
    order_id: int, data: ShipIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    o = _my_order(db, order_id, user)
    orders.mark_shipped(db, user, o, data.carrier, data.tracking_number)
    db.commit()
    return order_out(db, o, user)


@router.post("/orders/{order_id}/delivered", dependencies=[Depends(verify_csrf)])
def delivered(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    o = _my_order(db, order_id, user)
    orders.mark_delivered(db, user, o)
    db.commit()
    return order_out(db, o, user)


@router.post("/orders/{order_id}/confirm", dependencies=[Depends(verify_csrf)])
def confirm(
    order_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    o = _my_order(db, order_id, user)
    orders.confirm_received(db, provider, user, o)
    db.commit()
    return order_out(db, o, user)


@router.post(
    "/orders/{order_id}/dispute",
    dependencies=[Depends(verify_csrf), Depends(rate_limit("market_dispute", 10, 86400))],
)
def dispute(
    order_id: int,
    data: DisputeIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    o = _my_order(db, order_id, user)
    orders.open_dispute(db, user, o, data.reason, data.details)
    db.commit()
    return order_out(db, o, user)


@router.post("/disputes/{dispute_id}/respond", dependencies=[Depends(verify_csrf)])
def respond(
    dispute_id: int,
    data: RespondIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    d = db.get(Dispute, dispute_id)
    if d is None:
        raise NotFound("dispute_not_found")
    orders.respond_dispute(db, user, d, data.response)
    db.commit()
    return order_out(db, db.get(Order, d.order_id), user)


# ---- admin -------------------------------------------------------------------------------


@router.get("/mod/disputes")
def open_disputes(mod: User = Depends(moderator), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Dispute)
        .where(or_(Dispute.status == DisputeStatus.open, Dispute.status == DisputeStatus.responded))
        .order_by(Dispute.id)
    ).all()
    return [
        {"dispute_id": d.id, "order": order_out(db, db.get(Order, d.order_id), mod)} for d in rows
    ]


@router.post("/mod/disputes/{dispute_id}/decide", dependencies=[Depends(verify_csrf)])
def decide(
    dispute_id: int,
    data: DecideIn,
    adm: User = Depends(admin),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    d = db.get(Dispute, dispute_id)
    if d is None:
        raise NotFound("dispute_not_found")
    orders.decide_dispute(db, provider, adm, d, data.decision, data.note)
    log_action(db, adm, f"dispute_{data.decision}", "market_dispute", d.id, data.note)
    db.commit()
    return order_out(db, db.get(Order, d.order_id), adm)


@router.post("/mod/payouts/run", dependencies=[Depends(verify_csrf)])
def run_payouts(
    adm: User = Depends(admin),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_provider),
):
    n = orders.release_due(db, provider)
    log_action(db, adm, "payouts_run", "market_orders", 0, f"released {n}")
    db.commit()
    return {"released": n}


# ---- privacy: "download my data" ------------------------------------------------------


def _export(db: Session, user: User) -> dict:
    rows = db.scalars(select(Order).where(Order.buyer_id == user.id)).all()
    seller = service.seller_for(db, user)
    sold = db.scalars(select(Order).where(Order.seller_id == seller.id)).all() if seller else []
    return {
        "marketplace_orders": {
            "bought": [order_out(db, o, user) for o in rows],
            "sold": [order_out(db, o, user) for o in sold],
        }
    }


EXPORT_HOOKS.append(_export)
