"""Marketplace payments with a fake Stripe: seller setup, fee breakdown, Buy now rules,
checkout + webhooks, held funds and release, disputes, INFORM check, legal pages."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings, get_settings
from app.core import ratelimit
from app.core.errors import AppError
from app.db import get_db
from app.main import create_app
from app.modules.accounts.models import Role, User, UserStatus
from app.modules.marketplace import orders as orders_mod
from app.modules.marketplace.models import Listing, ListingStatus, Order
from app.modules.marketplace.payments import AccountStatus, breakdown, get_provider
from app.modules.safety.nhtsa import get_nhtsa
from app.modules.vehicles.vpic import get_vpic
from tests.conftest import csrf, register

PW = "correct-horse-battery"
API = "/api/v1/market"
VERSION = orders_mod.SELLER_AGREEMENT_VERSION


class FakeStripe:
    name = "stripe"

    def __init__(self):
        self.accounts: dict[str, AccountStatus] = {}
        self.checkouts: list = []
        self.refunds: list = []
        self.payouts: list = []
        self.payout_ready = True

    def create_seller_account(self, email, seller_id):
        acct = f"acct_{seller_id}"
        self.accounts[acct] = AccountStatus(False, False, False)
        return acct

    def onboarding_link(self, account_id, return_url, refresh_url):
        return f"https://connect.stripe.test/{account_id}"

    def dashboard_link(self, account_id):
        return f"https://dashboard.stripe.test/{account_id}"

    def account_status(self, account_id):
        return self.accounts[account_id]

    def create_checkout(self, req):
        self.checkouts.append(req)
        return f"cs_{req.order_id}", f"https://checkout.stripe.test/cs_{req.order_id}"

    def refund(self, account_id, payment_id):
        self.refunds.append(payment_id)
        return f"re_{payment_id}"

    def payout(self, account_id, payment_id):
        if not self.payout_ready:
            raise AppError("payout_not_ready", 409)
        self.payouts.append(payment_id)
        return f"po_{payment_id}"

    def parse_webhook(self, payload, signature):
        import json

        if signature != "good":
            raise AppError("webhook_invalid", 400)
        return json.loads(payload)


@pytest.fixture
def fake():
    return FakeStripe()


@pytest.fixture
def pc(db_session_factory, vpic, nhtsa, fake, monkeypatch):
    s = get_settings()
    for k, v in {"enable_marketplace": True, "enable_market_payments": True,
                 "stripe_secret_key": "sk_test_fake", "market_fee_percent": 6.0}.items():  # fmt: skip
        monkeypatch.setattr(s, k, v)
    ratelimit.reset()
    app = create_app(Settings(enable_marketplace=True, enable_market_payments=True))

    def _db():
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_vpic] = lambda: vpic
    app.dependency_overrides[get_nhtsa] = lambda: nhtsa
    app.dependency_overrides[get_provider] = lambda: fake
    with TestClient(app) as c:
        yield c


def user(c, factory, email, role=Role.user):
    register(c, email=email, password=PW, name=email.split("@")[0])
    with factory() as db:
        u = db.scalar(select(User).where(User.email == email))
        u.role, u.status = role, UserStatus.active
        db.commit()


def login(c, email):
    c.cookies.clear()
    assert c.post("/api/v1/auth/login", json={"email": email, "password": PW}).status_code == 200


def ready_seller(c, fake, name="Dayton Parts"):
    c.put(f"{API}/seller/me", headers=csrf(c), json={"seller_type": "recycler", "display_name": name,
          "city": "Dayton", "state": "OH", "postal_code": "45402"})  # fmt: skip
    assert (
        c.post(f"{API}/payments/onboard", headers=csrf(c)).json()["error"]["code"]
        == "agreement_not_accepted"
    )
    c.post(f"{API}/payments/agreement", headers=csrf(c), json={"accept": True, "version": VERSION})
    url = c.post(f"{API}/payments/onboard", headers=csrf(c)).json()["url"]
    acct = url.rsplit("/", 1)[1]
    fake.accounts[acct] = AccountStatus(True, True, True)  # seller finished Stripe's sign-up
    st = c.post(f"{API}/payments/refresh", headers=csrf(c)).json()
    assert st["charges_enabled"] and st["agreement_current"]
    return acct


def shipped_listing(c, **kw):
    body = {"title": "Alternator 2015 F-150 3.5L", "description": "Tested good on the bench.",
            "category": "electrical", "condition": "used", "price_cents": 10000, "shipping": "ships",
            "shipping_cents": 1500, "accept_rules": True, **kw}  # fmt: skip
    r = c.post(f"{API}/listings", json=body, headers=csrf(c))
    assert r.status_code == 201, r.text
    return r.json()


def event(c, payload):
    import json

    r = c.post(
        f"{API}/stripe/webhook", content=json.dumps(payload), headers={"stripe-signature": "good"}
    )
    assert r.status_code == 200, r.text
    return r.json()["result"]


def paid(c, order_id, acct, pi="pi_1"):
    return event(c, {"type": "checkout.session.completed", "account": acct, "data": {"object": {
        "id": f"cs_{order_id}", "payment_status": "paid", "payment_intent": pi, "amount_total": 11500,
        "total_details": {"amount_tax": 0},
        "collected_information": {"shipping_details": {"name": "Pat Buyer", "address": {
            "line1": "1 Main St", "city": "Columbus", "state": "OH", "postal_code": "43215", "country": "US"}}},
    }}})  # fmt: skip


def buy(c, listing_id):
    r = c.post(f"{API}/listings/{listing_id}/checkout", headers=csrf(c))
    assert r.status_code == 200, r.text
    return r.json()


# ---- tests ----------------------------------------------------------------------------------


def test_payments_module_off_by_default(client):
    assert client.get(f"{API}/payments/config").status_code == 404


def test_fee_breakdown_and_setting(pc, monkeypatch):
    b = pc.get(
        f"{API}/payments/breakdown", params={"price_cents": 10000, "shipping_cents": 1500}
    ).json()
    assert b["gross_cents"] == 11500 and b["platform_fee_cents"] == 690  # 6%
    assert b["stripe_fee_cents"] == 334 + 30  # 2.9% + 30c estimate
    assert b["seller_net_cents"] == 11500 - 690 - 364
    monkeypatch.setattr(get_settings(), "market_fee_percent", 8.0)  # owner changes the setting
    assert breakdown(10000).platform_fee_cents == 800
    assert pc.get(f"{API}/payments/config").json()["fee_percent"] == 8.0


def test_full_purchase_hold_and_release(pc, db_session_factory, fake):
    c = pc
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    acct = ready_seller(c, fake)
    item = shipped_listing(c)
    assert item["buy_now"] is True
    pickup = shipped_listing(
        c, title="Pickup-only bumper cover", shipping="pickup", shipping_cents=None
    )
    assert pickup["buy_now"] is False and pickup["buy_now_reason"] == "pickup_only"
    assert (
        c.post(f"{API}/listings/{item['id']}/checkout", headers=csrf(c)).json()["error"]["code"]
        == "cannot_buy_own"
    )

    login(c, "buyer@example.com")
    out = buy(c, item["id"])
    assert out["url"].startswith("https://checkout.stripe.test/")
    req = fake.checkouts[-1]
    assert (req.account_id, req.fee_cents, req.shipping_cents, req.tax) == (acct, 690, 1500, False)

    assert event(c, {"type": "checkout.session.completed", "data": {"object": {}}}) == "ignored"
    assert paid(c, out["order_id"], acct) == "paid"
    assert paid(c, out["order_id"], acct) == "ignored"  # webhook retries are harmless
    with db_session_factory() as db:
        assert db.get(Listing, item["id"]).status == ListingStatus.sold
    order = c.get(f"{API}/orders/{out['order_id']}").json()
    assert order["status"] == "paid" and order["role"] == "buyer" and "fee_cents" not in order
    assert (
        c.post(f"{API}/orders/{order['id']}/confirm", headers=csrf(c)).json()["error"]["code"]
        == "order_wrong_status"
    )

    login(c, "sam@example.com")
    sold = c.get(f"{API}/orders", params={"as": "seller"}).json()
    assert [o["id"] for o in sold] == [order["id"]]
    detail = c.get(f"{API}/orders/{order['id']}").json()
    assert (
        detail["ship_name"] == "Pat Buyer"
        and "Columbus" in detail["ship_address"]
        and detail["fee_cents"] == 690
    )
    r = c.post(
        f"{API}/orders/{order['id']}/ship",
        headers=csrf(c),
        json={"carrier": "USPS", "tracking_number": "9400100000000000000000"},
    )
    assert r.json()["status"] == "shipped"
    assert fake.payouts == []  # money is held

    login(c, "buyer@example.com")
    r = c.post(f"{API}/orders/{order['id']}/confirm", headers=csrf(c))
    assert r.json()["status"] == "completed" and fake.payouts == ["pi_1"]


def test_auto_release_after_delivery_and_retry(pc, db_session_factory, fake):
    c = pc
    user(c, db_session_factory, "admin@example.com", role=Role.admin)
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    acct = ready_seller(c, fake)
    item = shipped_listing(c)
    login(c, "buyer@example.com")
    oid = buy(c, item["id"])["order_id"]
    paid(c, oid, acct)
    login(c, "sam@example.com")
    c.post(
        f"{API}/orders/{oid}/ship",
        headers=csrf(c),
        json={"carrier": "UPS", "tracking_number": "1Z999"},
    )
    c.post(f"{API}/orders/{oid}/delivered", headers=csrf(c))

    login(c, "admin@example.com")
    assert c.post(f"{API}/mod/payouts/run", headers=csrf(c)).json()["released"] == 0  # 3-day hold
    with db_session_factory() as db:
        o = db.get(Order, oid)
        o.delivered_at = datetime.now(UTC) - timedelta(days=4)
        db.commit()
    fake.payout_ready = False  # Stripe funds still settling: try again next run
    assert c.post(f"{API}/mod/payouts/run", headers=csrf(c)).json()["released"] == 0
    fake.payout_ready = True
    assert c.post(f"{API}/mod/payouts/run", headers=csrf(c)).json()["released"] == 1
    assert c.get(f"{API}/orders/{oid}").json()["status"] == "completed"


def test_dispute_refund_flow(pc, db_session_factory, fake):
    c = pc
    user(c, db_session_factory, "admin@example.com", role=Role.admin)
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    acct = ready_seller(c, fake)
    item = shipped_listing(c)
    login(c, "buyer@example.com")
    oid = buy(c, item["id"])["order_id"]
    paid(c, oid, acct)
    r = c.post(f"{API}/orders/{oid}/dispute", headers=csrf(c),
               json={"reason": "not_received", "details": "Nothing arrived after two weeks."})  # fmt: skip
    assert r.json()["status"] == "disputed"
    did = r.json()["disputes"][0]["id"]

    login(c, "sam@example.com")
    r = c.post(
        f"{API}/disputes/{did}/respond",
        headers=csrf(c),
        json={"response": "I never got the address."},
    )
    assert r.json()["disputes"][0]["status"] == "responded"
    assert (
        c.post(
            f"{API}/mod/disputes/{did}/decide", headers=csrf(c), json={"decision": "release"}
        ).status_code
        == 403
    )

    login(c, "admin@example.com")
    assert c.get(f"{API}/mod/disputes").json()[0]["dispute_id"] == did
    r = c.post(
        f"{API}/mod/disputes/{did}/decide",
        headers=csrf(c),
        json={"decision": "refund", "note": "No tracking."},
    )
    assert r.json()["status"] == "refunded" and fake.refunds == ["pi_1"] and fake.payouts == []
    assert c.post(f"{API}/mod/payouts/run", headers=csrf(c)).json()["released"] == 0


def test_chargeback_freezes_order(pc, db_session_factory, fake):
    c = pc
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    acct = ready_seller(c, fake)
    item = shipped_listing(c)
    login(c, "buyer@example.com")
    oid = buy(c, item["id"])["order_id"]
    paid(c, oid, acct)
    assert (
        event(c, {"type": "charge.dispute.created", "data": {"object": {"payment_intent": "pi_1"}}})
        == "chargeback"
    )
    assert c.get(f"{API}/orders/{oid}").json()["status"] == "disputed"


def test_buy_now_rules(pc, db_session_factory, fake):
    c = pc
    user(c, db_session_factory, "sam@example.com")
    c.put(f"{API}/seller/me", headers=csrf(c), json={"seller_type": "individual", "display_name": "Sam",
          "city": "Dayton", "state": "OH"})  # fmt: skip
    item = shipped_listing(c)
    assert (
        item["buy_now_reason"] == "seller_not_set_up"
    )  # no Stripe account yet: contact seller only
    ready_seller(c, fake, name="Sam")
    assert c.get(f"{API}/listings/{item['id']}").json()["buy_now"] is True
    assert c.get(f"{API}/payments/config").json()["contact_only_categories"] == ["vehicle"]


def test_webhook_signature_required(pc):
    r = pc.post(f"{API}/stripe/webhook", content=b"{}", headers={"stripe-signature": "forged"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "webhook_invalid"


def test_inform_high_volume_seller_must_verify(pc, db_session_factory, fake, monkeypatch):
    c = pc
    s = get_settings()
    monkeypatch.setattr(s, "market_inform_sales", 2)  # small thresholds for the test
    monkeypatch.setattr(s, "market_inform_revenue_cents", 15000)
    user(c, db_session_factory, "buyer@example.com")
    user(c, db_session_factory, "sam@example.com")
    acct = ready_seller(c, fake)
    a, b = shipped_listing(c), shipped_listing(c, title="Starter 2015 F-150 3.5L")
    login(c, "buyer@example.com")
    for i, item in enumerate((a, b)):
        paid(c, buy(c, item["id"])["order_id"], acct, pi=f"pi_{i}")

    login(c, "sam@example.com")
    st = c.get(f"{API}/payments/me").json()["inform"]
    assert st["high_volume"] and st["sales_12m"] == 2
    assert set(st["missing"]) == {"phone", "yearly_certification"}
    r = c.post(f"{API}/listings", headers=csrf(c), json={"title": "Water pump", "description": "New in box.",
               "category": "cooling", "condition": "new", "price_cents": 5000, "shipping": "ships",
               "shipping_cents": 900, "accept_rules": True})  # fmt: skip
    assert r.status_code == 403 and r.json()["error"]["code"] == "inform_verification_required"
    assert (
        c.post(f"{API}/payments/inform-certify", headers=csrf(c)).json()["error"]["code"]
        == "phone_required"
    )
    c.put(f"{API}/payments/contact", headers=csrf(c), json={"phone": "+1 937 555 0100"})
    st = c.post(f"{API}/payments/inform-certify", headers=csrf(c)).json()["inform"]
    assert st["ok"] is True


def test_legal_pages_are_drafts(client):
    for name in ("terms", "seller-agreement", "prohibited-items"):
        d = client.get(f"/api/v1/legal/{name}").json()
        assert d["draft"] is True and d["version"] and "DRAFT" in d["markdown"]
    terms = client.get("/api/v1/legal/terms").json()["markdown"]
    for must in ("third-party platform", "cooperate with law enforcement", "legal documentation",
                 "evidence of theft"):  # fmt: skip
        assert must in terms
    assert "delete kits" in client.get("/api/v1/legal/prohibited-items").json()["markdown"]


def test_stripe_provider_sends_planned_settings():
    """The real Stripe provider, with Stripe's client swapped for a recorder (no network)."""
    from types import SimpleNamespace

    from app.modules.marketplace.payments import CheckoutRequest, StripeProvider

    calls = []

    def rec(name, result):
        def fn(*args):
            calls.append((name, args))
            return result

        return fn

    p = StripeProvider("sk_test_x", "whsec_x")
    v1 = SimpleNamespace(
        accounts=SimpleNamespace(create=rec("accounts.create", SimpleNamespace(id="acct_1"))),
        checkout=SimpleNamespace(sessions=SimpleNamespace(
            create=rec("checkout.create", SimpleNamespace(id="cs_1", url="https://x")))),
        refunds=SimpleNamespace(create=rec("refunds.create", SimpleNamespace(id="re_1"))),
    )  # fmt: skip
    p.client = SimpleNamespace(v1=v1)

    assert p.create_seller_account("s@example.com", 7) == "acct_1"
    params = calls[-1][1][0]
    assert params["controller"] == {
        "fees": {"payer": "account"}, "losses": {"payments": "stripe"},
        "requirement_collection": "stripe", "stripe_dashboard": {"type": "express"},
    }  # fmt: skip
    assert params["settings"]["payouts"]["schedule"]["interval"] == "manual"

    p.create_checkout(CheckoutRequest(order_id=5, account_id="acct_1", title="Alternator",
                                      unit_amount_cents=10000, quantity=1, shipping_cents=1500,
                                      fee_cents=690, tax=True, success_url="s", cancel_url="c"))  # fmt: skip
    params, opts = calls[-1][1]
    assert opts == {"stripe_account": "acct_1"}  # direct charge on the seller's account
    assert params["payment_intent_data"]["application_fee_amount"] == 690
    assert params["automatic_tax"] == {"enabled": True, "liability": {"type": "self"}}
    assert params["shipping_options"][0]["shipping_rate_data"]["fixed_amount"]["amount"] == 1500

    p.refund("acct_1", "pi_1")
    params, opts = calls[-1][1]
    assert params == {"payment_intent": "pi_1", "refund_application_fee": True}
