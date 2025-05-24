import streamlit as st
import numpy as np
from math import pow
import plotly.graph_objects as go
import numpy_financial as npf

st.set_page_config(page_title="NRI Investment Analyzer", layout="wide")
st.title("🏘️ NRI Investment Analyzer")

# Sidebar inputs
property_type = st.sidebar.selectbox("Property Type", ["Ready-to-move", "Under-construction"])
property_price = st.sidebar.number_input("Property Price (₹)", value=8000000, step=50000)
down_payment_pct = st.sidebar.slider("Down Payment (%)", 10, 100, 30)
loan_interest_rate = st.sidebar.number_input("Loan Interest Rate (%)", value=8.5)
loan_tenure_yrs = st.sidebar.slider("Loan Tenure (years)", 5, 30, 20)
rent_monthly = st.sidebar.number_input("Expected Monthly Rent (₹)", value=25000, step=1000)
annual_maintenance = st.sidebar.number_input("Annual Maintenance & Tax (₹)", value=30000)
capital_appreciation = st.sidebar.slider("Expected Capital Appreciation (CAGR %)", 0, 15, 6)
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 10)

# Calculations
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

final_property_value = property_price * pow(1 + capital_appreciation / 100, horizon_years)
total_inflow = net_rent_total + final_property_value

interest_paid = emi * min(horizon_years, loan_tenure_yrs) * 12 - loan_amt
net_profit = total_inflow - total_outflow - interest_paid

cashflows = [-down_payment_amt] + [net_rent_annual] * (horizon_years - 1) + [net_rent_annual + final_property_value]
irr = npf.irr(cashflows)

# Dashboard Layout
st.subheader("📊 Investment Summary Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Monthly EMI", f"₹{emi_rounded:,}")
col2.metric("Net Rental Yield", f"{net_rent_annual / property_price * 100:.2f}%")
col3.metric(f"Est. Property Value (₹{horizon_years} yrs)", f"₹{final_property_value:,.0f}")
col4.metric("IRR", f"{irr * 100:.2f}%" if irr is not None else "N/A")

col1.metric("Total Outflow", f"₹{(total_outflow + interest_paid):,.0f}")
col2.metric("Total Inflow", f"₹{total_inflow:,.0f}")
col3.metric("Net Profit", f"₹{net_profit:,.0f}")
col4.metric("Gross Rental Yield", f"{rent_annual / property_price * 100:.2f}%")

# Interactive Graphs
st.subheader("📈 Cashflow & Valuation Projections")

years = list(range(1, horizon_years + 1))
net_rent_vals = [net_rent_annual] * (horizon_years - 1) + [net_rent_annual]
property_vals = [property_price * pow(1 + capital_appreciation / 100, i) for i in range(1, horizon_years + 1)]

fig = go.Figure()

fig.add_trace(go.Bar(
    x=years,
    y=net_rent_vals,
    name="Net Rent (Annual)",
    marker_color='green',
    hovertemplate="Year %{x}: ₹%{y:,.0f}<extra></extra>"
))

fig.add_trace(go.Scatter(
    x=years,
    y=property_vals,
    mode='lines+markers',
    name='Estimated Property Value',
    line=dict(color='blue', width=3),
    hovertemplate="Year %{x}: ₹%{y:,.0f}<extra></extra>"
))

fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Amount (₹)",
    barmode='group',
    hovermode='x unified',
    height=450,
    legend=dict(y=0.95, x=0.01)
)

st.plotly_chart(fig, use_container_width=True)

# Footer note
st.caption("Built for NRI and domestic investors to analyze residential real estate with data-driven metrics. 🧮")
