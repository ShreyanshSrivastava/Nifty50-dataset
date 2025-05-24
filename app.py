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

# Additional fields for under-construction properties
if property_type == "Under-construction":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Under-construction Settings")
    construction_years = st.sidebar.slider("Construction Period (Years)", 0, horizon_years, 2)
    
    # Support custom payment schedule input as comma-separated percentages
    payment_schedule_option = st.sidebar.selectbox("Payment Plan", ["10:20:30:40", "Custom"])
    if payment_schedule_option == "10:20:30:40":
        payment_schedule = [0.1, 0.2, 0.3, 0.4]
    else:
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

    staggered_emi = st.sidebar.checkbox("Enable Staggered EMI During Construction", value=True)
else:
    construction_years = 0
    payment_schedule = None

# --- Calculations ---
down_payment_amt = property_price * down_payment_pct / 100
loan_amt = property_price - down_payment_amt
monthly_interest_rate = loan_interest_rate / 12 / 100
months = loan_tenure_yrs * 12

# EMI calculation (regular fixed EMI)
emi = npf.pmt(monthly_interest_rate, months, -loan_amt)
emi_rounded = round(emi)

# Disbursement logic for payment schedule
disbursement_schedule = []
if property_type == "Under-construction" and payment_schedule:
    # distribute payments across construction period and possibly after
    # We assume equal spacing across schedule length (e.g. 4 payments over construction period)
    num_payments = len(payment_schedule)
    # Distribute payments evenly over construction period, if construction_years > 0
    # if no construction period, all upfront (Year 0)
    if construction_years > 0:
        payment_years = np.linspace(0, construction_years, num=num_payments, dtype=int)
    else:
        payment_years = [0]*num_payments

    disbursed_amounts = [loan_amt * pct for pct in payment_schedule]
    disbursement_schedule = list(zip(payment_years, disbursed_amounts))

# Adjust cashflows and outflows
total_outflow = down_payment_amt
rent_annual = rent_monthly * 12
net_rent_annual = rent_annual - annual_maintenance

# Calculate rent with growth each year
net_rent_vals = []
current_rent = net_rent_annual
for i in range(horizon_years):
    if i < construction_years:
        net_rent_vals.append(0)  # no rent during construction
    else:
        net_rent_vals.append(current_rent)
        current_rent *= (1 + rental_growth / 100)

net_rent_total = sum(net_rent_vals)

# Estimate property value after holding period (year-wise)
property_vals = [property_price * pow(1 + capital_appreciation / 100, i + 1) for i in range(horizon_years)]
final_property_value = property_vals[-1]

# --- Loan Amortization Schedule Calculation ---

def amortization_schedule(principal, annual_rate, months):
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

amort_df = amortization_schedule(loan_amt, loan_interest_rate, months)

# Sum interest and principal paid in horizon years (partial loan payoff)
months_horizon = min(horizon_years * 12, months)
interest_paid = amort_df.loc[:months_horizon - 1, "Interest Paid"].sum()
principal_paid = amort_df.loc[:months_horizon - 1, "Principal Paid"].sum()

# Net profit calculation updated to use amortization data
total_outflow += interest_paid
total_inflow = net_rent_total + final_property_value
net_profit = total_inflow - total_outflow

# IRR Calculation using cash flows (simplified - using annual flows)
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
col7.metric(f"Total Outflow (₹)", f"{total_outflow:,.0f}")
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

# If under-construction, add disbursement visualization
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

fig.update_layout(
    xaxis_title="Year",
    yaxis=dict(
        title="Property Value (₹)",
        tickfont=dict(color='blue'),
        side='left',
        showgrid=False
    ),
    yaxis2=dict(
        title="Net Rent (₹)",
        tickfont=dict(color='green'),
        overlaying='y',
        side='right',
        showgrid=False
    ),
    barmode='group',
    hovermode='x unified',
    height=500,
    legend=dict(y=0.95, x=0.01)
)

st.subheader("📊 Cashflow Projection")
st.plotly_chart(fig, use_container_width=True)

# --- Cashflow Table ---

st.subheader("🧾 Annual Cashflow Table")

cashflow_df = pd.DataFrame({
    "Year": years,
    "Net Rent (₹)": [f"₹{int(x):,}" for x in net_rent_vals],
    "Property Value (₹)": [f"₹{int(x):,}" for x in property_vals]
})

st.dataframe(cashflow_df)

# --- Loan Amortization Schedule Display ---

st.subheader("🏦 Loan Amortization Schedule")

show_amort = st.checkbox("Show Detailed Loan Amortization Schedule")
if show_amort:
    # Add month and format values
    amort_df_display = amort_df.copy()
    amort_df_display["Month"] = amort_df_display["Month"].astype(int)
    amort_df_display["Interest Paid"] = amort_df_display["Interest Paid"].apply(lambda x: f"₹{x:,.0f}")
    amort_df_display["Principal Paid"] = amort_df_display["Principal Paid"].apply(lambda x: f"₹{x:,.0f}")
    amort_df_display["Remaining Balance"] = amort_df_display["Remaining Balance"].apply(lambda x: f"₹{x:,.0f}")
    st.dataframe(amort_df_display)

    # Plot Interest vs Principal over months
    fig_amort = go.Figure()
    fig_amort.add_trace(go.Scatter(
        x=amort_df["Month"],
        y=amort_df["Interest Paid"].astype(float),
        mode='lines',
        name="Interest Paid",
        line=dict(color='red')
    ))
    fig_amort.add_trace(go.Scatter(
        x=amort_df["Month"],
        y=amort_df["Principal Paid"].astype(float),
        mode='lines',
        name="Principal Paid",
        line=dict(color='blue')
    ))
    fig_amort.update_layout(
        title="Loan Amortization: Interest vs Principal Paid Over Time",
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        height=400,
        legend=dict(x=0.7, y=0.95)
    )
    st.plotly_chart(fig_amort, use_container_width=True)
