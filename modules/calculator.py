"""
All the maths. Python does the calculations; the AI never does.
Every function that needs rates takes the tariff dictionary as an argument.
"""
import math
from decimal import Decimal, ROUND_HALF_UP


def _money(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def appliance_kwh(watts, hours_per_day, quantity=1, days=30):
    """Return (daily_kwh, period_kwh) for one appliance."""
    daily = watts * hours_per_day * quantity / 1000
    return daily, daily * days


def household_summary(appliances, tariff, days=30):
    """appliances: list of dicts with name, watts, hours, qty. Cost uses energy + fuel rate."""
    per_kwh = tariff["energy_rate"] + tariff["fuel_rate"]
    rows = []
    for a in appliances:
        daily, period = appliance_kwh(a["watts"], a["hours"], a["qty"], days)
        rows.append({
            "name": a["name"],
            "daily_kwh": round(daily, 2),
            "monthly_kwh": round(period, 2),
            "monthly_cost": round(period * per_kwh, 2),
        })
    return rows


def _num(value):
    """A number, or None if the value is blank or not a number."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def clean_appliances(rows):
    """
    Check the rows a user typed into the appliance table.
    Returns (good_rows, problems). Completely blank rows are skipped silently.
    """
    good, problems = [], []
    for n, row in enumerate(rows, start=1):
        name = str(row.get("name") or "").strip()
        if name.lower() == "nan":
            name = ""
        watts, hours, qty = _num(row.get("watts")), _num(row.get("hours")), _num(row.get("qty"))
        if not name and watts is None and hours is None and qty is None:
            continue
        qty = 1 if qty is None else qty
        if not name:
            problems.append(f"Row {n}: appliance name is missing")
        elif watts is None or watts < 0:
            problems.append(f"Row {n} ({name}): wattage must be a number, 0 or more")
        elif hours is None or not 0 <= hours <= 24:
            problems.append(f"Row {n} ({name}): hours per day must be between 0 and 24")
        elif qty < 0:
            problems.append(f"Row {n} ({name}): quantity cannot be negative")
        else:
            good.append({"name": name, "watts": watts, "hours": hours, "qty": qty})
    return good, problems


def what_if(appliances, name, hours_less, tariff, days=30):
    """Estimated monthly bill before and after using one appliance fewer hours per day."""
    def total_kwh(items):
        return sum(appliance_kwh(a["watts"], a["hours"], a["qty"], days)[1] for a in items)

    changed = [dict(a, hours=max(0, a["hours"] - hours_less)) if a["name"] == name else dict(a)
               for a in appliances]
    before_kwh, after_kwh = total_kwh(appliances), total_kwh(changed)
    before = bill_breakdown(before_kwh, tariff)["total_due"]
    after = bill_breakdown(after_kwh, tariff)["total_due"]
    return {"before_kwh": round(before_kwh, 2), "after_kwh": round(after_kwh, 2),
            "before_total": before, "after_total": after, "saving": round(before - after, 2)}


def bill_breakdown(kwh, tariff):
    """What a bill for this many kWh should look like under the tariff."""
    kwh_d = Decimal(str(kwh))
    energy = _money(kwh_d * Decimal(str(tariff["energy_rate"])))
    fuel = _money(kwh_d * Decimal(str(tariff["fuel_rate"])))
    fixed = _money(Decimal(str(tariff["fixed_charge"])))
    subtotal = energy + fuel + fixed
    tax = _money(subtotal * Decimal(str(tariff["tax_rate"])))
    total = subtotal + tax
    return {
        "energy_charge": float(energy), "fuel_charge": float(fuel),
        "fixed_charge": float(fixed), "tax": float(tax), "total_due": float(total),
    }


CHECKED_FIELDS = ["energy_charge", "fuel_charge", "fixed_charge", "tax", "total_due"]


def check_bill(parsed, tariff, tolerance=0.01):
    """
    Compare a parsed bill with what the loaded tariff says it should be.
    Returns {"ok", "issues", "expected", "kwh_used_for_check", "kwh_source"}.
    ok is None when the check cannot be done.
    """
    kwh = parsed.get("kwh_used")
    source = "printed on bill"
    if kwh is None:
        prev, cur = parsed.get("previous_reading"), parsed.get("current_reading")
        if prev is not None and cur is not None:
            kwh, source = cur - prev, "worked out from meter readings"
        else:
            return {"ok": None, "issues": ["kWh not found, so the bill cannot be checked."],
                    "expected": None, "kwh_used_for_check": None, "kwh_source": None}

    expected = bill_breakdown(kwh, tariff)
    issues = []
    for field in CHECKED_FIELDS:
        printed = parsed.get(field)
        if printed is None:
            continue
        if abs(printed - expected[field]) > tolerance:
            issues.append(
                f"{field}: bill shows {printed:,.2f}, tariff says {expected[field]:,.2f} "
                f"(difference {printed - expected[field]:+,.2f})"
            )
    return {"ok": not issues, "issues": issues, "expected": expected,
            "kwh_used_for_check": kwh, "kwh_source": source}