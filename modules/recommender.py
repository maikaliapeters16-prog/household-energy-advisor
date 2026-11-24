"""
The rules-based recommendation engine (the "AI component" of the MVP).

INPUT      the appliance list (name, watts, hours per day, quantity)
ANALYSE    work out each appliance's kWh and its share of the household's usage
RECOMMEND  show the tips whose rules match THIS household

BASELINE   a fixed list of generic tips that is shown to everybody (BASELINE_TIP_IDS).

Every threshold below is a design decision made by the group. Document each one
in docs/data_notes.md, and do not claim they come from a published source unless they do.
Every tip needs a real public source in its "source" field before the symposium.
"""
import re

from modules.calculator import household_summary

# ---- Thresholds (group decisions: review and justify each one) ----
AC_HOURS = 6              # air conditioner used this many hours a day or more
AC_SHARE = 0.30           # air conditioner is this share of estimated usage or more
FRIDGE_SHARE = 0.15       # a fridge or freezer is this share of usage or more
LIGHT_HOURS = 6           # lights on this many hours a day or more
BULB_WATTS = 40           # one bulb at this wattage or more is probably not an LED
FAN_HOURS = 10            # a fan runs this many hours a day or more
HIGH_TOTAL_KWH = 400      # estimated monthly usage at or above this counts as high

SOURCE_TODO = "SOURCE NEEDED: add the public guide's title, organisation and date"

CATEGORY_KEYWORDS = {   # checked in this order; the first match wins
    "water_heater": r"\b(water\s*heater|shower\s*heater|geyser)\b",
    "ac": r"\b(air\s*condition\w*|a/?c|aircon)\b",
    "fridge": r"\b(fridge|refrigerator|freezer)\b",
    "fan": r"\bfans?\b",
    "light": r"\b(bulbs?|lights?|lamps?|lighting|led|cfl)\b",
    "dryer": r"\bdryer\b",
    "entertainment": r"\b(tv|television|console|playstation|xbox|stereo|speakers?)\b",
    "computer": r"\b(laptop|computer|desktop|pc|monitor)\b",
}


def categorise(name):
    for category, pattern in CATEGORY_KEYWORDS.items():
        if re.search(pattern, name.lower()):
            return category
    return "other"


def analyse_household(appliances, tariff, days=30):
    """appliances: cleaned list of dicts (name, watts, hours, qty)."""
    rows = household_summary(appliances, tariff, days)
    total = sum(r["monthly_kwh"] for r in rows)
    items = []
    for a, r in zip(appliances, rows):
        items.append({**r, "category": categorise(a["name"]), "watts": a["watts"],
                      "hours": a["hours"], "qty": a["qty"],
                      "share": r["monthly_kwh"] / total if total else 0})
    top = max(items, key=lambda i: i["monthly_kwh"]) if items else None
    return {"items": items, "total_kwh": round(total, 2), "top": top}


def _of(analysis, *categories):
    return [i for i in analysis["items"] if i["category"] in categories]


def _ac_hours(a):
    return max((i for i in _of(a, "ac") if i["hours"] >= AC_HOURS), key=lambda i: i["hours"], default=None)


def _top_three(a):
    ranked = sorted(a["items"], key=lambda i: i["monthly_kwh"], reverse=True)[:3]
    return ", ".join(i["name"].lower() for i in ranked)


TIPS = [
    {"id": "ac_hours",
     "applies": lambda a: _ac_hours(a) is not None,
     "message": lambda a: (f"Your air conditioner is used for {_ac_hours(a)['hours']:g} hours daily. "
                           "Try reducing usage where practical or adjusting the temperature setting. "
                           "This may help lower energy consumption."),
     "source": SOURCE_TODO},
    {"id": "ac_share",
     "applies": lambda a: any(i["share"] >= AC_SHARE for i in _of(a, "ac")),
     "message": lambda a: ("Your air conditioner accounts for a large share of your estimated usage "
                           f"({max(i['share'] for i in _of(a, 'ac')):.0%}). Even a small change in how "
                           "it is used will show up in your bill."),
     "source": SOURCE_TODO},
    {"id": "fridge_care",
     "applies": lambda a: any(i["share"] >= FRIDGE_SHARE for i in _of(a, "fridge")),
     "message": lambda a: ("Your fridge or freezer runs all day, so it is a steady part of your usage. "
                           "Keep the door seals clean and tight, avoid leaving the door open, and keep "
                           "it away from heat sources."),
     "source": SOURCE_TODO},
    {"id": "led_switch",
     "applies": lambda a: any(i["watts"] >= BULB_WATTS for i in _of(a, "light")),
     "message": lambda a: ("One of your bulbs uses a high wattage. LED bulbs use less power for similar "
                           "light, so replacing older bulbs is a simple saving."),
     "source": SOURCE_TODO},
    {"id": "lighting_hours",
     "applies": lambda a: any(i["hours"] >= LIGHT_HOURS for i in _of(a, "light")),
     "message": lambda a: "Your lights are on for many hours a day. Switch them off in rooms nobody is using.",
     "source": SOURCE_TODO},
    {"id": "water_heater",
     "applies": lambda a: any(i["hours"] > 0 for i in _of(a, "water_heater")),
     "message": lambda a: ("Water heating uses a lot of power while it is on. Shorter showers and "
                           "switching the heater off when it is not needed can help."),
     "source": SOURCE_TODO},
    {"id": "standby_electronics",
     "applies": lambda a: bool(_of(a, "entertainment", "computer")),
     "message": lambda a: ("TVs, consoles and computers can keep drawing power on standby. Switch them "
                           "off fully, or use a power strip, when they are not in use."),
     "source": SOURCE_TODO},
    {"id": "dryer_alternative",
     "applies": lambda a: any(i["hours"] > 0 for i in _of(a, "dryer")),
     "message": lambda a: "Clothes dryers use a lot of power. Line-drying when the weather allows avoids that.",
     "source": SOURCE_TODO},
    {"id": "fan_off_when_empty",
     "applies": lambda a: any(i["hours"] >= FAN_HOURS for i in _of(a, "fan")),
     "message": lambda a: ("Fans cool people, not rooms. Switch them off when nobody is in the room."),
     "source": SOURCE_TODO},
    {"id": "high_total",
     "applies": lambda a: a["total_kwh"] >= HIGH_TOTAL_KWH,
     "message": lambda a: (f"Your estimated usage is high ({a['total_kwh']:,.0f} kWh a month). "
                           f"Start with your biggest users: {_top_three(a)}."),
     "source": SOURCE_TODO},
]

# The baseline: the same generic tips for every household.
BASELINE_TIP_IDS = ["led_switch", "standby_electronics", "fan_off_when_empty", "fridge_care"]


def recommend(analysis):
    """Tips whose rules match this household."""
    return [{"id": t["id"], "message": t["message"](analysis), "source": t["source"]}
            for t in TIPS if t["applies"](analysis)]


def top_user_summary(analysis):
    top = analysis["top"]
    if not top:
        return None
    return f"Biggest user: {top['name']} ({top['share']:.0%} of your estimated usage)."


def baseline_tips():
    by_id = {t["id"]: t for t in TIPS}
    generic = {"led_switch": "Replace older bulbs with LED bulbs.",
               "standby_electronics": "Switch off electronics instead of leaving them on standby.",
               "fan_off_when_empty": "Switch off fans in empty rooms.",
               "fridge_care": "Keep fridge door seals clean and avoid leaving the door open."}
    return [{"id": i, "message": generic[i], "source": by_id[i]["source"]} for i in BASELINE_TIP_IDS]