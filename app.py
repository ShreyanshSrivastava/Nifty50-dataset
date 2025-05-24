import streamlit as st
import numpy as np
import pandas as pd
from math import pow
import plotly.graph_objects as go
import numpy_financial as npf

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
rental_growth = st.sidebar.slider("Expected Rental Growth (CAGR %)", 0, 15, 3)
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 10)

# --- Calculations ---
down_payment_amt = property_price * down_payment_pct / 100
loan_amt = property_price - down_payment_amt
monthly_interest_rate = loan_interest_rate / 12 / 100
months = loan_tenure_yrs * 12

# EMI calculation
emi = loan_amt * monthly_interest_rate * pow(1 + monthly_interest_rate, months) / (pow(1 + monthly_interest_rate, months) - 1)
emi_rounded = round(emi)

total_outflow = down_payment_amt
rent_annual = rent_monthly * 12
net_rent_annual = rent_annual - annual_maintenance

# Calculate rent with growth each year
net_rent_vals = []
current_rent = net_rent_annual
for i in range(horizon_years):
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
    line=dict(color='blue', width=3),
    hovertemplate="Year %{x}: ₹%{y:,.0f}<extra></extra>"
))

fig.update_layout(
    xaxis_title="Year",
    yaxis=dict(
        title="Property Value (₹)",
        titlefont=dict(color='blue'),
        tickfont=dict(color='blue'),
        side='left'
    ),
    yaxis2=dict(
        title="Net Rent (₹)",
        titlefont=dict(color='green'),
        tickfont=dict(color='green'),
        overlaying='y',
        side='right'
    ),
    barmode='group',
    hovermode='x unified',
    height=450,
    legend=dict(y=0.95, x=0.01)
)

st.subheader("📊 Cashflow Projection")
st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.caption("Built for NRI and domestic investors to analyze residential real estate with data-driven metrics. 🧮")

