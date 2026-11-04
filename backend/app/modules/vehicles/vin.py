"""VIN validation (ISO 3779 / 49 CFR 565) — runs before we ever call NHTSA.

- 17 characters, letters and digits only
- Letters I, O and Q are never used (too easy to confuse with 1 and 0)
- Position 9 is a check digit (required on North American vehicles); we report a
  mismatch as a warning because it usually means a typo.
"""

import re

from app.core.errors import AppError

_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

_TRANSLITERATION = {
    **{str(d): d for d in range(10)},
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}  # fmt: skip
_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)


def normalize_vin(raw: str) -> str:
    """Uppercase and strip spaces/dashes people often type or paste."""
    return re.sub(r"[\s\-]", "", raw or "").upper()


def validate_vin(raw: str) -> str:
    vin = normalize_vin(raw)
    if len(vin) != 17:
        raise AppError("vin_wrong_length", 422, length=len(vin))
    if re.search(r"[IOQ]", vin):
        raise AppError("vin_invalid_letters", 422)
    if not _VIN_RE.match(vin):
        raise AppError("vin_invalid_characters", 422)
    return vin


def compute_check_digit(vin: str) -> str:
    total = sum(_TRANSLITERATION[c] * w for c, w in zip(vin, _WEIGHTS, strict=True))
    remainder = total % 11
    return "X" if remainder == 10 else str(remainder)


def check_digit_valid(vin: str) -> bool:
    return compute_check_digit(vin) == vin[8]
