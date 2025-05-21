import streamlit as st
import numpy_financial as npf
import pandas as pd

st.set_page_config(page_title="NRI Investment Analyzer", layout="wide")
st.title("🇮🇳 NRI Real Estate Investment Analyzer")

# --- Sidebar Inputs ---
st.sidebar.header("Property & Loan Details")
property_value = st.sidebar.number_input("Property Value (INR)", value=12000000, step=100000)
loan_amount = st.sidebar.number_input("Loan Amount (INR)", value=8000000, step=100000)
interest_rate = st.sidebar.slider("Interest Rate (%)", min_value=5.0, max_value=12.0, value=8.6) / 100
loan_term = st.sidebar.slider("Loan Tenure (Years)", 5, 30, 20)

st.sidebar.header("Rental & Growth")
monthly_rent = st.sidebar.number_input("Starting Rent (INR/month)", value=30000, step=1000)
rent_escalation = st.sidebar.slider("Annual Rent Escalation (%)", 0.0, 10.0, 5.0) / 100
appreciation = st.sidebar.slider("Property Appreciation (%)", 0.0, 15.0, 6.0) / 100
maintenance = st.sidebar.number_input("Monthly Maintenance (INR)", value=5000, step=500)

st.sidebar.header("Tax & FX")
tax_bracket = st.sidebar.slider("Tax Bracket (%)", 0, 40, 30) / 100
usd_inr = st.sidebar.number_input("USD/INR Exchange Rate", value=83.0)
cap_gains_tax = st.sidebar.slider("Capital Gains Tax (%)", 0, 30, 20) / 100

# --- Calculations ---
months = loan_term * 12
monthly_interest = interest_rate / 12
emi = loan_amount * monthly_interest * ((1 + monthly_interest) ** months) / (((1 + monthly_interest) ** months) - 1)

# Yearly projections
years = loan_term
df = pd.DataFrame(index=range(1, years + 1))
df['Year'] = df.index
df['Annual EMI'] = emi * 12
df['Annual Rent'] = [monthly_rent * 12 * ((1 + rent_escalation) ** (i)) for i in range(years)]
df['Maintenance'] = maintenance * 12
df['Net Cashflow'] = df['Annual Rent'] - df['Annual EMI'] - df['Maintenance']
df['Tax Savings'] = df['Annual EMI'] * tax_bracket

df['Net Benefit'] = df['Net Cashflow'] + df['Tax Savings']
df['Property Value'] = [property_value * ((1 + appreciation) ** i) for i in range(years)]

df['Net Benefit (USD)'] = df['Net Benefit'] / usd_inr
df['Property Value (USD)'] = df['Property Value'] / usd_inr

# IRR Calculation
initial_outflow = property_value - loan_amount
cashflows = [-initial_outflow] + df['Net Benefit'].tolist()
irr = npf.irr(cashflows)

# Sale details
df['Cumulative Net Benefit'] = df['Net Benefit'].cumsum()
sale_price = df['Property Value'].iloc[-1]
capital_gain = sale_price - property_value
tax_on_sale = capital_gain * cap_gains_tax
net_sale_proceeds_usd = (sale_price - tax_on_sale) / usd_inr

# --- Display ---
st.subheader("📊 Investment Summary")
st.dataframe(df.style.format({
    'Annual EMI': '₹{:,.0f}',
    'Annual Rent': '₹{:,.0f}',
    'Maintenance': '₹{:,.0f}',
    'Net Cashflow': '₹{:,.0f}',
    'Tax Savings': '₹{:,.0f}',
    'Net Benefit': '₹{:,.0f}',
    'Property Value': '₹{:,.0f}',
    'Net Benefit (USD)': '${:,.0f}',
    'Property Value (USD)': '${:,.0f}'
}))

st.markdown(f"### 💡 Internal Rate of Return (IRR): **{irr * 100:.2f}%**")
st.markdown(f"### 💸 Net USD Sale Proceeds (post-tax): **${net_sale_proceeds_usd:,.0f}**")

# --- Download ---
st.download_button(
    label="Download Results as CSV",
    data=df.to_csv(index=False).encode('utf-8'),
    file_name='nri_investment_analysis.csv',
    mime='text/csv'
)
