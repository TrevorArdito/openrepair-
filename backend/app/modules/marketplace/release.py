"""Release held marketplace payments whose hold has ended. Run daily:

    python -m app.modules.marketplace.release

(GitHub Actions runs it; needs DATABASE_URL, STRIPE_SECRET_KEY, ENABLE_MARKETPLACE and
ENABLE_MARKET_PAYMENTS in the environment.)"""

from app.config import get_settings
from app.db import SessionLocal
from app.modules.marketplace.orders import release_due
from app.modules.marketplace.payments import get_provider


def main() -> None:
    if not get_settings().market_payments_on:
        print("Marketplace payments are off — nothing to do.")
        return
    provider = get_provider()
    with SessionLocal() as db:
        n = release_due(db, provider)
        db.commit()
    print(f"Released {n} order(s).")


if __name__ == "__main__":
    main()
