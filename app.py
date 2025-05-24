import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from math import pow
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="NRI Investment Analyzer", layout="centered")
st.title("🏘️ NRI Investment Analyzer")

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
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 10)

# --- Calculations ---
down_payment_amt = property_price * down_payment_pct / 100
loan_amt = property_price - down_payment_amt
monthly_interest_rate = loan_interest_rate / 12 / 100
months = loan_tenure_yrs * 12
emi = loan_amt * monthly_interest_rate * pow(1 + monthly_interest_rate, months) / (pow(1 + monthly_interest_rate, months) - 1)
emi_rounded = round(emi)

total_outflow = down_payment_amt
rent_annual = rent_monthly * 12
net_rent_annual = rent_annual - annual_maintenance
net_rent_total = net_rent_annual * horizon_years

# Estimate property value after holding period
final_property_value = property_price * pow(1 + capital_appreciation / 100, horizon_years)
total_inflow = net_rent_total + final_property_value

# Approximate interest paid
interest_paid = emi * min(horizon_years, loan_tenure_yrs) * 12 - loan_amt
net_profit = total_inflow - total_outflow - interest_paid

# IRR Calculation using cash flows
cashflows = [-down_payment_amt]
for i in range(1, horizon_years + 1):
    cashflows.append(net_rent_annual)
cashflows[-1] += final_property_value
irr = np.irr(cashflows)

# --- Output Display ---
st.subheader("📈 Investment Summary")
st.markdown(f"**Monthly EMI:** ₹{emi_rounded:,}")
st.markdown(f"**Gross Rental Yield:** {rent_annual / property_price * 100:.2f}%")
st.markdown(f"**Net Rental Yield:** {net_rent_annual / property_price * 100:.2f}%")
st.markdown(f"**Estimated Property Value after {horizon_years} years:** ₹{final_property_value:,.0f}")
st.markdown(f"**Total Net Rent Earned:** ₹{net_rent_total:,.0f}")
st.markdown(f"**Total Outflow:** ₹{(total_outflow + interest_paid):,.0f}")
st.markdown(f"**Total Inflow:** ₹{total_inflow:,.0f}")
st.markdown(f"**Net Profit:** ₹{net_profit:,.0f}")
st.markdown(f"**IRR:** {irr * 100:.2f}%")

# --- Graphs ---
st.subheader("📊 Cashflow Projection")
years = list(range(1, horizon_years + 1))
cashflow_vals = [net_rent_annual] * (horizon_years - 1) + [net_rent_annual + final_property_value]

fig, ax = plt.subplots()
ax.bar(years, cashflow_vals, color='green')
ax.set_xlabel("Year")
ax.set_ylabel("Cashflow (₹)")
ax.set_title("Annual Cashflow including Final Exit")
st.pyplot(fig)

# --- Footer ---
st.caption("Built for NRI and domestic investors to analyze residential real estate with data-driven metrics. 🧮")
