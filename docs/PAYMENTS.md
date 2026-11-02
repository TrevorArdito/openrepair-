# Marketplace payments (Stripe Connect)

Status: **built for Stripe test mode, OFF by default** (`ENABLE_MARKET_PAYMENTS`). Needs the
marketplace on too (`ENABLE_MARKETPLACE`). Legal documents are DRAFTS for lawyer review
(`backend/app/legal/`, see `docs/legal/README.md`).

## How it works (plain English)
- **Sellers** tap "Set up payouts" → Stripe's own sign-up (identity, bank, tax info). Stripe
  verifies them and sends their 1099 tax forms. We never see card or bank numbers.
- **Local pickup** stays free: buyer and seller use in-app messages ("contact seller").
- **Shipped sales** get a *Buy now* button → Stripe's hosted checkout page. The money goes to the
  seller's Stripe balance; our fee (default **6%** of item + shipping) is taken automatically as a
  Stripe *application fee*. Stripe's processing fee is charged to the seller by Stripe.
- **Funds are held**: seller accounts are set to manual payouts. Each order's money is paid out to
  the seller when the buyer confirms receipt, or N days after delivery (default 3), or — if the
  seller never marks it delivered — N days after shipping (default 30), unless a problem is open.
- **Problems**: the buyer can report a problem before the money is released → seller responds →
  an admin decides "refund buyer" (our fee is refunded too) or "release to seller". Card
  chargebacks reported by the bank also freeze the order.
- **Receipts & history**: buyers and sellers see their orders and a receipt page; Stripe also
  emails the buyer a receipt.

## Stripe setup chosen
| Choice | Setting | Why |
|---|---|---|
| Account type | Express Dashboard (`controller.stripe_dashboard.type=express`) | Stripe hosts sign-up, ID checks, bank details, tax forms |
| Who pays Stripe fees | The seller (`controller.fees.payer=account`) — "Stripe handles pricing" | No monthly Connect fees for the platform |
| Who covers fraud losses | Stripe (`controller.losses.payments=stripe`) | A $0-budget platform shouldn't carry negative balances |
| Charge type | Direct charges + `application_fee_amount` | Required for "Stripe handles pricing"; seller is merchant of record |
| Holding funds | Payout schedule `manual`; we create each payout | Stripe allows platforms to manage payouts for Express-dashboard accounts |

**Sales tax (`MARKET_TAX_ENABLED`, off by default).** With direct charges the *seller* is the
merchant of record, so Stripe Tax collects tax on the seller's account (`liability: self`).
**Ask your CPA:** many US states have *marketplace facilitator* laws that make the marketplace
responsible for collecting tax once its sales into that state pass a threshold (often $100,000/yr).
Stripe's docs say platform-liable tax needs a different charge type (destination charges), which
can't be combined with "Stripe handles pricing". Switching later is a contained code change in
`backend/app/modules/marketplace/payments.py`.

**Contact-only categories (`MARKET_CONTACT_ONLY_CATEGORIES`, default `vehicle`).** Stripe's
restricted-business list doesn't ban US vehicle or auto-parts sales, but whole vehicles need an
in-person title transfer and large card payments invite fraud and chargebacks, so vehicles stay
"contact seller" until you change the setting. Add any category Stripe tells you it won't support.

**PayPal later.** All payment calls go through `PaymentProvider` (`payments.py`); orders record
which provider took the money. A PayPal provider can be added beside Stripe.

## Settings (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `ENABLE_MARKET_PAYMENTS` | `false` | Turn in-app payments on |
| `STRIPE_SECRET_KEY` | — | `sk_test_…` (test) or `sk_live_…` (live). **Secret.** |
| `STRIPE_WEBHOOK_SECRET` | — | `whsec_…` from the Connect webhook endpoint. **Secret.** |
| `MARKET_FEE_PERCENT` | `6` | Our fee on shipped / in-app sales |
| `MARKET_STRIPE_FEE_PERCENT` / `MARKET_STRIPE_FEE_FIXED_CENTS` | `2.9` / `30` | Used only to *show* sellers an estimate (Stripe's standard US card rate) |
| `MARKET_TAX_ENABLED` | `false` | Stripe Tax on checkout (after your CPA confirms) |
| `MARKET_RELEASE_DAYS_AFTER_DELIVERY` | `3` | Auto-release after delivery |
| `MARKET_RELEASE_DAYS_AFTER_SHIP` | `30` | Auto-release if never marked delivered |
| `MARKET_CONTACT_ONLY_CATEGORIES` | `vehicle` | Comma list of categories without *Buy now* |
| `MARKET_INFORM_SALES` / `MARKET_INFORM_REVENUE_CENTS` | `200` / `500000` | INFORM Consumers Act high-volume seller thresholds |

## Owner checklist — create Stripe and get test keys (about 20 minutes, free)
1. Go to **https://dashboard.stripe.com/register** and create an account with your project email.
   You can stay in **test mode** (toggle at the top right) without giving bank details yet.
2. Turn on Connect: in the Dashboard search for **"Connect"** → **Get started** → choose
   **Marketplace**. When asked who handles pricing, pick **"Stripe handles pricing for your
   users"**. When asked about dashboards, pick **Express**.
3. **Connect → Settings → Branding**: add the name *ChrystalClear* and an icon (shown to sellers).
4. **API keys**: Dashboard → **Developers → API keys** → copy the **Secret key** (`sk_test_…`).
   Never paste it into chat, GitHub, or a file — only into Render's environment settings.
5. **Webhook**: Developers → **Webhooks → Add endpoint**
   - URL: `https://<your-render-app>.onrender.com/api/v1/market/stripe/webhook`
   - Choose **"Events on Connected accounts"** and select: `checkout.session.completed`,
     `checkout.session.expired`, `account.updated`, `charge.dispute.created`, `charge.refunded`.
   - Copy the **Signing secret** (`whsec_…`).
6. On **Render → your service → Environment**, add:
   `ENABLE_MARKETPLACE=true`, `ENABLE_MARKET_PAYMENTS=true`,
   `STRIPE_SECRET_KEY=sk_test_…`, `STRIPE_WEBHOOK_SECRET=whsec_…`. Save (it redeploys).
7. Daily payout release: on GitHub → repo **Settings → Secrets and variables → Actions**, add
   `STRIPE_SECRET_KEY` (same test key). `PROD_DATABASE_URL` is already used by the data refresh.
8. Test: make a seller account, "Set up payouts" (Stripe test mode accepts its test data — use
   the "Use test data" buttons), list a shipped part, buy it from a second account with card
   `4242 4242 4242 4242`, any future date, any CVC.
9. **Going live later**: repeat steps 4–7 with live keys (`sk_live_…`) after Stripe approves your
   account, your lawyer/clinic reviews `backend/app/legal/`, and your CPA confirms the tax setup.
