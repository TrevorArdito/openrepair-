"""Explain what any OBD-II code means structurally — even codes we don't have
written up yet. Based on the public code-numbering scheme:

  P 0 3 01
  | | | +-- specific fault
  | | +---- subsystem (for P codes)
  | +------ 0 = generic (same on every vehicle), 1 = manufacturer-specific, ...
  +-------- P = powertrain, B = body, C = chassis, U = network
"""

import re

from app.core.errors import AppError

CODE_RE = re.compile(r"^[PBCU][0-3][0-9A-F]{3}$")

SYSTEMS = {"P": "powertrain", "B": "body", "C": "chassis", "U": "network"}

P_SUBSYSTEMS = {
    "0": "fuel_air_aux_emissions",
    "1": "fuel_air",
    "2": "fuel_air_injectors",
    "3": "ignition_misfire",
    "4": "aux_emissions",
    "5": "speed_idle",
    "6": "computer_outputs",
    "7": "transmission",
    "8": "transmission",
    "9": "transmission",
    "A": "hybrid",
    "B": "hybrid",
    "C": "hybrid",
}


def normalize_code(raw: str) -> str:
    return re.sub(r"[\s\-]", "", raw or "").upper()


def validate_code(raw: str) -> str:
    code = normalize_code(raw)
    if not CODE_RE.match(code):
        raise AppError("dtc_invalid", 422)
    return code


def is_generic(code: str) -> bool:
    # Generic: P0, P2, P34-P39, B0, C0, U0, U3. Manufacturer-specific: P1, P30-P33, B1/B2, C1/C2, U1/U2.
    first, second = code[0], code[1]
    if first == "P":
        return second in "02" or (second == "3" and code[2] in "456789")
    return second in "03"


def explain(code: str) -> dict:
    return {
        "system": SYSTEMS[code[0]],
        "generic": is_generic(code),
        "subsystem": P_SUBSYSTEMS.get(code[2]) if code[0] == "P" else None,
    }
