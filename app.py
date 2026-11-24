import pandas as pd
import plotly.express as px
import streamlit as st

import config
from modules.bill_parser import extract_text, parse_bill
from modules.calculator import (bill_breakdown, check_bill, clean_appliances,
                                household_summary, what_if)
from modules.recommender import (analyse_household, baseline_tips, recommend,
                                 top_user_summary)
from modules.tariff import load_tariff

st.set_page_config(page_title="Household Energy Advisor", layout="wide")
st.warning(config.BANNER_TEXT)

tariff = load_tariff()
cur = tariff["currency"]
label = "FICTIONAL tariff" if tariff["is_fictional"] else "Published tariff"
st.caption(f"{label}: {tariff['name']} | Source: {tariff['source']} | Date: {tariff['date']}")

st.title("Household Energy Advisor")
st.write("Simple inputs → useful estimates → actionable advice")

tab_calc, tab_advice, tab_bill = st.tabs(
    ["1. Energy calculator", "2. AI energy advisor", "Bill check (optional, later)"])

# ------------------------------------------------------------------ 1. calculator
with tab_calc:
    st.subheader("Your appliances")
    st.caption("Edit the table, or add rows at the bottom. Wattage is on the appliance label.")
    start = pd.read_csv(config.APPLIANCES_PATH)  # name, watts, hours, qty
    edited = st.data_editor(
        start, num_rows="dynamic", use_container_width=True,
        column_config={
            "name": "Appliance",
            "watts": st.column_config.NumberColumn("Wattage (W)", min_value=0),
            "hours": st.column_config.NumberColumn("Hours per day", min_value=0, max_value=24),
            "qty": st.column_config.NumberColumn("Quantity", min_value=0, default=1),
        })
    appliances, problems = clean_appliances(edited.to_dict("records"))
    for p in problems:
        st.error(p)

    if appliances:
        summary = pd.DataFrame(household_summary(appliances, tariff, config.DAYS_PER_MONTH))
        total_kwh = summary.monthly_kwh.sum()
        est = bill_breakdown(total_kwh, tariff)

        c1, c2, c3 = st.columns(3)
        c1.metric("Estimated usage per month", f"{total_kwh:,.1f} kWh")
        c2.metric(f"Estimated bill ({cur})", f"{est['total_due']:,.2f}")
        c3.metric("Biggest user", summary.sort_values("monthly_kwh").iloc[-1]["name"])
        st.caption("Estimate = energy + fuel charges + fixed charge + tax, using the tariff above. "
                   "It is a guide, not a bill.")

        st.dataframe(summary.sort_values("monthly_kwh", ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(summary.sort_values("monthly_kwh", ascending=False),
                               x="name", y="monthly_kwh", title="Monthly kWh by appliance"),
                        use_container_width=True)

        st.subheader("What if...?")
        names = sorted({a["name"] for a in appliances})
        w1, w2 = st.columns(2)
        pick = w1.selectbox("Appliance", names)
        less = w2.slider("Use it this many hours less per day", 0.0, 12.0, 2.0, 0.5)
        r = what_if(appliances, pick, less, tariff, config.DAYS_PER_MONTH)
        st.metric(f"Estimated monthly bill ({cur})", f"{r['after_total']:,.2f}",
                  delta=f"{-r['saving']:,.2f}", delta_color="inverse")
    else:
        st.info("Add at least one appliance to see your estimate.")

# ------------------------------------------------------------------ 2. advisor
with tab_advice:
    if not appliances:
        st.info("Enter your appliances on the first tab.")
    else:
        analysis = analyse_household(appliances, tariff, config.DAYS_PER_MONTH)
        st.subheader("Analysis")
        st.write(top_user_summary(analysis))

        st.subheader("Recommended for your household")
        tips = recommend(analysis)
        if not tips:
            st.success("Nothing stands out. Your usage pattern does not trigger any of our tips.")
        for t in tips:
            st.write("- " + t["message"])
            st.caption(f"Source: {t['source']}")

        with st.expander("Baseline for comparison: the same generic tips for everyone"):
            for t in baseline_tips():
                st.write("- " + t["message"])
        st.caption("This advisor is rules-based. It does not learn from data, and it cannot "
                   "see your real meter readings.")

# ------------------------------------------------------------------ optional: bill check
with tab_bill:
    st.write("**Optional, planned for a later version.** Upload a **fictional sample bill** (PDF). "
             "It is read on this computer and not stored.")
    pdf = st.file_uploader("Bill PDF", type=["pdf"])
    if pdf:
        try:
            text = extract_text(pdf)
        except Exception:
            text = ""
        if not text.strip():
            st.error("Could not read any text from this PDF. Scanned PDFs are not supported.")
        else:
            parsed = parse_bill(text)
            if not parsed["is_bill"]:
                st.warning("This does not look like an electricity bill, so I can't explain it.")
            else:
                shown = {k: ("Not found" if v is None else v) for k, v in parsed.items() if k != "is_bill"}
                st.subheader("What I read from the bill")
                st.table(pd.DataFrame({"Field": shown.keys(), "Value": [str(v) for v in shown.values()]}))

                result = check_bill(parsed, tariff)
                st.subheader("Does the bill match the tariff?")
                if result["ok"] is None:
                    st.info(result["issues"][0])
                elif result["ok"]:
                    st.success(f"All charges match the tariff (kWh {result['kwh_source']}).")
                else:
                    st.error("Some amounts do not match the loaded tariff:")
                    for issue in result["issues"]:
                        st.write("- " + issue)