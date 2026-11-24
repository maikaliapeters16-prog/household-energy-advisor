"""
Reads a bill PDF and pulls out the fields. Tuned to the fictional sample bills.
pypdf puts a label and its value on separate lines, so every pattern allows whitespace (including a newline) between them.
A field that cannot be found is None. We never guess.
"""
import re

from pypdf import PdfReader

NUM = r"([\d,]+)"            # whole number, with optional thousands commas
MONEY = r"([\d,]+\.\d{2})"   # amount with two decimals
PCT = r"\([\d.]+%\)"         # e.g. (15%)

PATTERNS = {
    "account_number": (r"Account Number:\s*([A-Z]{2}-\d+)", str),
    "days": (r"Days in Period:\s*(\d+)", int),
    "previous_reading": (r"Previous Reading\s+" + NUM, int),
    "current_reading": (r"Current Reading\s+" + NUM, int),
    "kwh_used": (r"(?:kWh Used|Units Consumed \(kWh\))\s+" + NUM, int),
    "energy_charge": (r"Energy Charge\s+" + MONEY, float),
    "fuel_charge": (r"Fuel Adjustment(?: Charge)?\s+" + MONEY, float),
    "fixed_charge": (r"(?:Fixed )?Customer Charge\s+" + MONEY, float),
    "tax": (r"(?:Sales )?Tax\s+" + PCT + r"\s+" + MONEY, float),
    "total_due": (r"(?:Total Amount Due|Amount Payable)\s+" + MONEY, float),
}


def extract_text(file):
    """file: a path or an uploaded file object. Returns all the text in the PDF."""
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _convert(raw, kind):
    return raw if kind is str else kind(raw.replace(",", ""))


def parse_bill(text):
    """Return a dict of every field (None if not found) plus is_bill."""
    result = {}
    for field, (pattern, kind) in PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        result[field] = _convert(m.group(m.lastindex), kind) if m else None

    m = re.search(r"Billing Period:\s*(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", text)
    result["billing_period_start"] = m.group(1) if m else None
    result["billing_period_end"] = m.group(2) if m else None

    key_fields = ["kwh_used", "total_due", "account_number", "energy_charge"]
    result["is_bill"] = sum(result[f] is not None for f in key_fields) >= 2
    return result
