import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import numpy_financial as npf
from numpy_financial import irr

st.set_page_config(page_title="NRI Investment Analyzer", layout="wide")
st.title("🏘️ NRI Investment Analyzer - Real Estate")

st.sidebar.header("Property & Loan Details")

# --- Input Section ---
property_value = st.sidebar.number_input("Property Value (₹)", value=8500000, step=50000)
equity_contribution = st.sidebar.number_input("Equity Contribution (₹)", value=5000000, step=50000)
loan_amount = property_value - equity_contribution
interest_rate = st.sidebar.number_input("Loan Interest Rate (%)", value=8.6) / 100
loan_tenure_years = st.sidebar.number_input("Loan Tenure (years)", value=20)

st.sidebar.markdown("---")

# Custom Payment Plan
st.sidebar.subheader("Under-Construction Payment Plan")
payment_plan = []
payment_tranches = st.sidebar.number_input("Number of Payment Tranches", value=4, min_value=1, max_value=10)

for i in range(payment_tranches):
    col1, col2 = st.sidebar.columns(2)
    with col1:
        percent = st.number_input(f"Tranche {i+1} (%)", min_value=0.0, max_value=100.0, value=25.0, key=f"p_{i}")
    with col2:
        month = st.number_input(f"Month {i+1}", min_value=0, max_value=240, value=i * 6, key=f"m_{i}")
    payment_plan.append({"month": month, "percent": percent})

completion_month = st.sidebar.number_input("Construction Completion (Month)", value=24)
rent_start = completion_month
monthly_rent = st.sidebar.number_input("Expected Monthly Rent after Possession (₹)", value=24000)
rent_growth = st.sidebar.number_input("Annual Rent Growth Rate (%)", value=5.0) / 100

sale_price = st.sidebar.number_input("Expected Sale Price (₹)", value=11000000)
sale_month = st.sidebar.number_input("Expected Sale Month", value=120)

# --- Backend Calculations ---
horizon_months = max(sale_month, max([p["month"] for p in payment_plan]) + 12)
cashflow = np.zeros(horizon_months + 1)

# Equity Payments
for tranche in payment_plan:
    amount = (tranche["percent"] / 100) * property_value
    cashflow[tranche["month"]] -= amount

# Loan Disbursements aligned to payment tranches (if equity insufficient)
emi_schedule = []
remaining_equity = equity_contribution
for tranche in payment_plan:
    amount = (tranche["percent"] / 100) * property_value
    if remaining_equity >= amount:
        remaining_equity -= amount
    else:
        loan_part = amount - remaining_equity
        remaining_equity = 0
        disbursement_month = tranche["month"]
        emi = npf.pmt(interest_rate / 12, loan_tenure_years * 12, -loan_part)
        emi_schedule.append({"month": disbursement_month, "emi": emi, "principal": loan_part})

# Add EMIs to cashflow
for emi_entry in emi_schedule:
    start = emi_entry["month"] + 1
    for m in range(start, start + loan_tenure_years * 12):
        if m >= len(cashflow):
            break
        cashflow[m] -= emi_entry["emi"]

# Add Rent from completion
for m in range(rent_start, len(cashflow)):
    year_index = (m - rent_start) // 12
    rent = monthly_rent * ((1 + rent_growth) ** year_index)
    cashflow[m] += rent

# Sale inflow
if sale_month < len(cashflow):
    cashflow[sale_month] += sale_price

# IRR
investment_irr = irr(cashflow)

# --- Summary Metrics ---

st.subheader("📈 Investment Summary")
total_outflow = -sum([cf for cf in cashflow if cf < 0])
total_inflow = sum([cf for cf in cashflow if cf > 0])
total_profit = total_inflow - total_outflow
interest_paid = sum([e["emi"] * loan_tenure_years * 12 for e in emi_schedule]) - sum([e["principal"] for e in emi_schedule])
final_property_value = sale_price
net_rent_total = sum([cf for cf in cashflow if cf > 0 and cf != sale_price])
horizon_years = horizon_months // 12

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Investment (₹)", f"{total_outflow:,.0f}")
col2.metric("Total Profit (₹)", f"{total_profit:,.0f}")
col3.metric("Gross Return (%)", f"{(total_profit / total_outflow * 100):.2f}")
col4.metric("Holding Period (years)", f"{horizon_years}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Total Interest Paid (₹)", f"{interest_paid:,.0f}")
col6.metric("Final Property Value (₹)", f"{final_property_value:,.0f}")
col7.metric("Net Rent Income (₹)", f"{net_rent_total:,.0f}")
col8.metric("IRR (%)", f"{investment_irr * 100:.2f}" if investment_irr is not None else "N/A")

# --- Plotly Visualization ---
st.subheader("📊 Cashflow Overview")
annual_cashflows = [sum(cashflow[i:i+12]) for i in range(0, len(cashflow), 12)]
annual_years = list(range(len(annual_cashflows)))
fig = go.Figure()
fig.add_trace(go.Bar(name="Annual Net Rent", x=annual_years, y=[max(cf, 0) for cf in annual_cashflows]))
fig.add_trace(go.Bar(name="Annual Outflows (EMI+Payments)", x=annual_years, y=[-min(cf, 0) for cf in annual_cashflows]))
fig.update_layout(barmode='relative', xaxis_title="Year", yaxis_title="Net Cashflow (₹)")
st.plotly_chart(fig, use_container_width=True)
