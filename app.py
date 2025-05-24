import numpy as np
import pandas as pd
from math import pow
import streamlit as st
import plotly.graph_objects as go
import numpy_financial as npf
from dateutil.relativedelta import relativedelta
from datetime import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="Real Estate Investment Analyzer", layout="centered")
st.title("🏨 Real Estate Investment Analyzer")

st.markdown("""
This tool helps you analyze residential property investments — for both ready-to-move and under-construction projects.
""")

# --- Inputs ---
st.sidebar.header("Property Details")
property_type = st.sidebar.selectbox("Property Type", ["Ready-to-move", "Under-construction"])
property_price = st.sidebar.number_input("Property Price (₹)", value=8000000, step=50000)
down_payment_pct = st.sidebar.slider("Down Payment (%)", 10, 100, 30)
loan_interest_rate = st.sidebar.number_input("Loan Interest Rate (%)", value=8.5)
loan_tenure_yrs = st.sidebar.slider("Loan Tenure (years)", 5, 30, 20)
rent_monthly = st.sidebar.number_input("Expected Monthly Rent (₹)", value=25000, step=1000)
annual_maintenance = st.sidebar.number_input("Annual Maintenance & Tax (₹)", value=30000)
capital_appreciation = st.sidebar.slider("Expected Capital Appreciation (CAGR %)", 0, 15, 6)
rental_growth = st.sidebar.slider("Expected Rental Growth (CAGR %)", 0, 15, 3)
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 10)

# Additional fields for under-construction properties
if property_type == "Under-construction":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Under-construction Settings")
    construction_years = st.sidebar.slider("Construction Period (Years)", 0, horizon_years, 2)

    # Allow user to input custom payment schedule and timing
    st.sidebar.markdown("### Payment Schedule Setup")
    default_schedule = "10,20,30,40"
    payment_schedule_str = st.sidebar.text_input(
        "Enter Payment % splits (comma separated)", default_schedule
    )

    # Parse the percentages and validate sum to 100%
    try:
        payment_splits = [float(x.strip()) for x in payment_schedule_str.split(",")]
    except:
        st.sidebar.error("Invalid payment split input. Use comma-separated numbers.")

    if abs(sum(payment_splits) - 100) > 0.01:
        st.sidebar.warning("Payment splits should sum to 100%. Please adjust.")

    # Timing input (in months) for each tranche
    timing_default = [0, 6, 18, 36]  # example defaults (months)
    payment_timing_str = st.sidebar.text_input(
        "Enter payment timings in months (comma separated)", ",".join(str(x) for x in timing_default[:len(payment_splits)])
    )

    try:
        payment_timing = [int(x.strip()) for x in payment_timing_str.split(",")]
    except:
        st.sidebar.error("Invalid payment timing input. Use comma-separated integers (months).")

    if len(payment_timing) != len(payment_splits):
        st.sidebar.warning("Number of timings must equal number of payment splits.")

else:
    construction_years = 0
    payment_splits = [100]
    payment_timing = [0]

# --- Calculations ---
down_payment_amt = property_price * down_payment_pct / 100
loan_amt = property_price - down_payment_amt
monthly_interest_rate = loan_interest_rate / 12 / 100
months = loan_tenure_yrs * 12

# EMI calculation
emi = npf.pmt(monthly_interest_rate, months, -loan_amt)
emi_rounded = round(emi)

# Disbursement logic: use user payment_splits and payment_timing if under construction
if property_type == "Under-construction":
    disbursement_schedule = []
    for pct, month in zip(payment_splits, payment_timing):
        disbursement_schedule.append((month / 12, loan_amt * (pct / 100)))  # convert months to years for timeline
else:
    disbursement_schedule = []

# Adjust cashflows and outflows
total_outflow = down_payment_amt
rent_annual = rent_monthly * 12
net_rent_annual = rent_annual - annual_maintenance

# Calculate rent with growth each year
net_rent_vals = []
current_rent = net_rent_annual
for i in range(horizon_years):
    if property_type == "Under-construction" and i < construction_years:
        net_rent_vals.append(0)  # no rent during construction
    else:
        net_rent_vals.append(current_rent)
        current_rent *= (1 + rental_growth / 100)

net_rent_total = sum(net_rent_vals)

# Estimate property value after holding period (year-wise)
property_vals = [property_price * pow(1 + capital_appreciation / 100, i + 1) for i in range(horizon_years)]
final_property_value = property_vals[-1]

total_inflow = net_rent_total + final_property_value

# Approximate interest paid (for holding period or loan tenure, whichever is smaller)
interest_paid = emi * min(horizon_years, loan_tenure_yrs) * 12 - loan_amt
net_profit = total_inflow - total_outflow - interest_paid

# IRR Calculation using cash flows
cashflows = [-down_payment_amt]
for rent in net_rent_vals[:-1]:
    cashflows.append(rent)
cashflows.append(net_rent_vals[-1] + final_property_value)
irr = npf.irr(cashflows)

# --- Enhanced Dashboard Output ---

st.subheader("📈 Investment Summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Monthly EMI (₹)", f"{emi_rounded:,}")
col2.metric("Gross Rental Yield (%)", f"{rent_annual / property_price * 100:.2f}")
col3.metric("Net Rental Yield (%)", f"{net_rent_annual / property_price * 100:.2f}")
col4.metric(f"Investment Horizon (yrs)", f"{horizon_years}")

col5, col6, col7, col8 = st.columns(4)

col5.metric(f"Estimated Property Value (₹)", f"{final_property_value:,.0f}")
col6.metric(f"Total Net Rent Earned (₹)", f"{net_rent_total:,.0f}")
col7.metric(f"Total Outflow (₹)", f"{(total_outflow + interest_paid):,.0f}")
col8.metric(f"Net Profit (₹)", f"{net_profit:,.0f}")

st.markdown(f"**Internal Rate of Return (IRR):** {irr * 100:.2f}%")

# --- Interactive Graph with Plotly ---

years = list(range(1, horizon_years + 1))

fig = go.Figure()

fig.add_trace(go.Bar(
    x=years,
    y=net_rent_vals,
    name="Net Rent (Annual ₹)",
    marker_color='green',
    yaxis="y2",
    hovertemplate="Year %{x}: ₹%{y:,.0f}<extra></extra>"
))

fig.add_trace(go.Scatter(
    x=years,
    y=property_vals,
    mode='lines+markers',
    name='Estimated Property Value (₹)',
    line=dict(color='white', width=3),
    hovertemplate="Year %{x}: ₹%{y:,.0f}<extra></extra>"
))

fig.update_layout(
    title="Investment Cashflow & Property Value Over Time",
    xaxis_title="Year",
    yaxis=dict(
        title="Property Value & Disbursements (₹)",
        tickfont=dict(color='white'),
        side='left',
        showgrid=False
    ),
    yaxis2=dict(
        title="Net Rent (₹)",
        tickfont=dict(color='green'),
        overlaying='y',
        side='right',
        showgrid=False,
        range=[min(net_rent_vals)*0.9, max(net_rent_vals)*1.25]
    ),
    barmode='group',
    hovermode='x unified',
    height=450,
    legend=dict(y=0.95, x=0.01),
    template="plotly_white"
)

st.subheader("📊 Cashflow Projection")
st.plotly_chart(fig, use_container_width=True)

# --- Cashflow Table ---

st.subheader("🧾 Annual Cashflow Table")
cashflow_table = pd.DataFrame({
    "Year": years,
    "Net Rent (₹)": net_rent_vals,
    "Property Value (₹)": property_vals
})
st.dataframe(
    cashflow_table.style.format({"Net Rent (₹)": "₹{:.0f}", "Property Value (₹)": "₹{:.0f}"}),
    use_container_width=True
)

# --- Loan Amortization Schedule (Annual/Monthly toggle) ---
st.subheader("💰 Loan Amortization Schedule")

amortization_view = st.radio("View Amortization Schedule By:", ["Annual", "Monthly"])

def amortization_schedule(principal, annual_rate, years, view):
    monthly_rate = annual_rate / 12 / 100
    n_months = years * 12
    balance = principal

    records = []

    for month in range(1, n_months + 1):
        interest = balance * monthly_rate
        payment = npf.pmt(monthly_rate, n_months - month + 1, -balance)
        principal_paid = payment - interest
        balance -= principal_paid
        balance = max(balance, 0)

        records.append({
            "Month": month,
            "Interest Paid": interest,
            "Principal Paid": principal_paid,
            "Balance": balance
        })

    if view == "Monthly":
        df = pd.DataFrame(records)
        df.rename(columns={"Month": "Period"}, inplace=True)
        return df

    else:  # Annual aggregation
        # Aggregate monthly into years
        df = pd.DataFrame(records)
        df["Year"] = ((df["Month"] - 1) // 12) + 1
        df_annual = df.groupby("Year").agg({
            "Interest Paid": "sum",
            "Principal Paid": "sum",
            "Balance": "last"
        }).reset_index()
        df_annual.rename(columns={"Year": "Period"}, inplace=True)
        return df_annual

amort_df = amortization_schedule(loan_amt, loan_interest_rate, loan_tenure_yrs, amortization_view)
amort_df[["Interest Paid", "Principal Paid", "Balance"]] = amort_df[["Interest Paid", "Principal Paid", "Balance"]].round(2)

st.dataframe(amort_df.style.format({
    "Interest Paid": "₹{:.2f}",
    "Principal Paid": "₹{:.2f}",
    "Balance": "₹{:.2f}"
}), use_container_width=True)

# --- Interest vs Principal Line Graph ---
st.subheader("📉 Interest vs Principal Over Time")

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=amort_df["Period"],
    y=amort_df["Interest Paid"],
    mode='lines+markers',
    name="Interest Paid",
    line=dict(color='red', width=2),
    hovertemplate="Period %{x}: ₹%{y:,.0f}<extra></extra>"
))

fig2.add_trace(go.Scatter(
    x=amort_df["Period"],
    y=amort_df["Principal Paid"],
    mode='lines+markers',
    name="Principal Paid",
    line=dict(color='blue', width=2),
    hovertemplate="Period %{x}: ₹%{y:,.0f}<extra></extra>"
))

fig2.update_layout(
    title="Loan Repayment Breakdown Over Time",
    xaxis_title="Period",
    yaxis_title="Amount (₹)",
    hovermode='x unified',
    template="plotly_white",
    height=450,
    legend=dict(y=0.95, x=0.01)
)

st.plotly_chart(fig2, use_container_width=True)
