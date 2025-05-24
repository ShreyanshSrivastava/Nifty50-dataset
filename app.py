import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

st.title("🏠 NRI Real Estate Investment Analyzer")

# Sidebar inputs
st.sidebar.header("📋 Project & Financial Details")
property_name = st.sidebar.text_input("Property Name", "Lodha Amara - 1 BHK")
total_cost = st.sidebar.number_input("Total Property Cost (₹)", value=8500000, step=50000)
loan_percentage = st.sidebar.slider("Loan as % of Total Cost", 0, 100, 60)
tenure_years = st.sidebar.slider("Loan Tenure (Years)", 1, 30, 20)
interest_rate = st.sidebar.slider("Interest Rate (% p.a.)", 1.0, 15.0, 8.6)

payment_schedule_type = st.sidebar.selectbox("Payment Plan Type", ["Standard (10:20:30:40)", "Custom"])

if payment_schedule_type == "Standard (10:20:30:40)":
    schedule = [(10, 0), (20, 45), (30, 315), (40, 1000)]  # days from today
else:
    st.sidebar.markdown("### Custom Payment Plan")
    num_tranches = st.sidebar.number_input("Number of Tranches", 1, 10, 4)
    schedule = []
    for i in range(num_tranches):
        percent = st.sidebar.number_input(f"Tranche {i+1} %", min_value=0, max_value=100, value=25, key=f"percent_{i}")
        days = st.sidebar.number_input(f"Tranche {i+1} - Days from Today", min_value=0, value=i * 180, key=f"days_{i}")
        schedule.append((percent, days))

expected_rent = st.sidebar.number_input("Expected Monthly Rent on Possession (₹)", value=24000, step=1000)
appreciation_rate = st.sidebar.slider("Expected Annual Appreciation (%)", 0.0, 20.0, 6.0)
holding_period_years = st.sidebar.slider("Holding Period (Years)", 1, 30, tenure_years)

# Calculations
loan_amount = total_cost * loan_percentage / 100
equity = total_cost - loan_amount
emi = np.pmt(interest_rate / 1200, tenure_years * 12, -loan_amount)

# Demand schedule
today = datetime.today()
demand_df = pd.DataFrame(schedule, columns=["%", "Days"])
demand_df["₹"] = demand_df["%"] / 100 * total_cost
demand_df["Date"] = demand_df["Days"].apply(lambda x: today + timedelta(days=int(x)))
demand_df = demand_df.sort_values("Date").reset_index(drop=True)
demand_df["Cumulative ₹"] = demand_df["₹"].cumsum()

# Loan amortization
def generate_amortization(loan, rate, tenure_years, freq="Monthly"):
    schedule = []
    periods = tenure_years * 12 if freq == "Monthly" else tenure_years
    r = rate / 1200 if freq == "Monthly" else rate / 100
    emi = np.pmt(r, periods, -loan)
    balance = loan
    for i in range(1, periods + 1):
        interest = balance * r
        principal = emi - interest
        balance -= principal
        schedule.append({"Period": i, "EMI": emi, "Interest": interest, "Principal": principal, "Balance": balance})
    return pd.DataFrame(schedule)

amort_view = st.radio("📅 View Amortization Schedule As:", ["Monthly", "Annual"])
amort_df = generate_amortization(loan_amount, interest_rate, tenure_years, freq=amort_view)
if amort_view == "Annual":
    amort_df = amort_df.groupby(amort_df.index // 12).sum(numeric_only=True).reset_index(drop=True)
    amort_df.index += 1
    amort_df["Period"] = amort_df.index

# Rent and appreciation projections
possession_date = demand_df["Date"].max()
rent_years = holding_period_years - ((possession_date - today).days // 365)
rental_income = expected_rent * 12 * max(rent_years, 0)
projected_value = total_cost * ((1 + appreciation_rate / 100) ** holding_period_years)
total_outflow = equity + (emi * min(holding_period_years, tenure_years) * 12)
net_profit = projected_value + rental_income - total_outflow
roi = (net_profit / total_outflow) * 100 if total_outflow else 0

# Display Summary
st.header("📊 Investment Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Equity Invested (₹)", f"{equity:,.0f}")
col2.metric("Loan Amount (₹)", f"{loan_amount:,.0f}")
col3.metric("Monthly EMI (₹)", f"{emi:,.0f}")

col4, col5, col6 = st.columns(3)
col4.metric("Rental Income (₹)", f"{rental_income:,.0f}")
col5.metric("Property Value (₹)", f"{projected_value:,.0f}")
col6.metric("Net Profit (₹)", f"{net_profit:,.0f}")

col7, col8, col9 = st.columns(3)
col7.metric("Total Outflow (₹)", f"{total_outflow:,.0f}")
col8.metric("ROI (%)", f"{roi:.2f}%")

# Demand Table
st.subheader("📅 Demand Schedule")
st.dataframe(demand_df[["%", "₹", "Date", "Cumulative ₹"]])

# Cashflow over years
st.subheader("🧾 Annual Cashflow Table")
cf_data = []
for year in range(1, holding_period_years + 1):
    rent = expected_rent * 12 if year > (possession_date - today).days // 365 else 0
    emi_outflow = emi * 12 if year <= tenure_years else 0
    net = rent - emi_outflow
    cf_data.append({"Year": year, "Rental Income": rent, "EMI Outflow": emi_outflow, "Net Cashflow": net})
cf_df = pd.DataFrame(cf_data)
st.dataframe(cf_df)

# Loan Amortization
st.subheader("💳 Loan Amortization Schedule")
st.dataframe(amort_df)

# Principal vs Interest chart
fig = go.Figure()
fig.add_trace(go.Bar(x=amort_df["Period"], y=amort_df["Principal"], name="Principal", marker_color="green"))
fig.add_trace(go.Bar(x=amort_df["Period"], y=amort_df["Interest"], name="Interest", marker_color="red"))
fig.update_layout(title="EMI Split Over Time", xaxis_title="Period", yaxis_title="Amount (₹)", barmode='stack')
st.plotly_chart(fig)

