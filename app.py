import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Wickboldt Capital | BTR Pro Forma Engine", layout="wide")

st.title("🏗️ BTR Pro Forma Engine")
st.markdown("### Wickboldt Capital — *Today's Foundation. Tomorrow's Legacy.*")
st.divider()

# --- SIDEBAR: MASTER MODEL DRIVERS ---
st.sidebar.header("Master Model Drivers")

st.sidebar.subheader("Project Scale")
units = st.sidebar.number_input("Number of Units (Doors)", min_value=1, value=1, step=1, format="%d")
opt_gc = st.sidebar.checkbox("Apply Consolidated Multi-Unit GC Fee?")
custom_gc_fee = 0
if opt_gc:
    custom_gc_fee = st.sidebar.number_input("Flat Consolidated GC Fee ($)", value=20000, step=1000, format="%d")

st.sidebar.subheader("Construction Costs (Heated Area)")
sqft = st.sidebar.number_input("Heated SqFt per Unit", value=1150, step=50, format="%d")
direct_cost_sf = st.sidebar.slider("Direct Build Cost / SF ($)", min_value=40.0, max_value=150.0, value=74.0, step=1.0)

st.sidebar.subheader("Auxiliary Structure (Carport / Garage)")
structure_type = st.sidebar.selectbox("Structure Type", ["Carport", "Garage"])
struct_sqft = st.sidebar.number_input(f"{structure_type} SqFt per Unit", value=200, step=25, format="%d")
default_struct_cost = 31.0 if structure_type == "Carport" else 55.0
struct_cost_sf = st.sidebar.slider(f"{structure_type} Cost / SF ($)", min_value=15.0, max_value=90.0, value=default_struct_cost, step=1.0)

st.sidebar.subheader("Porches (Front & Back)")
front_porch_sqft = st.sidebar.number_input("Front Porch SqFt", value=60, step=10, format="%d")
front_porch_cost_sf = st.sidebar.slider("Front Porch Cost / SF ($)", min_value=15.0, max_value=70.0, value=35.0, step=1.0)

back_porch_sqft = st.sidebar.number_input("Back Porch SqFt", value=120, step=10, format="%d")
back_porch_cost_sf = st.sidebar.slider("Back Porch Cost / SF ($)", min_value=15.0, max_value=70.0, value=35.0, step=1.0)

st.sidebar.subheader("Financing & Timeline")
use_comp_valuation = st.sidebar.checkbox("Derive Appraised Value (ARV) from Comp Tool?", value=True)
manual_arv_per_unit = st.sidebar.number_input("Manual Retail Appraised Value (ARV) per Unit ($)", value=182600, step=1000, format="%d")
ltv = st.sidebar.slider("Commercial Takeout LTV (%)", min_value=60.0, max_value=85.0, value=80.0, step=5.0) / 100.0
build_months = st.sidebar.slider("Construction Duration (Months)", min_value=3, max_value=18, value=9, step=1)
const_rate = st.sidebar.slider("Construction Loan Rate (%)", min_value=4.0, max_value=12.0, value=8.0, step=0.5) / 100.0

st.sidebar.subheader("Standard Fees & Land")
land_basis = st.sidebar.number_input("Land Basis per Lot ($)", value=15000, step=1000, format="%d")
soft_costs = st.sidebar.number_input("Soft Costs per Unit ($)", value=5500, step=500, format="%d")
const_fees = st.sidebar.number_input("Const. Loan Closing Fee per Unit ($)", value=6000, step=500, format="%d")
takeout_fees = st.sidebar.number_input("Takeout Refi Fee per Unit ($)", value=3650, step=50, format="%d")

# --- COMPARABLE MARKET ANALYSIS (COMP BENCHMARK TOOL) ---
st.markdown("### 🔍 Market Comp Blended Cost & Valuation Benchmark")
st.markdown("Input market comparable data below to evaluate blended under-roof costs. If enabled in the sidebar, this comp valuation drives the project's Appraised Value (ARV).")

cc_col1, cc_col2, cc_col3, cc_col4, cc_col5 = st.columns(5)
comp_price = cc_col1.number_input("Comp Total Value / Price ($)", value=182600, step=1000, format="%d")
comp_heated_sf = cc_col2.number_input("Comp Heated SF", value=1150, step=50, format="%d")
comp_struct_sf = cc_col3.number_input("Comp Garage/Carport SF", value=200, step=25, format="%d")
comp_front_sf = cc_col4.number_input("Comp Front Porch SF", value=60, step=10, format="%d")
comp_back_sf = cc_col5.number_input("Comp Back Porch SF", value=120, step=10, format="%d")

comp_total_sf = comp_heated_sf + comp_struct_sf + comp_front_sf + comp_back_sf
comp_blended_cost = comp_price / comp_total_sf if comp_total_sf > 0 else 0

# --- CORE CALCULATIONS ---
heated_hard_cost = sqft * direct_cost_sf
struct_total_cost = struct_sqft * struct_cost_sf
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf

hard_cost_per_unit = heated_hard_cost + struct_total_cost + front_porch_cost + back_porch_cost
total_hard_cost = hard_cost_per_unit * units

# Under-roof metrics for project unit
total_under_roof_sqft = sqft + struct_sqft + front_porch_sqft + back_porch_sqft
blended_cost_per_sf = hard_cost_per_unit / total_under_roof_sqft if total_under_roof_sqft > 0 else 0

# Determine Appraised Value (ARV) per unit
if use_comp_valuation:
    arv_per_unit = comp_blended_cost * total_under_roof_sqft
else:
    arv_per_unit = manual_arv_per_unit

gcond = total_hard_cost * 0.05
fee_basis = total_hard_cost + gcond

if opt_gc:
    gc_fee = custom_gc_fee
else:
    gc_fee = fee_basis * 0.10

premium = total_hard_cost * 0.05
total_const = fee_basis + gc_fee + premium

total_soft_costs = soft_costs * units
total_land = land_basis * units
total_const_fees = const_fees * units
total_takeout_fees = takeout_fees * units

total_arv = arv_per_unit * units
loan_total = total_arv * ltv
buydown_pts = loan_total * 0.02

# Carry interest calculation (dynamic build time)
carry_int = (total_const + total_soft_costs) * 0.5 * const_rate * (build_months / 12.0)

total_project_basis = total_land + total_const + total_soft_costs + total_const_fees + total_takeout_fees + buydown_pts + carry_int
cash_surplus = loan_total - total_project_basis
retained_equity = total_arv - loan_total
day1_wealth = gc_fee + max(0, cash_surplus) + retained_equity

st.info(f"📊 **Comp Benchmarks:** Comp Under-Roof Area: **{comp_total_sf:,} SF** | Comp Blended Cost: **${comp_blended_cost:.2f} / SF** | **Derived Unit ARV: ${arv_per_unit:,.0f}**")
st.divider()

# --- DASHBOARD UI ---
col1, col2, col3, col4 = st.columns(4)

col1.metric("Takeout Loan Proceeds", f"${loan_total:,.0f}", f"{ltv*100:.0f}% LTV")
col2.metric("Total Project Basis", f"${total_project_basis:,.0f}", f"${total_project_basis/units:,.0f} per door", delta_color="inverse")
col3.metric("Under-Roof Blended Cost", f"${blended_cost_per_sf:.2f} / SF", f"{total_under_roof_sqft:,} Total SF Under Roof")

if cash_surplus >= 0:
    col4.metric("Tax-Free Cash Surplus", f"${cash_surplus:,.0f}", "Capital Recovered")
else:
    col4.metric("Trapped Seed Capital", f"${cash_surplus:,.0f}", "Loss at Closing")

st.divider()

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown("### 📊 Capital Ledger Breakdown")
    ledger_data = {
        "Category": [
            "Land Acquisition", 
            f"Heated Hard Costs ({sqft:,.0f} SF @ ${direct_cost_sf:.2f}/SF)", 
            f"{structure_type} Hard Costs ({struct_sqft:,.0f} SF @ ${struct_cost_sf:.2f}/SF)",
            f"Front Porch ({front_porch_sqft:,.0f} SF @ ${front_porch_cost_sf:.2f}/SF)",
            f"Back Porch ({back_porch_sqft:,.0f} SF @ ${back_porch_cost_sf:.2f}/SF)",
            "General Conditions (5%)", 
            "GC Management Fee", 
            "BTR Buying Power Premium (5%)", 
            "Soft Costs & Permitting",
            "Const. Loan Fees & Carry Interest", 
            "Takeout Refi Fees & Buydown Points", 
            "TOTAL PROJECT BASIS"
        ],
        "Amount ($)": [
            total_land,
            heated_hard_cost * units,
            struct_total_cost * units,
            front_porch_cost * units,
            back_porch_cost * units,
            gcond,
            gc_fee,
            premium,
            total_soft_costs,
            total_const_fees + carry_int,
            total_takeout_fees + buydown_pts,
            total_project_basis
        ]
    }
    df_ledger = pd.DataFrame(ledger_data)
    df_ledger['Amount ($)'] = df_ledger['Amount ($)'].apply(lambda x: f"${x:,.0f}")
    st.dataframe(df_ledger, hide_index=True, use_container_width=True)

with row2_col2:
    st.markdown("### 💰 Day-1 Wealth Creation")
    wealth_data = {
        "Pocket Component": [
            "Pocket 1: Active GC Fee Revenue", 
            "Pocket 2: Tax-Free Cash Surplus at Close",
            "Pocket 3: Retained Asset Equity", 
            "TOTAL DAY-1 CREATED VALUE"
        ],
        "Value ($)": [
            gc_fee, 
            cash_surplus, 
            retained_equity, 
            day1_wealth
        ]
    }
    df_wealth = pd.DataFrame(wealth_data)
    df_wealth['Value ($)'] = df_wealth['Value ($)'].apply(lambda x: f"${x:,.0f}")
    st.dataframe(df_wealth, hide_index=True, use_container_width=True)

    if cash_surplus >= 0:
        st.success(f"**Infinite Cash-on-Cash Return Achieved:** You have recovered 100% of your seed capital plus an additional ${cash_surplus:,.0f} in liquid cash.")
    else:
        st.error(f"**Capital Trapped:** You are leaving ${abs(cash_surplus):,.0f} of your seed capital in the deal to close the takeout loan. Try lowering your Direct Build Cost / SF or reducing the construction timeline.")
