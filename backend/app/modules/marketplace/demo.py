"""Demo stock for showing the marketplace to local yards (MARKET_DEMO_DATA=true).

Everything here is clearly labeled as a sample: the seller is "Demo Yard (sample listings)" and
every title starts with "DEMO —", so nobody mistakes it for a real yard's inventory. Donor VINs
are made up in the right format (correct check digit) and don't belong
to a real car: they decode correctly at NHTSA (right year, make, model, engine) but use the
serial number 000000 (production numbers start above zero), so they should not belong to a
real vehicle. Turning the setting off removes the demo seller and all its listings.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import hash_password
from app.modules.accounts.models import Role, User, UserStatus
from app.modules.marketplace.models import (
    Condition,
    Listing,
    ListingFitment,
    ListingKind,
    ListingStatus,
    Running,
    Seller,
    SellerType,
    Shipping,
    TitleStatus,
    VehicleDetails,
)
from app.modules.vehicles import service as vehicles
from app.modules.vehicles.catalog import _make
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.vin import compute_check_digit

DEMO_EMAIL = "demo-yard@chrystalclear.invalid"  # .invalid can never receive mail
DEMO_NAME = "Demo Yard (sample listings)"


def _vin(prefix8: str, year_char: str, plant: str, serial: str) -> str:
    base = f"{prefix8}0{year_char}{plant}{serial}"
    return base[:8] + compute_check_digit(base) + base[9:]


# Donor vehicles: (make, model, year, displacement_l, cylinders, vin, odometer, running, title)
DONORS = {
    "f150": ("Ford", "F-150", 2012, 5.0, 8, _vin("1FTFW1EF", "C", "F", "000000"), 168_400,
             Running.runs_drives, TitleStatus.salvage),
    "camry": ("Toyota", "Camry", 2008, 2.4, 4, _vin("4T1BE46K", "8", "U", "000000"), 211_900,
              Running.not_running, TitleStatus.non_repairable),
    "accord": ("Honda", "Accord", 2006, 2.4, 4, _vin("1HGCM564", "6", "A", "000000"), 187_250,
               Running.runs_not_drives, TitleStatus.clean),
    "silverado": ("Chevrolet", "Silverado", 2010, 5.3, 8, _vin("1GCSKSE3", "A", "Z", "000000"),
                  203_600, Running.not_running, TitleStatus.salvage),
}  # fmt: skip

# (title, donor, kind, category, price_dollars, shipping, description)
LISTINGS = [
    ("DEMO — 2012 Ford F-150 5.0L, salvage title, runs and drives", "f150", "vehicle", "vehicle",
     3400, Shipping.pickup, "Sample listing. Front-end damage, engine runs smooth, automatic "
     "shifts fine. Salvage title in hand. Sold as-is for rebuild or parts."),
    ("DEMO — 2008 Toyota Camry 2.4L, parts car, non-running", "camry", "vehicle", "vehicle",
     650, Shipping.pickup, "Sample listing. Doesn't run. Good body panels, glass and interior. "
     "Junk/parts-only title. Tow-away."),
    ("DEMO — 2006 Honda Accord 2.4L, runs, doesn't drive (transmission)", "accord", "vehicle",
     "vehicle", 900, Shipping.pickup, "Sample listing. Engine runs well; no forward gears. "
     "Clean title. Good candidate for a transmission swap."),
    ("DEMO — 2010 Chevrolet Silverado 1500 5.3L, parts truck", "silverado", "vehicle", "vehicle",
     1500, Shipping.pickup, "Sample listing. Not running (lifter noise reported before parking). "
     "Bed, doors and rear axle in good shape. Salvage title."),
    ("DEMO — Automatic transmission, 2012 F-150 5.0L donor (168k miles)", "f150", "part",
     "transmission", 950, Shipping.pickup_or_ships, "Sample listing. Pulled from the donor truck "
     "above, which drove in. Fluid looked clean. 30-day yard warranty. Confirm the transmission "
     "and part number match yours before buying."),
    ("DEMO — Automatic transmission, 2010 Silverado 1500 5.3L donor (204k miles)", "silverado",
     "part", "transmission", 700, Shipping.pickup_or_ships, "Sample listing. Shifted through all "
     "gears before the engine was parked. Sold as-is. Check the tag against yours."),
    ("DEMO — 2.4L engine, 2008 Camry donor (212k miles, for rebuild)", "camry", "part", "engine",
     300, Shipping.pickup, "Sample listing. Non-running engine for rebuild or parts — "
     "turns over by hand. Core charge may apply."),
    ("DEMO — Alternator, 2006 Accord 2.4L donor (tested)", "accord", "part", "electrical",
     55, Shipping.pickup_or_ships, "Sample listing. Bench-tested good. Includes pulley."),
]  # fmt: skip


def _demo_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),  # nobody can log in
            display_name="Demo Yard",
            role=Role.user,
            status=UserStatus.active,
        )
        db.add(user)
        db.flush()
    return user


def load(db: Session) -> int:
    """Create the demo seller and listings once. Returns listings added."""
    s = get_settings()
    user = _demo_user(db)
    seller = db.scalar(select(Seller).where(Seller.user_id == user.id))
    if seller is None:
        seller = Seller(user_id=user.id, seller_type=SellerType.recycler, display_name=DEMO_NAME,
                        city=s.market_demo_city, state=s.market_demo_state,
                        postal_code=s.market_demo_zip or None,
                        about="Sample listings for demonstrating the marketplace. Not real inventory.")  # fmt: skip
        db.add(seller)
        db.flush()
    added = 0
    for title, donor, kind, category, price, shipping, desc in LISTINGS:
        if db.scalar(
            select(Listing.id).where(Listing.seller_id == seller.id, Listing.title == title)
        ):
            continue
        make_name, model_name, year, disp, cyl, vin, miles, running, title_status = DONORS[donor]
        make = _make(db, make_name)
        model = vehicles.get_or_create_model(db, make, None, model_name)
        vehicle = db.scalar(
            select(Vehicle)
            .where(
                Vehicle.model_id == model.id,
                Vehicle.year == year,
                func.abs(Vehicle.engine_displacement_l - disp) < 0.05,
            )
            .limit(1)  # fmt: skip
        )
        listing = Listing(
            seller_id=seller.id, title=title, description=desc,
            kind=ListingKind.vehicle if kind == "vehicle" else ListingKind.part, category=category,
            condition=Condition.for_parts if "rebuild" in title else Condition.used,
            price_cents=price * 100, quantity=1, shipping=shipping,
            source_vin=None if kind == "vehicle" else vin, mileage=None if kind == "vehicle" else miles,
            status=ListingStatus.active, rules_accepted_at=datetime.now(UTC),
            search_text=f"{title} {desc} {year} {make_name} {model_name} {vin}".lower(),
        )  # fmt: skip
        if kind == "vehicle":
            listing.vehicle = VehicleDetails(
                year=year, make_id=make.id, model_id=model.id,
                vehicle_id=vehicle.id if vehicle else None, vin=vin, odometer=miles,
                title_status=title_status, running=running,
            )  # fmt: skip
        else:
            listing.fitment = [ListingFitment(make_id=make.id, model_id=model.id, year_from=year,
                                              year_to=year, displacement_l=disp)]  # fmt: skip
        db.add(listing)
        added += 1
    db.flush()
    return added


def remove(db: Session) -> bool:
    """Delete the demo seller (and, through it, every demo listing)."""
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        return False
    seller = db.scalar(select(Seller).where(Seller.user_id == user.id))
    if seller is not None:
        for listing in db.scalars(select(Listing).where(Listing.seller_id == seller.id)):
            db.delete(listing)
        db.delete(seller)
    db.delete(user)
    db.flush()
    return True
