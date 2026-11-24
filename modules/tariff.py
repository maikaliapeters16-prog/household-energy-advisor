"""
Loads the tariff (electricity rates) from data/tariff.json.

Every part of the project reads rates from here and nowhere else.
To use real rates, replace the values in data/tariff.json and set
"is_fictional" to false, with the official source and date.
"""
import json
from pathlib import Path

import config

REQUIRED_KEYS = [
    "name", "is_fictional", "source", "date", "currency",
    "energy_rate", "fuel_rate", "fixed_charge", "tax_rate",
]
NUMBER_KEYS = ["energy_rate", "fuel_rate", "fixed_charge", "tax_rate"]


def load_tariff(path=None):
    """Read and validate the tariff file. Raises ValueError with a clear message if it is wrong."""
    path = Path(path or config.TARIFF_PATH)
    with open(path, encoding="utf-8") as f:
        tariff = json.load(f)

    missing = [k for k in REQUIRED_KEYS if k not in tariff]
    if missing:
        raise ValueError(f"{path.name} is missing: {', '.join(missing)}")

    for key in NUMBER_KEYS:
        value = tariff[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{key} in {path.name} must be a number that is 0 or more")
    if tariff["tax_rate"] > 1:
        raise ValueError("tax_rate must be a fraction, e.g. 0.15 for 15%")

    return tariff