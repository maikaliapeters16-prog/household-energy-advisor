"""
Compares the rules-based recommender with the generic-tips baseline on the test households.

Precision: of the tips shown, how many were expected for that household.
Recall:    of the tips expected, how many were shown.

Run: python evaluate_recommender.py
"""
import json

import config
from modules.recommender import BASELINE_TIP_IDS, analyse_household, recommend
from modules.tariff import load_tariff


def score(shown, expected):
    shown, expected = set(shown), set(expected)
    hit = len(shown & expected)
    precision = hit / len(shown) if shown else 1.0
    recall = hit / len(expected) if expected else 1.0
    return precision, recall


def main():
    tariff = load_tariff()
    with open(config.TEST_HOUSEHOLDS_PATH, encoding="utf-8") as f:
        households = json.load(f)["households"]

    totals = {"rules": [0, 0], "baseline": [0, 0]}
    exact = 0
    print(f"{'ID':<5}{'rules P':>8}{'rules R':>9}{'base P':>8}{'base R':>8}   notes")
    for h in households:
        analysis = analyse_household(h["appliances"], tariff, config.DAYS_PER_MONTH)
        rules_ids = [t["id"] for t in recommend(analysis)]
        rp, rr = score(rules_ids, h["expected_tips"])
        bp, br = score(BASELINE_TIP_IDS, h["expected_tips"])
        totals["rules"][0] += rp; totals["rules"][1] += rr
        totals["baseline"][0] += bp; totals["baseline"][1] += br
        note = ""
        if set(rules_ids) == set(h["expected_tips"]):
            exact += 1
        else:
            extra = sorted(set(rules_ids) - set(h["expected_tips"]))
            missing = sorted(set(h["expected_tips"]) - set(rules_ids))
            note = f"extra: {extra}  missing: {missing}"
        print(f"{h['id']:<5}{rp:>8.2f}{rr:>9.2f}{bp:>8.2f}{br:>8.2f}   {note}")

    n = len(households)
    print(f"\nAverage over {n} households")
    print(f"  Rules    precision {totals['rules'][0]/n:.2f}   recall {totals['rules'][1]/n:.2f}")
    print(f"  Baseline precision {totals['baseline'][0]/n:.2f}   recall {totals['baseline'][1]/n:.2f}")
    print(f"  Households where the rules matched the expected tips exactly: {exact} of {n}")


if __name__ == "__main__":
    main()