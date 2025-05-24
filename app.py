import streamlit as st
import numpy as np
import pandas as pd
from math import pow
import plotly.graph_objects as go
import numpy_financial as npf

st.set_page_config(page_title="NRI Investment Analyzer", layout="centered")
st.title("🏨 NRI Investment Analyzer")

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

# --- Under-construction settings ---
if property_type == "Under-construction":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Under-construction Settings")
    construction_years = st.sidebar.slider("Construction Period (Years)", 0, horizon_years, 2)
    
    payment_schedule_option = st.sidebar.selectbox("Payment Plan", ["10:20:30:40", "Custom"])
    
    # Default schedules
    default_schedule = [0.1, 0.2, 0.3, 0.4]
    default_timing_years = [0, 1, 1.75, 3]  # example timing for 10:20:30:40 in years
    
    if payment_schedule_option == "10:20:30:40":
        payment_schedule = default_schedule
        payment_timing = default_timing_years
    else:
        # Custom payment % input
        custom_schedule_str = st.sidebar.text_input(
            "Enter Custom Payment Schedule (%) as comma-separated values (sum=100)",
            value="10,20,30,40"
        )
        try:
            payment_schedule = [float(x.strip()) / 100 for x in custom_schedule_str.split(",")]
            if abs(sum(payment_schedule) - 1) > 0.01:
                st.sidebar.error("Sum of payment schedule percentages must be 100%.")
                payment_schedule = None
        except:
            st.sidebar.error("Invalid input for payment schedule.")
            payment_schedule = None
        
        # Custom timing input - user inputs comma separated timings (in months or years)
        timing_unit = st.sidebar.selectbox("Timing unit for payments", ["Months", "Years"])
        default_timing_input = "0, 6, 12, 18" if timing_unit == "Months" else "0, 0.5, 1, 1.5"
        custom_timing_str = st.sidebar.text_input(
            "Enter Timing for each payment tranche as comma-separated values",
            value=default_timing_input
        )
        try:
            payment_timing = [float(x.strip()) for x in custom_timing_str.split(",")]
            if len(payment_timing) != len(payment_schedule):
                st.sidebar.error("Number of timings must match number of payment tranches.")
                payment_timing = None
        except:
            st.sidebar.error("Invalid input for payment timings.")
            payment_timing = None
        
        # Convert timing to years if input was in months
        if payment_timing and timing_unit == "Months":
            payment_timing = [t/12 for t in payment_timing]
else:
    construction_years = 0
    payment_schedule = None
    payment_timing = None

# --- Calculations ---
down_payment_amt = property_price * down_payment_pct / 100
loan_amt = property_price - down_payment_amt
monthly_interest_rate = loan_interest_rate / 12 / 100
months = loan_tenure_yrs * 12

# EMI calculation
emi = npf.pmt(monthly_interest_rate, months, -loan_amt)
emi_rounded = round(emi)

# Disbursement schedule based on payment_schedule and payment_timing
disbursement_schedule = []
if property_type == "Under-construction" and payment_schedule and payment_timing:
    disbursed_amounts = [loan_amt * pct for pct in payment_schedule]
    # payment_timing is in years, convert to integer year and fractional for plotting
    disbursement_schedule = list(zip(payment_timing, disbursed_amounts))

# Rent cashflows
total_outflow = down_payment_amt
rent_annual = rent_monthly * 12
net_rent_annual = rent_annual - annual_maintenance

net_rent_vals = []
current_rent = net_rent_annual
for i in range(horizon_years):
    if i < construction_years:
        net_rent_vals.append(0)
    else:
        net_rent_vals.append(current_rent)
        current_rent *= (1 + rental_growth / 100)

net_rent_total = sum(net_rent_vals)

property_vals = [property_price * pow(1 + capital_appreciation / 100, i + 1) for i in range(horizon_years)]
final_property_value = property_vals[-1]

# --- Amortization Schedule ---

def amortization_schedule_monthly(principal, annual_rate, months):
    monthly_rate = annual_rate / 12 / 100
    schedule = []
    balance = principal
    for month in range(1, months + 1):
        interest = balance * monthly_rate
        principal_payment = npf.pmt(monthly_rate, months - month + 1, -balance) - interest
        balance -= principal_payment
        schedule.append({
            "Month": month,
            "Interest Paid": interest,
            "Principal Paid": principal_payment,
            "Remaining Balance": max(balance, 0)
        })
    return pd.DataFrame(schedule)

def amortization_schedule_annual(principal, annual_rate, years):
    monthly_rate = annual_rate / 12 / 100
    months = years * 12
    schedule = amortization_schedule_monthly(principal, annual_rate, months)
    schedule['Year'] = ((schedule['Month'] - 1) // 12) + 1
    annual_schedule = schedule.groupby('Year').agg({
        'Interest Paid': 'sum',
        'Principal Paid': 'sum',
        'Remaining Balance': 'last'
    }).reset_index()
    return annual_schedule

# Choose amortization view
st.subheader("🏦 Loan Amortization Schedule View")
amort_view = st.radio("Select amortization schedule view:", ["Monthly", "Annual"])

if amort_view == "Monthly":
    amort_df = amortization_schedule_monthly(loan_amt, loan_interest_rate, months)
else:
    amort_df = amortization_schedule_annual(loan_amt, loan_interest_rate, loan_tenure_yrs)

# Summarize interest and principal paid till horizon
if amort_view == "Monthly":
    months_horizon = min(horizon_years * 12, months)
    interest_paid = amort_df.loc[:months_horizon - 1, "Interest Paid"].sum()
    principal_paid = amort_df.loc[:months_horizon - 1, "Principal Paid"].sum()
else:
    years_horizon = min(horizon_years, loan_tenure_yrs)
    interest_paid = amort_df.loc[:years_horizon - 1, "Interest Paid"].sum()
    principal_paid = amort_df.loc[:years_horizon - 1, "Principal Paid"].sum()

total_outflow += interest_paid
total_inflow = net_rent_total + final_property_value
net_profit = total_inflow - total_outflow

# IRR Calculation using cash flows
cashflows = [-down_payment_amt]
for rent in net_rent_vals[:-1]:
    cashflows.append(rent)
cashflows.append(net_rent_vals[-1] + final_property_value)
irr = npf.irr(cashflows)

# --- Dashboard Output ---
st.subheader("📈 Investment Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Monthly EMI (₹)", f"{emi_rounded:,}")
col2.metric("Gross Rental Yield (%)", f"{rent_annual / property_price * 100:.2f}")
col3.metric("Net Rental Yield (%)", f"{net_rent_annual / property_price * 100:.2f}")
col4.metric(f"Investment Horizon (yrs)", f"{horizon_years}")

col5, col6, col7, col8 = st.columns(4)
col5.metric(f"Estimated Property Value (₹)", f"{final_property_value:,.0f}")
col6.metric(f"Total Net Rent Earned (₹)", f"{net_rent_total:,.0f}")
col7.metric(f"Total Outflow (₹)", f"{total_outflow:,.0f}")
col8.metric(f"Net Profit (₹)", f"{net_profit:,.0f}")

st.markdown(f"**Internal Rate of Return (IRR):** {irr * 100:.2f}%")

# --- Cashflow Projection Graph ---
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

# Plot disbursement schedule for under-construction payment timings
if disbursement_schedule:
    for year, amt in disbursement_schedule:
        fig.add_trace(go.Bar(
            x=[year + 1],
            y=[amt],
            name="Loan Disbursement",
            marker_color='orange',
            hovertemplate=f"Disbursed: ₹{amt:,.0f} in Year {year + 1}<extra></extra>",
            opacity=0.6,
            yaxis="y"
        ))

fig.update_layout
