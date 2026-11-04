"""In-app purchases: checkout, Stripe events, shipping, held funds, release, problems
(disputes), and the INFORM Consumers Act high-volume seller check. See docs/PAYMENTS.md."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import AppError, NotFound
from app.modules.accounts.models import User
from app.modules.community.service import ensure_can_contribute
from app.modules.marketplace.models import (
    Dispute,
    DisputeReason,
    DisputeStatus,
    Listing,
    ListingKind,
    ListingStatus,
    Order,
    OrderStatus,
    Seller,
    SellerStatus,
    Shipping,
)
from app.modules.marketplace.payments import CheckoutRequest, PaymentProvider, platform_fee

log = logging.getLogger(__name__)
_AGREEMENT = Path(__file__).resolve().parents[2] / "legal" / "SELLER_AGREEMENT.md"
# Sellers must (re-)accept the Seller Agreement whenever its "Version:" line changes.
SELLER_AGREEMENT_VERSION = next(
    ln.split("Version:", 1)[1].strip()
    for ln in _AGREEMENT.read_text(encoding="utf-8").splitlines()
    if "Version:" in ln
)
HELD = (OrderStatus.paid, OrderStatus.shipped, OrderStatus.delivered)
COUNTED = (*HELD, OrderStatus.completed, OrderStatus.disputed)


def now() -> datetime:
    return datetime.now(UTC)


def aware(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=UTC)


# ---- INFORM Consumers Act ---------------------------------------------------------------


def inform_status(db: Session, seller: Seller) -> dict:
    """High-volume seller = 200+ sales and $5,000+ gross in the last 12 months (thresholds are
    settings). Counts in-app orders and listings marked sold (local pickup sales)."""
    s = get_settings()
    since = now() - timedelta(days=365)
    n_orders, rev_orders = db.execute(
        select(
            func.count(Order.id), func.coalesce(func.sum(Order.total_cents - Order.tax_cents), 0)
        ).where(Order.seller_id == seller.id, Order.status.in_(COUNTED), Order.paid_at >= since)
    ).one()
    n_sold, rev_sold = db.execute(
        select(func.count(Listing.id), func.coalesce(func.sum(Listing.price_cents), 0)).where(
            Listing.seller_id == seller.id,
            Listing.status == ListingStatus.sold,
            Listing.updated_at >= since,
            ~Listing.id.in_(select(Order.listing_id).where(Order.listing_id.is_not(None))),
        )
    ).one()
    sales, revenue = (n_orders or 0) + (n_sold or 0), (rev_orders or 0) + (rev_sold or 0)
    high = sales >= s.market_inform_sales and revenue >= s.market_inform_revenue_cents
    missing = []
    if high:
        if not (seller.details_submitted and seller.payouts_enabled):
            missing.append("verified_identity_and_bank")  # collected and verified by Stripe
        if not seller.phone:
            missing.append("phone")
        cert = aware(seller.inform_certified_at)
        if cert is None or cert < now() - timedelta(days=365):
            missing.append("yearly_certification")
    return {
        "high_volume": high,
        "sales_12m": sales,
        "revenue_12m_cents": revenue,
        "missing": missing,
        "ok": not missing,
    }


def ensure_inform_ok(db: Session, seller: Seller) -> None:
    if not inform_status(db, seller)["ok"]:
        raise AppError("inform_verification_required", 403)


# ---- can this listing be bought in the app? ----------------------------------------------


def buy_now_reason(listing: Listing) -> str | None:
    """None if Buy now is available, else a stable reason code."""
    s = get_settings()
    seller = listing.seller
    if not s.market_payments_on:
        return "payments_off"
    if listing.status != ListingStatus.active or seller.status != SellerStatus.active:
        return "not_available"
    if listing.kind == ListingKind.vehicle or listing.category in s.contact_only_categories:
        return "contact_only_category"
    if listing.shipping == Shipping.pickup or listing.shipping_cents is None:
        return "pickup_only"
    if not (seller.stripe_account_id and seller.charges_enabled and seller.agreement_accepted_at):
        return "seller_not_set_up"
    return None


def start_checkout(
    db: Session, provider: PaymentProvider, buyer: User, listing: Listing, base_url: str
) -> tuple[Order, str]:
    ensure_can_contribute(buyer)
    if (reason := buy_now_reason(listing)) is not None:
        raise AppError("buy_now_unavailable", 409, reason=reason)
    if listing.seller.user_id == buyer.id:
        raise AppError("cannot_buy_own", 409)
    ensure_inform_ok(db, listing.seller)
    shipping = listing.shipping_cents or 0
    gross = listing.price_cents + shipping
    pct = get_settings().market_fee_percent
    order = Order(
        listing_id=listing.id, seller_id=listing.seller_id, buyer_id=buyer.id,
        listing_title=listing.title, seller_name=listing.seller.display_name,
        provider=provider.name, provider_account=listing.seller.stripe_account_id, quantity=1,
        item_cents=listing.price_cents, shipping_cents=shipping, total_cents=gross,
        fee_percent=pct, fee_cents=platform_fee(gross, pct), status=OrderStatus.pending_payment,
    )  # fmt: skip
    db.add(order)
    db.flush()
    checkout_id, url = provider.create_checkout(
        CheckoutRequest(
            order_id=order.id,
            account_id=order.provider_account,
            title=listing.title,
            unit_amount_cents=listing.price_cents,
            quantity=1,
            shipping_cents=shipping,
            fee_cents=order.fee_cents,
            tax=get_settings().market_tax_enabled,
            success_url=f"{base_url}/market/orders/{order.id}?paid=1",
            cancel_url=f"{base_url}/market/listings/{listing.id}",
        )  # fmt: skip
    )
    order.checkout_id = checkout_id
    db.flush()
    return order, url


# ---- Stripe events ----------------------------------------------------------------------


def _address(details: dict | None) -> tuple[str | None, str | None]:
    if not details:
        return None, None
    a = details.get("address") or {}
    lines = [a.get("line1"), a.get("line2"),
             " ".join(filter(None, [a.get("city"), a.get("state"), a.get("postal_code")])),
             a.get("country")]  # fmt: skip
    return details.get("name"), "\n".join(x for x in lines if x)


def handle_event(db: Session, provider: PaymentProvider, event: dict) -> str:
    """Apply one webhook event. Returns what happened (for logs/tests). Idempotent."""
    kind = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    account = event.get("account")

    if kind == "account.updated":
        seller = db.scalar(select(Seller).where(Seller.stripe_account_id == obj.get("id")))
        if seller is None:
            return "ignored"
        seller.charges_enabled = bool(obj.get("charges_enabled"))
        seller.payouts_enabled = bool(obj.get("payouts_enabled"))
        seller.details_submitted = bool(obj.get("details_submitted"))
        return "seller_updated"

    if kind in ("checkout.session.completed", "checkout.session.expired"):
        order = db.scalar(select(Order).where(Order.checkout_id == obj.get("id")))
        if order is None or (account and order.provider_account != account):
            return "ignored"
        if kind == "checkout.session.expired":
            if order.status == OrderStatus.pending_payment:
                order.status = OrderStatus.canceled
            return "canceled"
        if order.status != OrderStatus.pending_payment or obj.get("payment_status") != "paid":
            return "ignored"
        details = (obj.get("collected_information") or {}).get("shipping_details") or obj.get(
            "shipping_details"
        )
        order.ship_name, order.ship_address = _address(details)
        order.payment_id = obj.get("payment_intent")
        order.total_cents = obj.get("amount_total") or order.total_cents
        order.tax_cents = ((obj.get("total_details") or {}).get("amount_tax")) or 0
        order.paid_at = now()
        order.status = OrderStatus.paid
        listing = db.get(Listing, order.listing_id) if order.listing_id else None
        if listing is not None:
            if listing.quantity < order.quantity:  # someone else bought the last one first
                provider.refund(order.provider_account, order.payment_id)
                order.status, order.refunded_at = OrderStatus.refunded, now()
                order.note = "sold_out"
                return "refunded_sold_out"
            listing.quantity -= order.quantity
            if listing.quantity == 0:
                listing.status = ListingStatus.sold
        return "paid"

    if kind in ("charge.dispute.created", "charge.refunded"):
        order = db.scalar(select(Order).where(Order.payment_id == obj.get("payment_intent")))
        if order is None:
            return "ignored"
        if kind == "charge.refunded" and obj.get("refunded"):
            order.status, order.refunded_at = OrderStatus.refunded, order.refunded_at or now()
            return "refunded"
        if kind == "charge.dispute.created" and order.status != OrderStatus.refunded:
            order.status = OrderStatus.disputed
            db.add(Dispute(order_id=order.id, reason=DisputeReason.chargeback,
                           details="Card chargeback opened by the buyer's bank.",
                           status=DisputeStatus.responded))  # fmt: skip
            return "chargeback"
        return "ignored"
    return "ignored"


# ---- shipping, delivery, receipt confirmation ---------------------------------------------


def _get(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFound("order_not_found")
    return order


def role(db: Session, order: Order, user: User) -> str | None:
    if order.buyer_id == user.id:
        return "buyer"
    seller = db.get(Seller, order.seller_id) if order.seller_id else None
    if seller is not None and seller.user_id == user.id:
        return "seller"
    return None


def mark_shipped(db: Session, user: User, order: Order, carrier: str, tracking: str) -> None:
    if role(db, order, user) != "seller":
        raise NotFound("order_not_found")
    if order.status not in (OrderStatus.paid, OrderStatus.shipped):
        raise AppError("order_wrong_status", 409)
    order.carrier, order.tracking_number = carrier, tracking
    order.shipped_at = order.shipped_at or now()
    order.status = OrderStatus.shipped


def mark_delivered(db: Session, user: User, order: Order) -> None:
    if role(db, order, user) is None:
        raise NotFound("order_not_found")
    if order.status != OrderStatus.shipped:
        raise AppError("order_wrong_status", 409)
    order.delivered_at, order.status = now(), OrderStatus.delivered


def confirm_received(db: Session, provider: PaymentProvider, user: User, order: Order) -> None:
    if role(db, order, user) != "buyer":
        raise NotFound("order_not_found")
    if order.status not in (OrderStatus.shipped, OrderStatus.delivered):
        raise AppError("order_wrong_status", 409)
    order.confirmed_at = now()
    order.delivered_at = order.delivered_at or order.confirmed_at
    order.status = OrderStatus.delivered
    _try_release(db, provider, order)


def release_due_at(order: Order) -> datetime | None:
    s = get_settings()
    if order.status not in (OrderStatus.shipped, OrderStatus.delivered):
        return None
    if order.confirmed_at:
        return aware(order.confirmed_at)
    if order.delivered_at:
        return aware(order.delivered_at) + timedelta(days=s.market_release_days_after_delivery)
    if order.shipped_at:
        return aware(order.shipped_at) + timedelta(days=s.market_release_days_after_ship)
    return None


def _try_release(db: Session, provider: PaymentProvider, order: Order) -> bool:
    try:
        order.payout_id = provider.payout(order.provider_account, order.payment_id)
    except AppError as exc:
        log.info("order %s not released yet: %s", order.id, exc.code)
        return False
    order.released_at, order.status = now(), OrderStatus.completed
    return True


def release_due(db: Session, provider: PaymentProvider) -> int:
    """Pay out every order whose hold has ended (run daily, and by admins on demand)."""
    released = 0
    for order in db.scalars(select(Order).where(Order.status.in_(HELD))).all():
        due = release_due_at(order)
        if due is not None and due <= now() and _try_release(db, provider, order):
            released += 1
    db.flush()
    return released


# ---- problems (disputes) -----------------------------------------------------------------


def open_dispute(
    db: Session, user: User, order: Order, reason: str, details: str | None
) -> Dispute:
    if role(db, order, user) != "buyer":
        raise NotFound("order_not_found")
    if order.status not in HELD:
        raise AppError("order_wrong_status", 409)
    order.status = OrderStatus.disputed
    d = Dispute(order_id=order.id, opened_by_id=user.id, reason=DisputeReason(reason),
                details=details)  # fmt: skip
    db.add(d)
    db.flush()
    return d


def respond_dispute(db: Session, user: User, dispute: Dispute, response: str) -> None:
    order = _get(db, dispute.order_id)
    if role(db, order, user) != "seller":
        raise NotFound("dispute_not_found")
    if dispute.status not in (DisputeStatus.open, DisputeStatus.responded):
        raise AppError("dispute_closed", 409)
    dispute.seller_response = response
    dispute.status = DisputeStatus.responded


def decide_dispute(
    db: Session,
    provider: PaymentProvider,
    admin: User,
    dispute: Dispute,
    decision: str,
    note: str | None,
) -> None:
    order = _get(db, dispute.order_id)
    if dispute.status in (DisputeStatus.refunded, DisputeStatus.released):
        raise AppError("dispute_closed", 409)
    if decision == "refund" and dispute.reason == DisputeReason.chargeback:
        raise AppError("chargeback_in_stripe", 409)  # the bank decides; respond in Stripe
    if decision == "refund":
        provider.refund(order.provider_account, order.payment_id)
        order.status, order.refunded_at, order.note = OrderStatus.refunded, now(), "dispute_refund"
        dispute.status = DisputeStatus.refunded
    else:
        dispute.status = DisputeStatus.released
        order.status = OrderStatus.delivered
        order.confirmed_at = order.confirmed_at or now()
        _try_release(db, provider, order)
    dispute.decided_by_id, dispute.decision_note = admin.id, note
