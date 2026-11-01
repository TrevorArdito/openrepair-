"""What can be listed. Enforced on every create/edit; moderators handle the rest via reports.

Prohibited (CLAUDE.md, docs/COMMERCE_DESIGN.md):
- Used / rebuilt airbags and SRS parts (and new ones only from verified businesses —
  counterfeit airbags are a known killer).
- Anything that removes, disables or defeats emissions equipment ("delete" kits/pipes,
  O2 simulators/defoulers, test pipes) — Clean Air Act tampering / defeat-device rules.
- Catalytic converters: new ones must be EPA- or CARB-compliant (CARB needs an EO number);
  used/rebuilt ones only from sellers with an approved dismantler/business license.
- Counterfeit parts, stolen parts, parts with an unremedied safety recall — sellers must
  confirm the listing rules on every listing; reports + moderation catch the rest.
"""

import re

from app.core.errors import AppError
from app.modules.marketplace.models import Condition

# Category -> the repair-system slug it belongs to (links parts to guides/specs later).
CATEGORIES: dict[str, str | None] = {
    "engine": "engine",
    "cooling": "engine.cooling",
    "fuel": "fuel",
    "ignition": "engine.ignition",
    "intake": "engine.air_intake",
    "exhaust": "exhaust",
    "catalytic_converter": "exhaust.catalytic_converter",
    "emissions": "engine.emissions",
    "transmission": "transmission",
    "drivetrain": "drivetrain",
    "brakes": "brakes",
    "steering": "steering",
    "suspension": "suspension",
    "wheels_tires": "wheels_tires",
    "electrical": "electrical",
    "lighting": "electrical.lighting",
    "modules": "electrical.network",  # computers / control modules
    "hvac": "hvac",
    "body": "body",
    "glass": "body",
    "interior": "body",
    "airbag_srs": "restraints",
    "hybrid_ev": "hybrid_ev",
    "tools": None,
    "other": None,
}

# Emissions defeat / delete products. Word-boundary patterns, case-insensitive.
_DEFEAT = re.compile(
    r"""
    \b(egr|dpf|def|scr|cat|catalytic|catalyst|emissions?|o2|evap)\s*[-/ ]?\s*
        (delete|deletes|removal|eliminator|eliminators|bypass|block[- ]?off)\b
    | \bdelete\s*(kit|pipe|tune|tuner|race\s*pipe)s?\b
    | \b(o2|oxygen)\s*(sensor\s*)?(simulator|sim|spacer|defouler|eliminator)s?\b
    | \b(test|race|de-?cat)\s*pipes?\b
    | \bde-?cat\b
    | \bdefeat\s*device\b
    | \bemulator\b.*\b(def|adblue|nox|scr)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

USED_CONDITIONS = {Condition.used, Condition.reman, Condition.for_parts}


def check_listing(
    *,
    category: str,
    condition: Condition,
    text: str,
    emissions_compliance: str | None,
    carb_eo_number: str | None,
    seller_verified: bool,
) -> None:
    """Raise AppError with a stable code if the listing isn't allowed."""
    if category not in CATEGORIES:
        raise AppError("listing_invalid", 422, fields=[{"loc": ["category"]}])
    if _DEFEAT.search(text):
        raise AppError("listing_prohibited_defeat", 422)
    if category == "airbag_srs":
        if condition in USED_CONDITIONS:
            raise AppError("listing_prohibited_used_srs", 422)
        if not seller_verified:
            raise AppError("listing_requires_verified_seller", 403)
    if category == "catalytic_converter":
        if condition in USED_CONDITIONS:
            if not seller_verified:
                raise AppError("listing_requires_verified_seller", 403)
        elif emissions_compliance not in ("epa", "carb"):
            raise AppError("listing_needs_emissions_compliance", 422)
        if emissions_compliance == "carb" and not (carb_eo_number or "").strip():
            raise AppError("listing_needs_carb_eo", 422)
