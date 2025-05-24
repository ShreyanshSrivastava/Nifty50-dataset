import streamlit as st
import numpy as np
import pandas as pd
from math import pow, ceil
import numpy_financial as npf
import plotly.graph_objects as go

st.set_page_config(page_title="NRI Investment Analyzer - Under Construction Enhancements", layout="wide")
st.title("🏘️ NRI Investment Analyzer (Under Construction with Custom Payments)")

st.markdown("""
Analyze residential property investments with flexible payment plans and staggered loans for under-construction projects.
""")

# --- Inputs ---
st.sidebar.header("Property Details")
property_type = st.sidebar.selectbox("Property Type", ["Ready-to-move", "Under-construction"])
property_price = st.sidebar.number_input("Property Price (₹)", value=8000000, step=50000)

if property_type == "Under-construction":
    st.sidebar.markdown("### Custom Payment Schedule")
    num_payments = st.sidebar.slider("Number of Payments", 2, 6, 4)

    payment_percents = []
    payment_months = []

    for i in range(num_payments):
        p = st.sidebar.number_input(f"Payment {i+1} (%)", min_value=0, max_value=100, value=0, step=5, key=f"pct_{i}")
        m = st.sidebar.number_input(f"Payment {i+1} Month (from start)", min_value=0, max_value=60, value=0, step=1, key=f"month_{i}")
        payment_percents.append(p)
        payment_months.append(m)

    if abs(sum(payment_percents) - 100) > 0.01:
        st.sidebar.error("Total payment percentages must sum to 100%")
    
    construction_period_months = max(payment_months)
else:
    # Ready to move defaults
    down_payment_pct = st.sidebar.slider("Down Payment (%)", 10, 100, 30)
    construction_period_months = 0

loan_interest_rate = st.sidebar.number_input("Loan Interest Rate (%)", value=8.5)
loan_tenure_yrs = st.sidebar.slider("Loan Tenure (years)", 5, 30, 20)
rent_monthly = st.sidebar.number_input("Expected Monthly Rent (₹)", value=25000, step=1000)
annual_maintenance = st.sidebar.number_input("Annual Maintenance & Tax (₹)", value=30000)
capital_appreciation = st.sidebar.slider("Expected Capital Appreciation (CAGR %)", 0, 15, 6)
rental_growth = st.sidebar.slider("Expected Rental Growth (CAGR %)", 0, 15, 3)
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 10)

# --- Calculations ---
months_horizon = horizon_years * 12

if property_type == "Under-construction":
    # Calculate payment amounts by month
    payment_amounts = [property_price * (pct / 100) for pct in payment_percents]
    payment_schedule = list(zip(payment_months, payment_amounts))

    # Sort payments by month ascending (just in case)
    payment_schedule = sorted(payment_schedule, key=lambda x: x[0])

    # Loan disbursements = payments (loan funds paid out as needed)
    # Assume loan is taken as needed per payment, EMI tenure fixed for loan_tenure_yrs from disbursement month
    monthly_interest_rate = loan_interest_rate / 12 / 100

    # For each loan tranche, calculate EMI and generate EMI schedule over horizon months
    emi_schedules = np.zeros(months_horizon)
    loan_disbursed_total = 0

    for pay_month, pay_amt in payment_schedule:
        if pay_amt == 0:
            continue
        loan_disbursed_total += pay_amt
        tenure_months = loan_tenure_yrs * 12
        emi = pay_amt * monthly_interest_rate * pow(1 + monthly_interest_rate, tenure_months) / (pow(1 + monthly_interest_rate, tenure_months) - 1)

        # EMI starts at pay_month (0-based indexing)
        for m in range(pay_month, min(pay_month + tenure_months, months_horizon)):
            emi_schedules[m] += emi

    # Payments are outflows at payment months
    monthly_payments = np.zeros(months_horizon)
    for pay_month, pay_amt in payment_schedule:
        if pay_amt == 0:
            continue
        if pay_month < months_horizon:
            monthly_payments[pay_month] += pay_amt

    # Rent starts only after construction period ends
    monthly_rent_schedule = np.zeros(months_horizon)
    current_rent = rent_monthly
    for m in range(construction_period_months, months_horizon):
        # Apply rental growth annually (every 12 months)
        years_passed = (m - construction_period_months) // 12
        rent_this_month = current_rent * pow(1 + rental_growth / 100, years_passed)
        monthly_rent_schedule[m] = rent_this_month

    # Maintenance tax assumed yearly, distribute monthly for cashflow
    monthly_maintenance = annual_maintenance / 12

    # Monthly net rent after maintenance (only months after construction)
    monthly_net_rent = np.array([max(0, r - monthly_maintenance) for r in monthly_rent_schedule])

    # Property value growth yearly (for final sale)
    property_value_by_year = [property_price * pow(1 + capital_appreciation / 100, y) for y in range(1, horizon_years + 1)]

    # Total outflow: payments + EMIs
    total_outflows = np.sum(monthly_payments) + np.sum(emi_schedules)
    # Total inflow: rent + final sale value (at end of horizon)
    total_inflows = np.sum(monthly_net_rent) + property_value_by_year[-1]

    net_profit = total_inflows - total_outflows

    # Construct annual cashflows for IRR (year 0 is initial outflow of downpayment which is first payment)
    # For IRR, each year cashflow = inflows - outflows
    annual_cashflows = []
    for y in range(horizon_years + 1):
        start_month = y * 12
        end_month = min(start_month + 12, months_horizon)
        inflows = np.sum(monthly_net_rent[start_month:end_month])
        outflows = np.sum(monthly_payments[start_month:end_month]) + np.sum(emi_schedules[start_month:end_month])
        if y == 0:
            # Include initial payment(s) at month 0 if any
            outflows += 0  # Already counted in monthly_payments
        if y == horizon_years:
            inflows += property_value_by_year[-1]
        annual_cashflows.append(inflows - outflows)
    # Note: First year cashflow negative because payments > inflows

else:
    # Ready-to-move logic (simple)
    down_payment_amt = property_price * down_payment_pct / 100
    loan_amt = property_price - down_payment_amt
    monthly_interest_rate = loan_interest_rate / 12 / 100
    months = loan_tenure_yrs * 12

    emi = loan_amt * monthly_interest_rate * pow(1 + monthly_interest_rate, months) / (pow(1 + monthly_interest_rate, months) - 1)
    emi_rounded = round(emi)

    total_outflow = down_payment_amt
    rent_annual = rent_monthly * 12
    net_rent_annual = rent_annual - annual_maintenance

    net_rent_vals = []
    current_rent = net_rent_annual
    for i in range(horizon_years):
        net_rent_vals.append(current_rent)
        current_rent *= (1 + rental_growth / 100)

    net_rent_total = sum(net_rent_vals)

    property_vals = [property_price * pow(1 + capital_appreciation / 100, i + 1) for i in range(horizon_years)]
    final_property_value = property_vals[-1]

    total_inflow = net_rent_total + final_property_value

    interest_paid = emi * min(horizon_years, loan_tenure_yrs) * 12 - loan_amt
    net_profit = total_inflow - total_outflow - interest_paid

    cashflows = [-down_payment_amt]
    for rent in net_rent_vals[:-1]:
        cashflows.append(rent)
    cashflows.append(net_rent_vals[-1] + final_property_value)
    annual_cashflows = cashflows

# IRR Calculation
try:
    irr = npf.irr(annual_cashflows)
except:
    irr = None

# --- Dashboard ---

st.subheader("📈 Investment Summary")

if property_type == "Under-construction":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Payments (₹)", f"{np.sum(monthly_payments):,.0f}")
    col2.metric("Total EMIs Paid (₹)", f"{np.sum(emi_schedules):,.0f}")
    col3.metric("Total Outflows (₹)", f"{total_outflows:,.0f}")
    col4.metric("Net Profit (₹)", f"{net_profit:,.0f}")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Investment Horizon (yrs)", horizon_years)
    col6.metric("Final Property Value (₹)", f"{property_value_by_year[-1]:,.0f}")
    total_rent_earned = np.sum(monthly_net_rent)
    col7.metric("Total Net Rent Earned (₹)", f"{total_rent_earned:,.0f}")
    if irr is not None:
        col8.metric("Internal Rate of Return (IRR %)", f"{irr*100:.2f}%")
    else:
        col8.metric("Internal Rate of Return (IRR %)", "N/A")

else:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Monthly EMI (₹)", f"{emi_rounded:,}")
    col2.metric("Gross Rental Yield (%)", f"{rent_annual / property_price * 100:.2f}")
    col3.metric("Net Rental Yield (%)", f"{net_rent_annual / property_price * 100:.2f}")
    col4.metric(f"Investment Horizon (yrs)", f"{horizon_years}")

    col5, col6,
