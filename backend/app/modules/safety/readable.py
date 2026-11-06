"""Make NHTSA recall data easier to read and count.

- NHTSA text is often ALL CAPS: convert it to normal sentence case, keeping acronyms.
- A vehicle's recall list can include recalls filed by other companies (upfitters, equipment
  and conversion makers). Count only the vehicle maker's own recalls; group the rest.
- Some maker recalls name a specific engine ("vehicles equipped with 3.5L engines"); when
  that's a different engine from this vehicle's, put it in its own group.
"""

import re

# Vehicle make → words that appear in its maker's NHTSA manufacturer name.
MAKER_WORDS = {
    "chevrolet": ["general motors"], "gmc": ["general motors"], "buick": ["general motors"],
    "cadillac": ["general motors"], "pontiac": ["general motors"], "saturn": ["general motors"],
    "hummer": ["general motors"], "oldsmobile": ["general motors"],
    "ram": ["fca", "chrysler", "stellantis"], "dodge": ["fca", "chrysler", "stellantis"],
    "jeep": ["fca", "chrysler", "stellantis"], "chrysler": ["fca", "chrysler", "stellantis"],
    "fiat": ["fca", "fiat", "stellantis"], "toyota": ["toyota"], "lexus": ["toyota"],
    "scion": ["toyota"], "honda": ["honda"], "acura": ["honda"], "ford": ["ford"],
    "lincoln": ["ford"], "mercury": ["ford"], "nissan": ["nissan"], "infiniti": ["nissan"],
    "hyundai": ["hyundai"], "genesis": ["hyundai", "genesis"], "kia": ["kia"],
    "mercedes-benz": ["mercedes"], "mini": ["bmw", "mini"], "land rover": ["jaguar land rover"],
    "jaguar": ["jaguar"], "volkswagen": ["volkswagen"], "audi": ["volkswagen", "audi"],
}  # fmt: skip

ACRONYMS = {
    "ABS", "AC", "A/C", "ADAS", "AWD", "BCM", "CVT", "DTC", "ECM", "EGR", "ESC", "EV", "EVAP",
    "FCA", "FMVSS", "GM", "HVAC", "LED", "LLC", "MIL", "NHTSA", "OBD", "OTA", "PCM", "RWD",
    "SRS", "SUV", "TCM", "TPMS", "US", "USA", "VIN", "4WD", "2WD", "FWD", "HD", "EPB", "HEV",
    "PHEV", "BMW", "CNG", "LPG", "ACC", "LKA", "AEB", "RV", "II", "III", "IV",
    "OCSM", "TRS", "TECM", "SDM", "IPC", "EPS", "EBCM", "TIPM", "ORC", "RCM", "ESP", "VSA",
    "HID", "DRL", "ECU", "ACM", "PCV", "DCT", "MAF", "TPS", "OEM", "PSI", "MPH", "RPM", "VSC",
    "FCM", "BSM", "SCR", "DEF", "DPF", "PTU", "RDU", "ATF", "USB",
    "GPS", "LCD", "PRNDL", "SAE", "ISO", "TSB",
}  # fmt: skip
# Always capitalized in sentence case.
NAMES = {
    "january", "february", "march", "april", "june", "july", "august", "september",
    "october", "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "i",
}  # fmt: skip

_ENGINE = re.compile(r"\b(\d\.\d)\s*-?\s*(?:l\b|liter|litre)", re.IGNORECASE)


def is_maker_recall(manufacturer: str | None, make: str) -> bool:
    m = (manufacturer or "").lower()
    words = MAKER_WORDS.get(make.lower(), [make.lower()])
    return any(w in m for w in words)


def engines_named(*texts: str | None) -> set[float]:
    return {float(x) for t in texts if t for x in _ENGINE.findall(t)}


def recall_group(recall, make: str, displacement_l: float | None) -> str:
    """'maker' (counted), 'other_engine' (maker recall naming a different engine) or 'aftermarket'."""
    if not is_maker_recall(recall.manufacturer, make):
        return "aftermarket"
    named = engines_named(recall.summary, recall.component)
    if named and displacement_l and not any(abs(d - displacement_l) < 0.05 for d in named):
        return "other_engine"
    return "maker"


def readable(text: str | None, proper: set[str] = frozenset()) -> str | None:
    """ALL-CAPS text → sentence case. Leaves normal mixed-case text alone."""
    if not text:
        return text
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) / len(letters) < 0.7:
        return text
    proper_lower = {p.lower(): p for p in proper}

    def word(w: str) -> str:
        core = w.strip("().,;:'\"")
        parts = [p for p in re.split(r"[/-]", core) if p]
        if core[:1].isupper() and not core.isupper():
            return w  # already mixed case on purpose (e.g. the month "May")
        if parts and all(p.upper() in ACRONYMS for p in parts) or any(ch.isdigit() for ch in core):
            return w  # keep as-is (acronyms like TCM/PCM, part numbers, "3.5L")
        lw = w.lower()
        hit = proper_lower.get(core.lower())
        if hit:
            return lw.replace(core.lower(), hit)
        if core.lower() in NAMES and core:
            return lw.replace(core.lower(), core.capitalize())
        return lw

    text = re.sub(r":(?=\S)", ": ", text)
    text = re.sub(
        r"\bMAY(?=\s+\d)", "May", text
    )  # the month, not "may fail"  # "SYSTEM:BATTERY" -> "SYSTEM: BATTERY"
    out = " ".join(word(w) for w in text.split(" "))
    # Capitalize the start of each sentence.
    out = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out


def title_case(text: str | None) -> str | None:
    """ALL-CAPS label → Title Case ("FORD MOTOR COMPANY" → "Ford Motor Company"), acronyms kept."""
    if not text or not text.isupper():
        return text

    def w(x: str) -> str:
        core = x.strip("(),.")
        return x if core in ACRONYMS or any(c.isdigit() for c in core) else x.capitalize()

    return " ".join(w(x) for x in text.split(" "))


def proper_words(*names: str | None) -> set[str]:
    """Names to keep capitalized, e.g. 'Ford Motor Company', 'F-150'."""
    words = set()
    for n in names:
        for w in (n or "").replace(",", " ").split():
            w = w.strip("().")
            if w and w.upper() not in ACRONYMS:
                words.add(w if not w.isupper() else w.capitalize())
    return words
