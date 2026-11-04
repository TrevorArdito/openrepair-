"""Payment providers. Everything that talks to Stripe lives here, behind a small interface,
so PayPal (or another provider) can be added later as a buyer payment option.

Stripe setup (docs/PAYMENTS.md):
- Connected accounts: Express Dashboard, Stripe collects its fees from the seller
  (controller.fees.payer=account, "Stripe handles pricing"), Stripe covers losses.
- Direct charges with an application fee (our percentage).
- Payout schedule set to manual; we pay out each order when it's released.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from app.config import get_settings
from app.core.errors import AppError

log = logging.getLogger(__name__)


# ---- fee math (shown to sellers before they list; used for the application fee) ---------


@dataclass(frozen=True)
class Breakdown:
    price_cents: int  # item total (unit price x quantity)
    shipping_cents: int
    gross_cents: int  # what the buyer pays before tax
    platform_fee_cents: int
    stripe_fee_cents: int  # estimate: Stripe's standard US card rate
    seller_net_cents: int
    fee_percent: float


def platform_fee(gross_cents: int, percent: float | None = None) -> int:
    pct = get_settings().market_fee_percent if percent is None else percent
    return max(0, round(gross_cents * pct / 100))


def breakdown(price_cents: int, shipping_cents: int = 0) -> Breakdown:
    s = get_settings()
    gross = price_cents + shipping_cents
    fee = platform_fee(gross)
    stripe_fee = (
        round(gross * s.market_stripe_fee_percent / 100) + s.market_stripe_fee_fixed_cents
        if gross
        else 0
    )
    return Breakdown(
        price_cents=price_cents,
        shipping_cents=shipping_cents,
        gross_cents=gross,
        platform_fee_cents=fee,
        stripe_fee_cents=stripe_fee,
        seller_net_cents=gross - fee - stripe_fee,
        fee_percent=s.market_fee_percent,
    )


# ---- provider interface ------------------------------------------------------------------


@dataclass
class AccountStatus:
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool


@dataclass
class CheckoutRequest:
    order_id: int
    account_id: str
    title: str
    unit_amount_cents: int
    quantity: int
    shipping_cents: int
    fee_cents: int
    tax: bool
    success_url: str
    cancel_url: str


class PaymentProvider(Protocol):
    name: str

    def create_seller_account(self, email: str, seller_id: int) -> str: ...
    def onboarding_link(self, account_id: str, return_url: str, refresh_url: str) -> str: ...
    def dashboard_link(self, account_id: str) -> str: ...
    def account_status(self, account_id: str) -> AccountStatus: ...
    def create_checkout(self, req: CheckoutRequest) -> tuple[str, str]: ...  # (id, url)
    def refund(self, account_id: str, payment_id: str) -> str: ...
    def payout(self, account_id: str, payment_id: str) -> str: ...
    def parse_webhook(self, payload: bytes, signature: str | None) -> dict: ...


class StripeProvider:
    name = "stripe"

    def __init__(self, secret_key: str, webhook_secret: str):
        import stripe

        self._stripe = stripe
        self.client = stripe.StripeClient(secret_key, max_network_retries=2)
        self.webhook_secret = webhook_secret

    def _call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except self._stripe.StripeError as exc:
            log.warning("stripe error: %s", exc.user_message or exc)
            raise AppError("payment_provider_error", 502) from exc

    def _acct(self, account_id: str) -> dict:
        return {"stripe_account": account_id}

    def create_seller_account(self, email: str, seller_id: int) -> str:
        acct = self._call(
            self.client.v1.accounts.create,
            {
                "country": "US",
                "email": email,
                "controller": {
                    "fees": {"payer": "account"},  # Stripe handles pricing; seller pays Stripe
                    "losses": {"payments": "stripe"},
                    "requirement_collection": "stripe",
                    "stripe_dashboard": {"type": "express"},
                },
                "capabilities": {
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                "settings": {"payouts": {"schedule": {"interval": "manual"}}},  # we hold funds
                "metadata": {"seller_id": str(seller_id)},
            },
        )
        return acct.id

    def onboarding_link(self, account_id: str, return_url: str, refresh_url: str) -> str:
        link = self._call(
            self.client.v1.account_links.create,
            {
                "account": account_id,
                "type": "account_onboarding",
                "return_url": return_url,
                "refresh_url": refresh_url,
            },
        )
        return link.url

    def dashboard_link(self, account_id: str) -> str:
        return self._call(self.client.v1.accounts.login_links.create, account_id).url

    def account_status(self, account_id: str) -> AccountStatus:
        a = self._call(self.client.v1.accounts.retrieve, account_id)
        return AccountStatus(
            bool(a.charges_enabled), bool(a.payouts_enabled), bool(a.details_submitted)
        )

    def create_checkout(self, req: CheckoutRequest) -> tuple[str, str]:
        params: dict[str, Any] = {
            "mode": "payment",
            "line_items": [
                {
                    "quantity": req.quantity,
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": req.unit_amount_cents,
                        "product_data": {"name": req.title[:250]},
                        "tax_behavior": "exclusive",
                    },
                }
            ],
            "shipping_address_collection": {"allowed_countries": ["US"]},
            "shipping_options": [
                {
                    "shipping_rate_data": {
                        "type": "fixed_amount",
                        "display_name": "Shipping",
                        "fixed_amount": {"amount": req.shipping_cents, "currency": "usd"},
                        "tax_behavior": "exclusive",
                    }
                }
            ],
            "payment_intent_data": {
                "application_fee_amount": req.fee_cents,
                "metadata": {"order_id": str(req.order_id)},
            },
            "metadata": {"order_id": str(req.order_id)},
            "client_reference_id": str(req.order_id),
            "success_url": req.success_url,
            "cancel_url": req.cancel_url,
        }
        if req.tax:  # seller is merchant of record with direct charges (see docs/PAYMENTS.md)
            params["automatic_tax"] = {"enabled": True, "liability": {"type": "self"}}
        session = self._call(
            self.client.v1.checkout.sessions.create, params, self._acct(req.account_id)
        )
        return session.id, session.url

    def refund(self, account_id: str, payment_id: str) -> str:
        r = self._call(
            self.client.v1.refunds.create,
            {"payment_intent": payment_id, "refund_application_fee": True},
            self._acct(account_id),
        )
        return r.id

    def payout(self, account_id: str, payment_id: str) -> str:
        """Pay out this order's net (after Stripe's fee and our fee) to the seller's bank."""
        pi = self._call(
            self.client.v1.payment_intents.retrieve,
            payment_id,
            {"expand": ["latest_charge.balance_transaction"]},
            self._acct(account_id),
        )
        bt = pi.latest_charge.balance_transaction
        if bt.status != "available":
            raise AppError("payout_not_ready", 409)  # funds still settling; retried next run
        p = self._call(
            self.client.v1.payouts.create,
            {"amount": bt.net, "currency": bt.currency, "metadata": {"payment": payment_id}},
            self._acct(account_id),
        )
        return p.id

    def parse_webhook(self, payload: bytes, signature: str | None) -> dict:
        try:
            event = self.client.construct_event(payload, signature, self.webhook_secret)
        except (ValueError, self._stripe.SignatureVerificationError) as exc:
            raise AppError("webhook_invalid", 400) from exc
        return event.to_dict() if hasattr(event, "to_dict") else dict(event)


@lru_cache
def _stripe_provider(secret: str, webhook_secret: str) -> StripeProvider:
    return StripeProvider(secret, webhook_secret)


def get_provider() -> PaymentProvider:
    """FastAPI dependency (tests replace it with a fake)."""
    s = get_settings()
    if not s.market_payments_on or not s.stripe_secret_key:
        raise AppError("payments_not_configured", 503)
    return _stripe_provider(s.stripe_secret_key, s.stripe_webhook_secret)
