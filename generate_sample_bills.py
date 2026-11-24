"""
generate_sample_bills.py
Creates FICTIONAL electricity bill PDFs plus an answer key (expected_values.json)

The rates come from data/tariff.json, so changing that file and re-running this
script gives you matching bills and a matching answer key.

This script does its own sums on purpose and does NOT import modules/calculator.py.
That way the answer key is an independent check on your calculator.

Run: python generate_sample_bills.py
Needs: pip install reportlab
Output: data/demo/sample_bills/*.pdf and expected_values.json
"""
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent
TARIFF_PATH = BASE_DIR / "data" / "tariff.json"
OUT_DIR = BASE_DIR / "data" / "demo" / "sample_bills"

COMPANY = "9INE Power Co. (FICTIONAL)" 

with open(TARIFF_PATH, encoding="utf-8") as f:
    TARIFF = json.load(f)

ENERGY_RATE = Decimal(str(TARIFF["energy_rate"]))
FUEL_RATE = Decimal(str(TARIFF["fuel_rate"]))
FIXED_CHARGE = Decimal(str(TARIFF["fixed_charge"]))
TAX_RATE = Decimal(str(TARIFF["tax_rate"]))
CURRENCY = TARIFF["currency"]
TAX_PCT = format(TAX_RATE * 100, "f").rstrip("0").rstrip(".")


def money(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt(x):
    return f"{x:,.2f}"



LABELS = {
    "A": {"kwh": "kWh Used", "energy": "Energy Charge", "fuel": "Fuel Adjustment Charge",
          "fixed": "Customer Charge", "tax": f"Sales Tax ({TAX_PCT}%)", "total": "Total Amount Due"},
    "B": {"kwh": "Units Consumed (kWh)", "energy": "Energy Charge", "fuel": "Fuel Adjustment",
          "fixed": "Fixed Customer Charge", "tax": f"Tax ({TAX_PCT}%)", "total": "Amount Payable"},
}


BILLS = [
     ("bill_01.pdf", "Marcia Fictionson", "FS-100001", date(2026, 8, 3), 30, 10250, 150, "A", None,
     "Low usage, style A wording"),
    ("bill_02.pdf", "Devon Testerman", "FS-100002", date(2026, 8, 5), 30, 48200, 320, "A", None,
     "Typical household, style A"),
    ("bill_03.pdf", "Alicia Samplestone", "FS-100003", date(2026, 8, 9), 31, 7710, 780, "A", None,
     "High usage (heavy A/C), style A"),
    ("bill_04.pdf", "Ricardo Mockwell", "FS-100004", date(2026, 8, 12), 29, 30100, 320, "B", None,
     "Same kWh as bill_02 but style B wording"),
    ("bill_05.pdf", "Tanya Placeholder", "FS-100005", date(2026, 8, 15), 30, 99100, 1250, "B", None,
     "Very high usage: thousands separator in kWh and amounts"),
    ("bill_06.pdf", "Omar Dummyman", "FS-100006", date(2026, 8, 20), 28, 5000, 45, "A", None,
     "Very low usage: fixed charge dominates the bill"),
    ("bill_07.pdf", "Keisha Fakename", "FS-100007", date(2026, 8, 22), 30, 21300, 410, "A", "missing_kwh",
     "kWh line missing: parser must say 'not found', not guess"),
    ("bill_08.pdf", "Andre Notreal", "FS-100008", date(2026, 8, 25), 30, 60500, 500, "B", "wrong_total",
     "Printed total is WRONG (+1,000.00): the maths checker must flag it"),
]
NOT_A_BILL = "not_a_bill.pdf"


def build_values(customer, account, start, days, prev, kwh, special):
    kwh_d = Decimal(kwh)
    energy = money(kwh_d * ENERGY_RATE)
    fuel = money(kwh_d * FUEL_RATE)
    subtotal = energy + fuel + FIXED_CHARGE
    tax = money(subtotal * TAX_RATE)
    total = subtotal + tax
    printed_total = total + Decimal("1000.00") if special == "wrong total" else total
    return {
        "customer_name": customer,
        "account_number": account,
        "billing_period_start": start.isoformat(),
        "billing_period_end": (start + timedelta(days=days)).isoformat(),
        "days": days,
        "previous_reading": prev,
        "current_reading": prev + kwh,
        "kwh_used": kwh,
        "energy_charge": float(energy),
        "fuel_charge": float(fuel),
        "fixed_charge": float(FIXED_CHARGE),
        "tax": float(tax),
        "total_due": float(printed_total),
        "correct_total": float(total),
        "math_consistent": special != "wrong_total",
        "is_bill": True,
        "tariff_name": TARIFF["name"],
    }


def draw_line(c, y, label, value, bold=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", 11)
    c.drawString(60, y, label)
    c.drawRightString(535, y, value)


def draw_bill(path, v, style, special):
    L = LABELS[style]
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4

    c.setFillColor(colors.HexColor("#1a4d8f"))
    c.rect(0, h - 90, w, 90, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h - 45, COMPANY)
    c.setFont("Helvetica", 10)
    c.drawString(50, h - 65, "ELECTRICITY BILL - FICTIONAL SAMPLE FOR TRAINING USE ONLY")
    c.setFillColor(colors.black)

    y = h - 130
    c.setFont("Helvetica", 11)
    for line in [
        f"Customer: {v['customer_name']}",
        "Address: 1 Imaginary Lane, Fictional Parish",
        f"Account Number: {v['account_number']}",
        f"Billing Period: {v['billing_period_start']} to {v['billing_period_end']}",
        f"Days in Period: {v['days']}",
    ]:
        c.drawString(60, y, line)
        y -= 16

    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "Meter Reading")
    c.line(60, y - 4, 535, y - 4)
    y -= 22
    draw_line(c, y, "Previous Reading", f"{v['previous_reading']:,}")
    y -= 18
    draw_line(c, y, "Current Reading", f"{v['current_reading']:,}")
    y -= 18
    if special != "missing_kwh":  # for this bill the kWh line is simply not printed
        draw_line(c, y, L["kwh"], f"{v['kwh_used']:,}")

    y -= 34
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, f"Charges ({CURRENCY})")
    c.line(60, y - 4, 535, y - 4)
    y -= 22
    for key, field in [("energy", "energy_charge"), ("fuel", "fuel_charge"),
                       ("fixed", "fixed_charge"), ("tax", "tax")]:
        draw_line(c, y, L[key], fmt(Decimal(str(v[field]))))
        y -= 18
    y += 10
    c.line(60, y, 535, y)
    y -= 20
    draw_line(c, y, L["total"], fmt(Decimal(str(v["total_due"]))), bold=True)

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(60, 72, f"Tariff used: {TARIFF['name']}.")
    c.drawString(60, 60, "This document is fictional. Company, customer and account do not exist.")
    c.drawString(60, 48, "Not issued by any real utility company.")
    c.showPage()
    c.save()


def draw_not_a_bill(path):
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h=A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, h - 80, "Recipe: Fictional Callaloo Soup")
    c.setFont("Helvetica", 11)
    c.drawString(60, h - 110, "Ingredients: callaloo, coconut milk, onion, thyme, pepper.")
    c.drawString(60, h - 126, "Simmer for 20 minutes. Serves 4.")
    c.showPage()
    c.save()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    answer_key = {}

    for fname, cust, acct, start, days, prev, kwh, style, special, purpose in BILLS:
        values = build_values(cust, acct, start, days, prev, kwh, special)
        draw_bill(OUT_DIR / fname, values, style, special)
        if special == "missing_kwh":
            values["kwh_used"] = None  # not printed on the PDF, so the expected parse result is None
        values["purpose"] = purpose
        values["label_style"] = style
        answer_key[fname] = values

    draw_not_a_bill(OUT_DIR / NOT_A_BILL)
    answer_key[NOT_A_BILL] = {"is_bill": False, "purpose": "Not a bill: app should reject it politely"}

    with open(OUT_DIR / "expected_values.json", "w", encoding="utf-8") as f:
        json.dump(answer_key, f, indent=2)
    print(f"Wrote {len(BILLS) + 1} PDFs and expected_values.json to {OUT_DIR}")
    print(f"Tariff: {TARIFF['name']} (fictional: {TARIFF['is_fictional']})")


if __name__ == "__main__":
    main()
