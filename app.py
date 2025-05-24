# Full Streamlit App Code: Real Estate Investment Analyzer with Enhanced Metrics

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide", page_title="NRI Investment Analyzer")
st.title("🏘️ NRI Real Estate Investment Analyzer")

# --- Input Section ---
st.sidebar.header("🛠️ Property & Loan Configuration")

# Property inputs
property_price = st.sidebar.number_input("Property Price (₹)", value=8500000, step=500000)
rent_monthly = st.sidebar.number_input("Expected Monthly Rent (₹)", value=24000, step=1000)
rent_escalation = st.sidebar.slider("Annual Rent Escalation (%)", 0.0, 10.0, 5.0)
prop_appreciation = st.sidebar.slider("Annual Property Appreciation (%)", 0.0, 12.0, 6.0)
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 20, 10)

# Loan inputs
st.sidebar.markdown("---")
loan_amt = st.sidebar.number_input("Loan Amount (₹)", value=3000000, step=100000)
loan_interest_rate = st.sidebar.slider("Loan Interest Rate (%)", 5.0, 12.0, 8.6)
loan_tenure_yrs = st.sidebar.slider("Loan Tenure (Years)", 1, 30, 20)

# Amortization view
amortization_view = st.sidebar.radio("Amortization View", ["Annual", "Monthly"], index=0)

# Payment Plan Details
st.sidebar.markdown("---")
st.sidebar.markdown("### Payment Plan Details")
custom_schedule = st.sidebar.checkbox("Specify Custom Payment Schedule")

payment_plan = []
if custom_schedule:
    num_tranches = st.sidebar.number_input("Number of Tranches", min_value=1, max_value=10, value=4)
    for i in range(num_tranches):
        pct = st.sidebar.number_input(f"Tranche {i+1} (% of Price)", min_value=1, max_value=100, value=25, key=f"pct_{i}")
        timing = st.sidebar.number_input(f"Timing (months from now)", min_value=0, max_value=loan_tenure_yrs*12, value=i*6, key=f"time_{i}")
        payment_plan.append((pct, timing))
else:
    payment_plan = [(10, 0), (20, 1), (30, 9), (40, 36)]

# --- Calculations ---

# EMI calculation
def calculate_emi(P, R, N):
    r = R / (12 * 100)
    emi = P * r * ((1 + r) ** N) / (((1 + r) ** N) - 1)
    return emi

emi = calculate_emi(loan_amt, loan_interest_rate, loan_tenure_yrs * 12)
emi_rounded = round(emi)

# Rent and appreciation calculations
net_rent_annual = 0
net_rent_total = 0
rent_annual = rent_monthly * 12
cashflows = [-property_price]

for year in range(1, horizon_years + 1):
    rent = rent_annual * ((1 + rent_escalation / 100) ** (year - 1))
    net_rent_annual += rent
    net_rent_total += rent
    cashflows.append(rent)

# Property appreciation
final_property_value = property_price * ((1 + prop_appreciation / 100) ** horizon_years)

# Total Outflow (Custom Payment Plan)
payment_amounts = []
total_outflow = 0

for pct, months in payment_plan:
    amt = (pct / 100) * property_price
    total_outflow += amt
    payment_amounts.append((months, amt))

payment_amounts.sort()

# Interest paid on loan
interest_paid = (emi * loan_tenure_yrs * 12) - loan_amt
net_profit = (final_property_value + net_rent_total) - (total_outflow + interest_paid)

# IRR calculation
def xirr(cashflows, dates):
    from scipy.optimize import newton

    def npv(rate):
        return sum([cf / ((1 + rate) ** ((d - dates[0]).days / 365.0)) for cf, d in zip(cashflows, dates)])

    try:
        return newton(npv, 0.1)
    except:
        return 0.0

irr_dates = [datetime.today().replace(day=1)]
for y in range(1, horizon_years + 1):
    irr_dates.append(datetime.today().replace(year=datetime.today().year + y))

irr = xirr(cashflows + [final_property_value], irr_dates)

# ROI
roi = (net_profit / (total_outflow + interest_paid)) * 100

# --- UI Output ---

# --- Investment Summary with ROI ---
st.subheader("📈 Investment Summary")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Monthly EMI (₹)", f"{emi_rounded:,}")
col2.metric("Gross Rental Yield (%)", f"{rent_annual / property_price * 100:.2f}")
col3.metric("Net Rental Yield (%)", f"{net_rent_annual / property_price * 100:.2f}")
col4.metric("Investment Horizon (yrs)", f"{horizon_years}")
col5.metric("ROI (%)", f"{roi:.2f}")

col6, col7, col8, col9 = st.columns(4)
col6.metric("Estimated Property Value (₹)", f"{final_property_value:,.0f}")
col7.metric("Total Net Rent Earned (₹)", f"{net_rent_total:,.0f}")
col8.metric("Total Outflow (₹)", f"{(total_outflow + interest_paid):,.0f}")
col9.metric("Net Profit (₹)", f"{net_profit:,.0f}")

st.markdown(f"**Internal Rate of Return (IRR):** {irr * 100:.2f}%")

# --- Loan Amortization Section ---
st.subheader("💰 Loan Amortization Schedule")

def amortization_schedule(P, R, tenure_yrs, view):
    r = R / 12 / 100
    N = tenure_yrs * 12
    emi = calculate_emi(P, R, N)

    schedule = []
    balance = P

    for m in range(1, N + 1):
        interest = balance * r
        principal = emi - interest
        balance -= principal
        if view == "Monthly" or (view == "Annual" and m % 12 == 0):
            period = m if view == "Monthly" else m // 12
            year_interest = interest * 12 if view == "Annual" else interest
            year_principal = principal * 12 if view == "Annual" else principal
            schedule.append([period, year_interest, year_principal, balance])

    return pd.DataFrame(schedule, columns=["Period", "Interest Paid", "Principal Paid", "Balance"])

amort_df = amortization_schedule(loan_amt, loan_interest_rate, loan_tenure_yrs, amortization_view)

st.dataframe(amort_df.style.format({
    "Interest Paid": "₹{:.2f}",
    "Principal Paid": "₹{:.2f}",
    "Balance": "₹{:.2f}"
}), use_container_width=True)

# --- Interest vs Principal Graph ---
st.subheader("📉 Interest vs Principal Components Over Time")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=amort_df["Period"], y=amort_df["Interest Paid"], name="Interest Paid", line=dict(color="red")))
fig2.add_trace(go.Scatter(x=amort_df["Period"], y=amort_df["Principal Paid"], name="Principal Paid", line=dict(color="green")))
fig2.update_layout(xaxis_title="Period", yaxis_title="Amount (₹)", height=400, template="plotly_white")
st.plotly_chart(fig2, use_container_width=True)
