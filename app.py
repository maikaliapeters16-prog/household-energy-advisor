import pandas as pd
import plotly.express as px
import streamlit as st

import config
from modules.bill_parser import extract_text, parse_bill
from modules.calculator import (appliance_kwh, bill_breakdown, check_bill,
                                clean_appliances, household_summary, what_if)
from modules.recommender import (analyse_household, baseline_tips, recommend,
                                 top_user_summary)
from modules.tariff import load_tariff

st.set_page_config(page_title="Household Energy Advisor", layout="wide")
st.warning(config.BANNER_TEXT)


# ------------------------------------------------------------------ loading
@st.cache_data
def get_tariff():
    return load_tariff()


@st.cache_data
def get_households():
    """Sample households to start from.
    Optional in config.py:  SAMPLE_HOUSEHOLDS = {"Typical home": "data/demo/typical.csv", ...}
    Falls back to the single file in APPLIANCES_PATH."""
    options = getattr(config, "SAMPLE_HOUSEHOLDS", None) or {"Sample household": config.APPLIANCES_PATH}
    return {label: pd.read_csv(path) for label, path in options.items()}


try:
    tariff = get_tariff()
    households = get_households()
except Exception as err:
    st.error(f"Could not load the tariff or the sample data ({err}). "
             "Check the files in the data folder and the paths in config.py.")
    st.stop()

cur = tariff["currency"]
label = "FICTIONAL tariff" if tariff["is_fictional"] else "Published tariff"
st.caption(f"{label}: {tariff['name']} | Source: {tariff['source']} | Date: {tariff['date']}")

st.title("Household Energy Advisor")
st.write("Enter your appliances, see what they cost, and get advice that fits your home.")

tab_names = ["1. Energy calculator", "2. Energy advisor"]
if getattr(config, "SHOW_BILL_CHECK", False):
    tab_names.append("Bill check")
tabs = st.tabs(tab_names)
tab_calc, tab_advice = tabs[0], tabs[1]

# ------------------------------------------------------------------ 1. calculator
with tab_calc:
    st.subheader("Your appliances")

    labels = list(households)
    choice = st.selectbox("Start from a sample household", labels) if len(labels) > 1 else labels[0]
    st.caption("Edit the table, or add rows at the bottom. "
               "Enter the wattage of ONE unit (it is on the appliance label) and use Quantity for several.")

    edited = st.data_editor(
        households[choice], num_rows="dynamic", key=f"appliances_{choice}",
        column_config={
            "name": "Appliance",
            "watts": st.column_config.NumberColumn(
                "Wattage (W)", min_value=0, help="Watts of ONE unit. Use Quantity for several."),
            "hours": st.column_config.NumberColumn("Hours per day", min_value=0, max_value=24),
            "qty": st.column_config.NumberColumn("Quantity", min_value=0, default=1),
        })
    appliances, problems = clean_appliances(edited.to_dict("records"))
    for p in problems:
        st.error(p)
    if problems:
        st.caption("Rows with errors are left out of the results below.")

    if appliances:
        summary = pd.DataFrame(household_summary(appliances, tariff, config.DAYS_PER_MONTH))
        ranked = summary.sort_values("monthly_kwh", ascending=False).reset_index(drop=True)
        top_name = ranked.iloc[0]["name"]

        # Unrounded total, so it always agrees with what_if() below.
        total_kwh = sum(appliance_kwh(a["watts"], a["hours"], a["qty"], config.DAYS_PER_MONTH)[1]
                        for a in appliances)
        est = bill_breakdown(total_kwh, tariff)

        c1, c2, c3 = st.columns(3)
        c1.metric("Estimated usage per month", f"{total_kwh:,.1f} kWh")
        c2.metric(f"Estimated bill ({cur})", f"{est['total_due']:,.2f}")
        c3.metric("Biggest user", top_name)
        st.caption("Estimate = energy + fuel charges + fixed charge + tax, using the tariff above. "
                   "It is a guide, not a bill.")

        st.dataframe(
            ranked.rename(columns={
                "name": "Appliance", "daily_kwh": "kWh per day", "monthly_kwh": "kWh per month",
                "monthly_cost": f"Energy + fuel cost ({cur})"}),
            hide_index=True)
        st.caption("The cost column covers energy and fuel only. The fixed charge and tax are added "
                   "to the household total, not to each appliance.")

        left, right = st.columns(2)
        with left:
            st.plotly_chart(
                px.bar(ranked, x="name", y="monthly_kwh", title="Monthly kWh by appliance",
                       labels={"name": "Appliance", "monthly_kwh": "kWh per month"}))
        with right:
            parts = pd.DataFrame({
                "Charge": ["Energy", "Fuel", "Fixed charge", "Tax"],
                "Amount": [est["energy_charge"], est["fuel_charge"], est["fixed_charge"], est["tax"]]})
            parts = parts[parts["Amount"] > 0]

            view = st.radio("Show chart as", ["Percentage", "Amount"],
                            horizontal=True, key="bill_chart_view")

            fig = px.pie(parts, names="Charge", values="Amount", hole=0.4,
                         title=f"Where your estimated bill goes ({cur})")
            if view == "Amount":
                fig.update_traces(
                    texttemplate=f"%{{label}}<br>{cur} %{{value:,.2f}}",
                    hovertemplate=f"%{{label}}<br>{cur} %{{value:,.2f}}<extra></extra>")
            else:
                fig.update_traces(
                    texttemplate="%{label}<br>%{percent}",
                    hovertemplate="%{label}<br>%{percent}<extra></extra>")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        # ---------------------------------------------------------- what if
        st.subheader("What if...?")
        names = sorted({a["name"] for a in appliances})
        w1, w2 = st.columns(2)
        pick = w1.selectbox("Appliance", names, index=names.index(top_name))
        max_hours = max(a["hours"] for a in appliances if a["name"] == pick)

        if max_hours <= 0:
            st.info("This appliance is not used, so there is nothing to reduce.")
        else:
            less = w2.slider("Use it this many hours less per day",
                             0.0, float(max_hours), min(2.0, float(max_hours)), 0.5)
            r = what_if(appliances, pick, less, tariff, config.DAYS_PER_MONTH)
            b1, b2 = st.columns(2)
            b1.metric(f"Current bill ({cur})", f"{r['before_total']:,.2f}")
            b2.metric(f"After the change ({cur})", f"{r['after_total']:,.2f}",
                      delta=f"{-r['saving']:,.2f}", delta_color="inverse")
            st.caption(f"That is {r['before_kwh'] - r['after_kwh']:,.1f} kWh less per month.")
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

        def show_tip(t):
            st.write("- " + t["message"])
            st.caption(f"Source: {t['source']}")

        for t in tips[:4]:
            show_tip(t)
        if len(tips) > 4:
            with st.expander(f"{len(tips) - 4} more tips for your household"):
                for t in tips[4:]:
                    show_tip(t)

        with st.expander("Baseline for comparison: the same generic tips for everyone"):
            for t in baseline_tips():
                st.write("- " + t["message"])
        st.caption("This advisor is rules-based. It does not learn from data, and it cannot "
                   "see your real meter readings.")

# ------------------------------------------------------------------ optional: bill check
if getattr(config, "SHOW_BILL_CHECK", False):
    with tabs[2]:
        st.write("Upload a **fictional sample bill** (PDF). "
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
                    shown = {k: ("Not found" if v is None else v)
                             for k, v in parsed.items() if k != "is_bill"}
                    st.subheader("What I read from the bill")
                    st.table(pd.DataFrame({"Field": list(shown.keys()),
                                           "Value": [str(v) for v in shown.values()]}))

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