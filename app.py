import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import requests
import os
import json
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Wickboldt Capital | BTR Pro Forma Engine", layout="wide")

# ==========================================
# --- SMART DEFAULTS SYSTEM ---
# ==========================================
DEFAULT_FILE = "global_defaults.json"

HARDCODED_DRIVERS = {
    "units": 1,
    "sqft": 1150,
    "structure_type": "Carport", 
    "struct_sqft": 200,
    "base_struct_cost_sf": 31.0,
    "front_porch_sqft": 60,
    "front_porch_cost_sf": 35.0,
    "back_porch_sqft": 120,
    "back_porch_cost_sf": 35.0,
    "storage_sqft": 40,
    "storage_cost_sf": 45.0,
    "additional_foundation_cost": 0,
    
    "gross_monthly_rent": 1650,
    "target_dscr_rate": 1.20,
    "vacancy_rate_pct": 5.0,
    "opex_rate_pct": 30.0,
    
    "const_ltv_pct": 85.0,
    "build_months": 9,
    "const_rate_pct": 8.5,
    "avg_draw_pct": 50.0,
    "const_closing_fee": 6000,
    
    # Construction Lender DSCR Stress Constraints
    "const_bank_rent": 1500,
    "const_bank_opex_pct": 35.0,
    "const_bank_vac_pct": 7.0,
    "const_bank_dscr": 1.25,
    "const_bank_qual_rate_pct": 7.5,
    "const_bank_amort_yrs": 30,
    "reserve_accrual_pct": 100.0,
    
    "refi_ltv_pct": 80.0,
    "refi_term_years": 30,
    "base_refi_rate_pct": 6.5,
    "refi_closing_fee": 3650,
    "apply_buydown": False,
    "buydown_pts": 2.0,
    
    "gc_fee_mode": "Percentage of Hard Costs (%)",
    "gc_fee_pct": 10.0,
    "custom_gc_fee": 20000,
    "land_basis": 15000,
    
    "appraisal_mode": "Income Approach (GRM)",
    "target_grm": 10.5,
    
    "cost_calc_mode": "Reverse-Engineer from Appraisal",
    "base_direct_cost_sf": 74.0,
    "lot_cost_pct": 18.0,
    "margin_pct": 20.0,
    "sales_pct": 8.0,
    "finance_pct": 4.0,
    "pdf_include_sublevels": True,
    
    "comp_struct_sf": 200,
    "comp_front_sf": 60,
    "comp_back_sf": 120,
    "comp_storage_sf": 40
}

def load_defaults():
    if os.path.exists(DEFAULT_FILE):
        try:
            with open(DEFAULT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return HARDCODED_DRIVERS

# Load active defaults and initialize session state BEFORE rendering UI
GLOBAL_DRIVERS = load_defaults()
for key, value in GLOBAL_DRIVERS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "comp_address" not in st.session_state: st.session_state.comp_address = ""
if "comp_price" not in st.session_state: st.session_state.comp_price = 182600
if "comp_heated_sf" not in st.session_state: st.session_state.comp_heated_sf = 1150
if "raw_api_data" not in st.session_state: st.session_state.raw_api_data = None


# ==========================================
# --- SIDEBAR (Live Underwriting Controls) ---
# ==========================================
st.sidebar.header("Master Model Drivers")

with st.sidebar.container():
    st.subheader("1. Project Scale")
    st.number_input("Number of Units (Doors)", min_value=1, step=1, format="%d", key="units")

with st.sidebar.container():
    st.subheader("2. Physical Footprint & Aux Costs")
    st.number_input("Heated SqFt per Unit", step=50, format="%d", key="sqft")
    st.selectbox("Aux Structure Type", ["Carport", "Garage"], key="structure_type")
    st.number_input(f"{st.session_state.structure_type} SqFt per Unit", step=25, format="%d", key="struct_sqft")
    st.slider(f"{st.session_state.structure_type} Cost / SF ($)", min_value=15.0, max_value=90.0, step=1.0, key="base_struct_cost_sf")
    st.number_input("Front Porch SqFt", step=10, format="%d", key="front_porch_sqft")
    st.slider("Front Porch Cost / SF ($)", min_value=15.0, max_value=70.0, step=1.0, key="front_porch_cost_sf")
    st.number_input("Back Porch SqFt", step=10, format="%d", key="back_porch_sqft")
    st.slider("Back Porch Cost / SF ($)", min_value=15.0, max_value=70.0, step=1.0, key="back_porch_cost_sf")
    st.number_input("Storage Room SqFt", step=5, format="%d", key="storage_sqft")
    st.slider("Storage Room Cost / SF ($)", min_value=15.0, max_value=90.0, step=1.0, key="storage_cost_sf")
    st.number_input("Additional Foundation / Elevation Cost ($)", step=500, format="%d", key="additional_foundation_cost")

with st.sidebar.container():
    st.subheader("3. Takeout Appraisal Methodology")
    st.radio("Valuation Mode", ["Sales Comp (Price/SF)", "Income Approach (GRM)"], key="appraisal_mode")
    if st.session_state.appraisal_mode == "Income Approach (GRM)":
        st.number_input("Gross Rent Multiplier (GRM)", min_value=4.0, max_value=25.0, step=0.1, key="target_grm")

with st.sidebar.container():
    st.subheader("4. Cost Target Mode (Reverse Engineer)")
    st.radio("Calculation Logic", ["Manual Set (Heated SF)", "Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"], key="cost_calc_mode")
    if st.session_state.cost_calc_mode == "Manual Set (Heated SF)":
        st.slider("Direct Build Cost / SF ($)", min_value=40.0, max_value=150.0, step=1.0, key="base_direct_cost_sf")
    else:
        st.slider("Finished Lot Cost (%)", min_value=0.0, max_value=30.0, step=0.5, key="lot_cost_pct")
        st.slider("Gross Margin (O&P) (%)", min_value=0.0, max_value=30.0, step=0.5, key="margin_pct")
        st.slider("Sales & Marketing (%)", min_value=0.0, max_value=15.0, step=0.5, key="sales_pct")
        st.slider("Soft Costs & Finance (%)", min_value=0.0, max_value=15.0, step=0.5, key="finance_pct")

with st.sidebar.container():
    st.subheader("5. GC Fee & Land Costs")
    st.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"], key="gc_fee_mode")
    if st.session_state.gc_fee_mode == "Percentage of Hard Costs (%)":
        st.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, step=0.5, key="gc_fee_pct")
    else:
        st.number_input("Total Consolidated GC Fee ($)", step=1000, format="%d", key="custom_gc_fee")
    st.number_input("Land Basis per Lot ($)", step=1000, format="%d", key="land_basis")

with st.sidebar.container():
    st.subheader("6. Financing & Operations")
    st.number_input("Gross Monthly Rental Income per Unit ($)", step=50, format="%d", key="gross_monthly_rent")
    st.number_input("Target Lender DSCR Rate", min_value=1.0, max_value=1.5, step=0.05, key="target_dscr_rate")
    st.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, step=1.0, key="vacancy_rate_pct")
    st.slider("Operating Expenses (OpEx) Rate of EGI (%)", min_value=15.0, max_value=50.0, step=1.0, key="opex_rate_pct")
    
    st.slider("Construction Loan LTC / LTV (%)", min_value=60.0, max_value=100.0, step=5.0, key="const_ltv_pct")
    st.slider("Construction Duration (Months)", min_value=3, max_value=18, step=1, key="build_months")
    st.slider("Construction Loan Rate (%)", min_value=4.0, max_value=14.0, step=0.5, key="const_rate_pct")
    st.slider("Avg Draw Utilization (%)", min_value=20.0, max_value=100.0, step=5.0, key="avg_draw_pct")
    st.number_input("Const Loan Closing Fee ($ total)", step=500, format="%d", key="const_closing_fee")
    
    st.slider("Refinance LTV (%)", min_value=60.0, max_value=85.0, step=5.0, key="refi_ltv_pct")
    st.selectbox("Amortization Term (Years)", [15, 20, 25, 30], key="refi_term_years")
    st.slider("Base Refi Interest Rate (%)", min_value=4.0, max_value=10.0, step=0.25, key="base_refi_rate_pct")
    st.number_input("Refinance Closing Fee ($ total)", step=250, format="%d", key="refi_closing_fee")
    st.checkbox("Apply Interest Rate Buydown Points?", key="apply_buydown")
    if st.session_state.apply_buydown:
        st.number_input("Discount Points", min_value=0.0, max_value=5.0, step=0.5, key="buydown_pts")
        net_rate = max(0.01, (st.session_state.base_refi_rate_pct / 100.0) - (st.session_state.buydown_pts * 0.0025))
        st.markdown(f"📉 **Buydown Net Rate:** `{net_rate*100:.3f}%`")

with st.sidebar.container():
    st.subheader("7. Const. Lender DSCR Limits")
    st.number_input("Bank Underwriting Rent ($)", step=50, format="%d", key="const_bank_rent")
    st.slider("Bank Underwriting OpEx (%)", min_value=15.0, max_value=50.0, step=1.0, key="const_bank_opex_pct")
    st.slider("Bank Underwriting Vacancy (%)", min_value=0.0, max_value=15.0, step=1.0, key="const_bank_vac_pct")
    st.number_input("Bank Target DSCR", min_value=1.0, max_value=1.5, step=0.05, key="const_bank_dscr")
    st.slider("Bank Qualifying Rate (%)", min_value=4.0, max_value=14.0, step=0.25, key="const_bank_qual_rate_pct")
    st.selectbox("Bank Amortization (Years)", [15, 20, 25, 30], key="const_bank_amort_yrs")

with st.sidebar.container():
    st.subheader("PDF Export Options")
    st.checkbox("Include Detailed Sub-Levels in PDF Report", key="pdf_include_sublevels")


# ==========================================
# --- ACTIVE VARIABLE EXTRACTION FOR MATH ---
# ==========================================
units = st.session_state.units
sqft = st.session_state.sqft
struct_sqft = st.session_state.struct_sqft
base_struct_cost_sf = st.session_state.base_struct_cost_sf
front_porch_sqft = st.session_state.front_porch_sqft
front_porch_cost_sf = st.session_state.front_porch_cost_sf
back_porch_sqft = st.session_state.back_porch_sqft
back_porch_cost_sf = st.session_state.back_porch_cost_sf
storage_sqft = st.session_state.storage_sqft
storage_cost_sf = st.session_state.storage_cost_sf
additional_foundation_cost = st.session_state.additional_foundation_cost

gross_monthly_rent = st.session_state.gross_monthly_rent
target_dscr_rate = st.session_state.target_dscr_rate
vacancy_rate = st.session_state.vacancy_rate_pct / 100.0
opex_rate = st.session_state.opex_rate_pct / 100.0
const_ltv = st.session_state.const_ltv_pct / 100.0
build_months = st.session_state.build_months
const_rate = st.session_state.const_rate_pct / 100.0
avg_draw_pct = st.session_state.avg_draw_pct / 100.0
const_closing_fee = st.session_state.const_closing_fee

const_bank_rent = st.session_state.const_bank_rent
const_bank_opex_pct = st.session_state.const_bank_opex_pct / 100.0
const_bank_vac_pct = st.session_state.const_bank_vac_pct / 100.0
const_bank_dscr = st.session_state.const_bank_dscr
const_bank_qual_rate = st.session_state.const_bank_qual_rate_pct / 100.0
const_bank_amort_yrs = st.session_state.const_bank_amort_yrs

refi_ltv = st.session_state.refi_ltv_pct / 100.0
refi_term_years = st.session_state.refi_term_years
base_refi_rate = st.session_state.base_refi_rate_pct / 100.0
refi_closing_fee = st.session_state.refi_closing_fee
apply_buydown = st.session_state.apply_buydown
buydown_pts = st.session_state.buydown_pts
net_refi_rate = max(0.01, base_refi_rate - (buydown_pts * 0.0025)) if apply_buydown else base_refi_rate

gc_fee_mode = st.session_state.gc_fee_mode
gc_fee_pct = st.session_state.gc_fee_pct / 100.0
custom_gc_fee = st.session_state.custom_gc_fee
land_basis = st.session_state.land_basis
appraisal_mode = st.session_state.appraisal_mode
target_grm = st.session_state.target_grm
cost_calc_mode = st.session_state.cost_calc_mode
base_direct_cost_sf = st.session_state.base_direct_cost_sf
lot_cost_pct = st.session_state.lot_cost_pct / 100.0
margin_pct = st.session_state.margin_pct / 100.0
sales_pct = st.session_state.sales_pct / 100.0
finance_pct = st.session_state.finance_pct / 100.0

comp_price = st.session_state.comp_price
comp_heated_sf = st.session_state.comp_heated_sf
comp_struct_sf = st.session_state.comp_struct_sf
comp_front_sf = st.session_state.comp_front_sf
comp_back_sf = st.session_state.comp_back_sf
comp_storage_sf = st.session_state.comp_storage_sf


# ==========================================
# --- CORE PRE-RENDER MATHEMATICS ---
# ==========================================
struct_total_cost = struct_sqft * base_struct_cost_sf
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf
storage_cost = storage_sqft * storage_cost_sf
our_aux_cost_total = struct_total_cost + front_porch_cost + back_porch_cost + storage_cost + additional_foundation_cost

comp_total_sf = comp_heated_sf + comp_struct_sf + comp_front_sf + comp_back_sf + comp_storage_sf
raw_comp_price_sf = comp_price / comp_heated_sf if comp_heated_sf > 0 else 0
comp_aux_value = (comp_struct_sf * base_struct_cost_sf) + (comp_front_sf * front_porch_cost_sf) + (comp_back_sf * back_porch_cost_sf) + (comp_storage_sf * storage_cost_sf)
comp_isolated_heated_value = max(0, comp_price - comp_aux_value)
isolated_heated_rate = comp_isolated_heated_value / comp_heated_sf if comp_heated_sf > 0 else 0

if appraisal_mode == "Income Approach (GRM)":
    arv_per_unit = (gross_monthly_rent * 12) * target_grm
else:
    arv_per_unit = (isolated_heated_rate * sqft) + our_aux_cost_total

if cost_calc_mode == "Manual Set (Heated SF)":
    target_heated_hard_cost = base_direct_cost_sf * sqft
    target_total_hard_cost = target_heated_hard_cost + our_aux_cost_total
    comp_equivalent_arv = 0 
elif cost_calc_mode == "Reverse-Engineer from Appraisal":
    target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)
    target_total_hard_cost = arv_per_unit * target_hard_cost_pct
    target_heated_hard_cost = max(0, target_total_hard_cost - our_aux_cost_total)
    base_direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0
    comp_equivalent_arv = arv_per_unit
else: # Reverse from Comp
    comp_equivalent_arv = (isolated_heated_rate * sqft) + our_aux_cost_total
    target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)
    target_total_hard_cost = comp_equivalent_arv * target_hard_cost_pct
    target_heated_hard_cost = max(0, target_total_hard_cost - our_aux_cost_total)
    base_direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0

direct_cost_sf = base_direct_cost_sf
struct_cost_sf = base_struct_cost_sf

total_under_roof_sqft = sqft + struct_sqft + front_porch_sqft + back_porch_sqft + storage_sqft
heated_hard_cost = sqft * direct_cost_sf
blended_cost_per_sf = (heated_hard_cost + our_aux_cost_total) / total_under_roof_sqft if total_under_roof_sqft > 0 else 0
total_hard_cost = target_total_hard_cost * units if cost_calc_mode in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"] else (heated_hard_cost + our_aux_cost_total) * units
total_arv = arv_per_unit * units
loan_total = total_arv * refi_ltv

default_gcond = total_hard_cost * 0.05
fee_basis = total_hard_cost + default_gcond
default_gc_fee = custom_gc_fee if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else fee_basis * gc_fee_pct
default_premium = total_hard_cost * 0.05
total_land_default = land_basis * units
default_soft_cost_per_unit = 5500
total_soft_default = default_soft_cost_per_unit * units

# =========================================================================
# --- ACCURATE CONSTRUCTION SIZING, DSCR CAP & CAPITALIZED INTEREST ---
# =========================================================================
total_const_default = fee_basis + default_gc_fee + default_premium
total_project_costs_ex_interest_default = total_land_default + total_const_default + total_soft_default + const_closing_fee

# 1. Determine Bank's Capped Loan Size (DSCR Constraint)
cb_noi = (const_bank_rent * units * 12.0) * (1.0 - const_bank_vac_pct) * (1.0 - const_bank_opex_pct)
cb_max_annual_ds = cb_noi / const_bank_dscr
cb_monthly_rate = const_bank_qual_rate / 12.0
cb_term_months = const_bank_amort_yrs * 12
if cb_monthly_rate > 0:
    max_const_loan_dscr = (cb_max_annual_ds / 12.0) * ((1.0 - (1.0 + cb_monthly_rate)**-cb_term_months) / cb_monthly_rate)
else:
    max_const_loan_dscr = (cb_max_annual_ds / 12.0) * cb_term_months

# 2. Mathematically Pure Unconstrained Construction LTC Loan (includes interest carry)
time_years = build_months / 12.0
interest_multiplier = const_ltv * avg_draw_pct * const_rate * time_years

if interest_multiplier < 1.0:
    normal_const_loan = (const_ltv * total_project_costs_ex_interest_default) / (1.0 - interest_multiplier)
else:
    normal_const_loan = total_project_costs_ex_interest_default * const_ltv

# 3. Apply Bank DSCR Cap
actual_const_loan = min(normal_const_loan, max_const_loan_dscr)

# 4. Actual Interest Accrual (Derived directly from actual bank proceeds)
default_carry_int = actual_const_loan * avg_draw_pct * const_rate * time_years
carry_int_base = default_carry_int
carry_int_reserve = 0.0  # Sponsor equity does not accrue bank loan interest

# 5. Shortfall Determination (Day-1 Equity Injection required)
gap_proceeds = max(0.0, normal_const_loan - actual_const_loan)
dscr_shortfall_reserve = gap_proceeds

# 6. Total Project Basis & Refinance Outlays
default_buydown_cost = loan_total * (buydown_pts / 100.0) if apply_buydown else 0
total_const = total_hard_cost + default_gcond + default_gc_fee + default_premium
total_project_costs_ex_interest = total_land_default + total_const + total_soft_default + const_closing_fee
total_project_basis = total_project_costs_ex_interest + default_carry_int + refi_closing_fee + default_buydown_cost

# Seed Capital (Total construction cash requirement minus proceeds provided by construction lender)
seed_capital = (total_project_costs_ex_interest + default_carry_int) - actual_const_loan

# --- REFINANCE & OPERATING UNDERWRITING ---
monthly_interest_rate = net_refi_rate / 12.0
total_payments = refi_term_years * 12
if monthly_interest_rate > 0:
    monthly_pi_per_unit = (loan_total / units) * (monthly_interest_rate * (1 + monthly_interest_rate)**total_payments) / ((1 + monthly_interest_rate)**total_payments - 1)
else:
    monthly_pi_per_unit = (loan_total / units) / total_payments if total_payments > 0 else 0

total_monthly_pi = monthly_pi_per_unit * units
total_gross_monthly_income = gross_monthly_rent * units
monthly_vacancy_loss = total_gross_monthly_income * vacancy_rate
annual_vacancy_loss = monthly_vacancy_loss * 12.0
effective_gross_monthly_income = total_gross_monthly_income - monthly_vacancy_loss
annual_egi = effective_gross_monthly_income * 12.0
annual_opex = annual_egi * opex_rate
annual_noi = annual_egi - annual_opex
monthly_noi = annual_noi / 12.0

annual_debt_service = total_monthly_pi * 12.0
actual_dscr = annual_noi / annual_debt_service if annual_debt_service > 0 else 0
monthly_cash_flow = monthly_noi - total_monthly_pi
dscr_variance = actual_dscr - target_dscr_rate

# Refinance Waterfall at Title Close
net_cash_at_closing = loan_total - actual_const_loan - default_carry_int - refi_closing_fee - default_buydown_cost
cash_surplus = net_cash_at_closing - seed_capital
retained_equity = total_arv - loan_total
day1_wealth = default_gc_fee + max(0.0, cash_surplus) + retained_equity


# ==========================================
# --- PAGE HEADER ---
# ==========================================
st.title("🏗️ BTR Pro Forma Engine")
st.markdown("### Wickboldt Capital — *Today's Foundation. Tomorrow's Legacy.*")
st.divider()

tab_main, tab_admin = st.tabs(["📊 Main Underwriting Dashboard", "⚙️ Admin Access"])

# ==========================================
# --- ADMIN TAB (Save Defaults) ---
# ==========================================
with tab_admin:
    st.markdown("### 🔒 Master Underwriting Settings")
    st.info("The left sidebar controls your live deal parameters. If you have customized the sidebar and want those settings to automatically load as the new baseline every time you open this app, enter your PIN and save them below.")
    
    admin_pwd = st.text_input("Enter Admin PIN", type="password")
    
    if admin_pwd == "admin":
        st.success("Access Granted.")
        if st.button("💾 Save Current Sidebar Settings as Global Defaults", type="primary"):
            new_defaults = {k: st.session_state[k] for k in HARDCODED_DRIVERS.keys() if k in st.session_state}
            with open(DEFAULT_FILE, "w") as f:
                json.dump(new_defaults, f)
            st.success("Success! Your current sidebar settings have been saved. They will now load automatically as defaults.")


# ==========================================
# --- MAIN TAB ---
# ==========================================
with tab_main:
    # --- PROJECT INFO ---
    st.markdown("### 📋 Project Information")
    top_col1, top_col2 = st.columns([2, 2])
    project_name = top_col1.text_input("Project Title", placeholder="e.g. Phase 1 - 24-Lot Build-to-Rent")
    project_address = top_col2.text_input("Project Address", placeholder="e.g. Rogers Moore Parkway, Hammond, LA")
    report_date = datetime.now().strftime("%B %d, %Y")

    sub_col1, sub_col2, sub_col3 = st.columns([1, 1, 2])
    project_beds = sub_col1.number_input("Beds per Unit", min_value=1, value=3, step=1)
    project_baths = sub_col2.number_input("Baths per Unit", min_value=1.0, value=2.0, step=0.5)
    download_placeholder = sub_col3.empty()
    st.divider()

    ui_top_metrics = st.container()
    ui_op_metrics = st.container()
    ui_decision_dashboard = st.container()
    st.divider()

    # --- COMP TOOL ---
    st.markdown("### 🔍 Market Comp Valuation & Blended Rate Benchmark")
    comp_entry_mode = st.radio("Comparable Data Entry Mode", ["Manual Entry", "RentCast Live API Fetch"], horizontal=True)

    if comp_entry_mode == "RentCast Live API Fetch":
        rc_col1, rc_col2 = st.columns([4, 1])
        search_address = rc_col1.text_input("Property Address", placeholder="e.g. 1103 S Spruce St, Hammond, LA 70403")
        with st.expander("⚙️ API Configuration (Optional)"):
            manual_key = st.text_input("RentCast API Key Override", type="password")

        if rc_col2.button("Fetch Live Data", use_container_width=True):
            if search_address:
                rentcast_key = manual_key or os.environ.get("RENTCAST_API_KEY") or st.secrets.get("RENTCAST_API_KEY", "")
                if rentcast_key:
                    try:
                        with st.spinner("Fetching live data from RentCast MLS..."):
                            api_url = "https://api.rentcast.io/v1/properties"
                            headers = {"X-Api-Key": rentcast_key.strip(), "accept": "application/json"}
                            response = requests.get(api_url, headers=headers, params={"address": search_address.strip()})
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state.raw_api_data = data 
                                if data:
                                    prop = data[0]
                                    if prop.get("price") or prop.get("lastSalePrice"):
                                        st.session_state.comp_price = int(prop.get("price") or prop.get("lastSalePrice"))
                                    if prop.get("squareFootage"):
                                        st.session_state.comp_heated_sf = int(prop.get("squareFootage"))
                                    if prop.get("formattedAddress"):
                                        st.session_state.comp_address = str(prop.get("formattedAddress"))
                                    st.success(f"Imported: {st.session_state.comp_address}")
                                    st.rerun()
                                else:
                                    st.error("No exact match found.")
                    except Exception as e:
                        st.error(f"API Error: {e}")

    st.markdown("##### 1. Primary Comp Metrics")
    col_addr, col_price, col_hsf = st.columns([2, 1, 1])
    if comp_entry_mode == "RentCast Live API Fetch":
        col_addr.text_input("Comparable Property Address", value=st.session_state.comp_address, disabled=True)
        col_price.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, disabled=True)
        col_hsf.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, disabled=True)
    else:
        c_add = col_addr.text_input("Comparable Property Address", value=st.session_state.comp_address)
        c_prc = col_price.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, step=1000)
        c_hsf = col_hsf.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, step=50)
        if c_add != st.session_state.comp_address or c_prc != st.session_state.comp_price or c_hsf != st.session_state.comp_heated_sf:
            st.session_state.comp_address = c_add; st.session_state.comp_price = c_prc; st.session_state.comp_heated_sf = c_hsf
            st.rerun()

    st.markdown("##### 2. Comp Auxiliary Spaces (Always Editable)")
    c_aux1, c_aux2, c_aux3, c_aux4 = st.columns(4)
    c_aux1.number_input("Comp Aux. SF (Garage/Carport)", step=25, format="%d", key="comp_struct_sf")
    c_aux2.number_input("Comp Front Porch SF", step=10, format="%d", key="comp_front_sf")
    c_aux3.number_input("Comp Back Porch SF", step=10, format="%d", key="comp_back_sf")
    c_aux4.number_input("Comp Storage Room SF", step=5, format="%d", key="comp_storage_sf")

    if st.session_state.comp_address:
        st.caption(f"📍 **Active Comp:** {st.session_state.comp_address} | Isolated Heated Rate: **${isolated_heated_rate:.2f} / SF**")
    else:
        st.caption(f"📊 Isolated Heated Rate: **${isolated_heated_rate:.2f} / SF**")

    with st.expander("🧮 View Comp Math Audit & Raw API Data", expanded=False):
        st.markdown("**1. Raw Retail Heated Rate (Unadjusted)**")
        st.code(f"${comp_price:,.0f} ÷ {comp_heated_sf:,.0f} SF = ${raw_comp_price_sf:.2f} / SF")
        st.markdown("**2. True Isolated Heated Shell Rate**")
        st.code(f"(${comp_price:,.0f} - ${comp_aux_value:,.0f} Aux) ÷ {comp_heated_sf:,.0f} SF = ${isolated_heated_rate:.2f} / SF")
        if st.session_state.raw_api_data and comp_entry_mode == "RentCast Live API Fetch":
            st.json(st.session_state.raw_api_data)
    st.divider()

    # --- GRANULAR BUILDER ---
    st.markdown("### 🧱 Granular Direct Hard Cost Buildup")
    granular_mode = st.radio("Buildup Entry Mode", ["Auto-Proportional (Linked to Master Model)", "Manual Custom Entry (Bottom-Up)"], horizontal=True)

    raw_heated_divs = [
        ("DIVISION 1: FOUNDATION & CONCRETE", 9.50, True, ""),
        ("DIVISION 2: FRAMING & STRUCTURAL SHELL", 18.50, True, ""),
        ("DIVISION 3: EXTERIOR ENVELOPE & ROOFING", 10.00, True, ""),
        ("DIVISION 4: MECHANICAL, ELECTRICAL, PLUMBING", 15.50, True, ""),
        ("DIVISION 5: INSULATION & DRYWALL", 6.50, True, ""),
        ("DIVISION 6: INTERIOR FINISHES & CABINETS", 10.50, True, ""),
        ("DIVISION 7: APPLIANCES & SPECIALTIES", 1.50, True, ""),
        ("DIVISION 8: EXTERIOR FLATWORK & SITE", 2.00, True, "")
    ]
    raw_struct_divs = [("AUXILIARY: CARPORT / GARAGE", 31.00, True)]
    pdf_granular_data = []

    if granular_mode == "Auto-Proportional (Linked to Master Model)":
        st.markdown(f"#### 1. Heated Living Area ({sqft} SF @ ${direct_cost_sf:.2f} / SF)")
        h_data = {"Division / Trade Level": [], "Live Cost / SF": [], "Per Unit Cost": []}
        for name, base_val, is_header, scope in raw_heated_divs:
            live_sf = direct_cost_sf * (base_val / 74.0)
            h_data["Division / Trade Level"].append(name)
            h_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            h_data["Per Unit Cost"].append(f"${live_sf * sqft:,.0f}")
            pdf_granular_data.append((name, live_sf, live_sf * sqft, live_sf * sqft * units, True))
        st.dataframe(pd.DataFrame(h_data), hide_index=True, use_container_width=True)
        
        st.markdown(f"#### 2. {st.session_state.structure_type} Auxiliary ({struct_sqft} SF @ ${struct_cost_sf:.2f} / SF)")
        s_data = {"Component Level": [], "Live Cost / SF": [], "Per Unit Cost": []}
        for name, base_val, is_header in raw_struct_divs:
            live_sf = struct_cost_sf * (base_val / 31.0)
            s_data["Component Level"].append(name)
            s_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            s_data["Per Unit Cost"].append(f"${live_sf * struct_sqft:,.0f}")
        st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True)
    else:
        st.markdown(f"#### 1. Heated Living Area ({sqft} SF)")
        hl_heated = [{"Division / Trade Level": name, "Cost / SF": base_direct_cost_sf * (base/74.0)} for name, base, is_h, scope in raw_heated_divs]
        edited_h = st.data_editor(pd.DataFrame(hl_heated), column_config={"Division / Trade Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True)
        direct_cost_sf = edited_h["Cost / SF"].sum()
        for index, row in edited_h.iterrows():
            live_sf = row["Cost / SF"]
            pdf_granular_data.append((row["Division / Trade Level"], live_sf, live_sf * sqft, live_sf * sqft * units, True))
        
        st.markdown(f"#### 2. {st.session_state.structure_type} Auxiliary ({struct_sqft} SF)")
        hl_struct = [{"Component Level": name, "Cost / SF": base_struct_cost_sf * (base/31.0)} for name, base, is_h in raw_struct_divs]
        edited_s = st.data_editor(pd.DataFrame(hl_struct), column_config={"Component Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True)
        struct_cost_sf = edited_s["Cost / SF"].sum()

    st.markdown(f"#### 3. Auxiliary, Foundation & Outdoor Living")
    p_data = {
        "Component": ["Front Porch", "Back Porch", "Storage Room", "Addit. Foundation / Elevation", "TOTAL AUX/OUTDOOR"],
        "Area (SF)": [f"{front_porch_sqft} SF", f"{back_porch_sqft} SF", f"{storage_sqft} SF", "Site Specific", "Total"],
        "Cost / SF": [f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", f"${storage_cost_sf:.2f}", "-", "-"],
        "Total Amount": [f"${front_porch_cost:,.0f}", f"${back_porch_cost:,.0f}", f"${storage_cost:,.0f}", f"${additional_foundation_cost:,.0f}", f"${our_aux_cost_total:,.0f}"]
    }
    st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)
    st.divider()
    
    # --- BANK DSCR STRESS TEST BREAKDOWN ---
    st.markdown("### 🏦 Construction Lender Stress-Test & DSCR Limit")
    st.caption("Banks apply higher OpEx, higher vacancy, and worst-case interest rates to cap your maximum construction loan. If this cap is lower than your target Loan-to-Cost, an upfront Day-1 equity injection is required.")
    
    stress_test_data = {
        "Bank Underwriting Step": [
            "1. Gross Potential Rent (Bank Model)",
            "2. Less: Bank Vacancy Rate",
            "3. Less: Bank Operating Expenses (OpEx)",
            "4. Bank Qualified Net Operating Income (NOI)",
            "5. Target Construction DSCR Constraint",
            "6. Maximum Allowed Annual Debt Service",
            "7. Maximum DSCR-Supported Loan Proceeds",
            "8. Standard Baseline Const. Loan (LTC Request)",
            "9. Final Capped Construction Loan Proceeds",
            "10. Capital Gap (Requires Day-1 Sponsor Equity)"
        ],
        "Value": [
            f"${const_bank_rent * units * 12:,.0f} / yr",
            f"{const_bank_vac_pct*100:.1f}%",
            f"{const_bank_opex_pct*100:.1f}% of EGI",
            f"${cb_noi:,.0f} / yr",
            f"{const_bank_dscr:.2f}x",
            f"${cb_max_annual_ds:,.0f} / yr",
            f"${max_const_loan_dscr:,.0f} (@ {const_bank_qual_rate*100:.2f}%)",
            f"${normal_const_loan:,.0f} (@ {const_ltv*100:.1f}% Target)",
            f"${actual_const_loan:,.0f}",
            f"${gap_proceeds:,.0f}"
        ]
    }
    st.dataframe(pd.DataFrame(stress_test_data), hide_index=True, use_container_width=True)

    if dscr_shortfall_reserve > 0:
        st.error(f"**Shortfall Detected:** The bank has capped your loan **${gap_proceeds:,.0f}** below your baseline LTC request due to qualifying DSCR constraints. You must bring a total of **${seed_capital:,.0f}** in Day-1 Seed Capital to close the construction loan.")
    else:
        st.success("**Loan Unconstrained:** Your DSCR-supported loan limit is higher than your requested LTC baseline. No additional shortfall equity is required.")
    st.divider()

    # --- LEDGER & CAP STACK ---
    st.markdown("### 📊 Detailed Construction Cost & Capital Ledger")
    ledger_mode = st.radio("Ledger Input Mode", ["Sync with Global Parameters", "Manual Ledger Override"], horizontal=True)

    st.markdown("#### 1. Direct Hard Costs (Driven by Granular Builder)")
    direct_data = {
        "Cost Category": ["Heated Living Area", f"{st.session_state.structure_type} Auxiliary", "Front Porch", "Back Porch", "Storage Room", "Addit. Foundation / Elevation", "TOTAL DIRECT HARD COSTS"],
        "Area / Metric": [f"{sqft:,.0f} SF", f"{struct_sqft:,.0f} SF", f"{front_porch_sqft:,.0f} SF", f"{back_porch_sqft:,.0f} SF", f"{storage_sqft:,.0f} SF", "Site Specific", f"{total_under_roof_sqft:,.0f} SF Under Roof"],
        "Cost / SF": [f"${direct_cost_sf:.2f}", f"${struct_cost_sf:.2f}", f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", f"${storage_cost_sf:.2f}", "-", f"${blended_cost_per_sf:.2f} (Blended)"],
        "Total Amount ($)": [heated_hard_cost * units, struct_total_cost * units, front_porch_cost * units, back_porch_cost * units, storage_cost * units, additional_foundation_cost * units, total_hard_cost]
    }
    st.dataframe(pd.DataFrame(direct_data).style.format({"Total Amount ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)

    st.markdown("#### 2. Indirect, Land & Capital Costs")
    indirects_data = [
        {"Cost Category": "General Conditions", "Metric / Basis": "5.0% of Direct", "Amount ($)": default_gcond},
        {"Cost Category": "GC Management Fee", "Metric / Basis": "Flat Fee" if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else f"{gc_fee_pct*100:.1f}% Basis", "Amount ($)": default_gc_fee},
        {"Cost Category": "BTR Buying Power Premium", "Metric / Basis": "5.0% of Direct", "Amount ($)": default_premium},
        {"Cost Category": "Land Acquisition Basis", "Metric / Basis": f"${land_basis:,.0f} / Lot", "Amount ($)": total_land_default},
        {"Cost Category": "Soft Costs & Permitting", "Metric / Basis": f"${default_soft_cost_per_unit:,.0f} / Unit", "Amount ($)": total_soft_default},
        {"Cost Category": "Construction Loan Closing Fee", "Metric / Basis": "Flat Fee", "Amount ($)": const_closing_fee},
        {"Cost Category": f"Const. Loan Interest ({build_months} Mos)", "Metric / Basis": f"{avg_draw_pct*100:.0f}% Avg Draw", "Amount ($)": carry_int_base},
        {"Cost Category": "Takeout Refinance Closing Fee", "Metric / Basis": "Flat Fee", "Amount ($)": refi_closing_fee},
        {"Cost Category": "Rate Buydown Points Cost", "Metric / Basis": f"{buydown_pts} Points", "Amount ($)": default_buydown_cost}
    ]
    
    if ledger_mode == "Manual Ledger Override":
        st.caption("✏️ **Manual Mode Active:** Edit the amounts in the table below.")
        edited_df = st.data_editor(pd.DataFrame(indirects_data), column_config={"Amount ($)": st.column_config.NumberColumn(format="$%.2f", min_value=0.0)}, disabled=["Cost Category", "Metric / Basis"], hide_index=True, use_container_width=True)
    else:
        st.dataframe(pd.DataFrame(indirects_data).style.format({"Amount ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)

    st.markdown(f"### 🎯 TOTAL PROJECT BASIS: **${total_project_basis:,.0f}** *(${total_project_basis/units:,.0f} / Door)*")
    st.divider()

    # ==========================================
    # --- POPULATE INVISIBLE DASHBOARDS ---
    # ==========================================
    with ui_top_metrics:
        st.markdown("### 🏗️ Project Capital & Valuation Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Takeout Loan Proceeds", f"${loan_total:,.0f}", f"Const. Loan: ${actual_const_loan:,.0f}", delta_color="off")
        if cash_surplus >= 0:
            deal_health_color = "normal" 
            surplus_title = "Tax-Free Cash Surplus"
            surplus_delta = "Capital Recovered"
        else:
            deal_health_color = "inverse" 
            surplus_title = "Trapped Seed Capital"
            surplus_delta = "Loss at Closing"
        col2.metric("Total Project Basis", f"${total_project_basis:,.0f}", f"${total_project_basis/units:,.0f} per door", delta_color=deal_health_color)
        col3.metric("Under-Roof Blended Cost", f"${blended_cost_per_sf:.2f} / SF", f"{total_under_roof_sqft:,} Total SF Under Roof")
        col4.metric(surplus_title, f"${cash_surplus:,.0f}", surplus_delta, delta_color=deal_health_color)

    with ui_op_metrics:
        st.markdown("### 🏢 Operating & DSCR Metrics")
        op1, op2, op3, op4 = st.columns(4)
        arv_label = "Derived Unit ARV (Price/SF)" if appraisal_mode == "Sales Comp (Price/SF)" else "Derived Unit ARV (GRM)"
        op1.metric(arv_label, f"${arv_per_unit:,.0f}", f"${total_arv:,.0f} Total ARV")
        op2.metric("Actual DSCR Rate", f"{actual_dscr:.2f}x", f"Target: {target_dscr_rate:.2f}x", delta_color="normal" if actual_dscr >= target_dscr_rate else "inverse")
        op3.metric("Monthly Cash Flow", f"${monthly_cash_flow:,.0f} /mo", f"${monthly_cash_flow*12:,.0f} Annual", delta_color="normal" if monthly_cash_flow >= 0 else "inverse")
        op4.metric("Monthly P&I Payment", f"${total_monthly_pi:,.0f} /mo", f"{refi_term_years}Yr @ {net_refi_rate*100:.3f}%")

    with ui_decision_dashboard:
        st.markdown("### 🚦 Go/No-Go Investment Decision Dashboard")
        dscr_pass = actual_dscr >= target_dscr_rate
        cash_pass = cash_surplus >= 0
        dscr_light = "🟢 GREEN LIGHT" if dscr_pass else "🔴 RED LIGHT"
        cash_light = "🟢 GREEN LIGHT" if cash_pass else "🔴 RED LIGHT"

        dash_col1, dash_col2, dash_col3 = st.columns(3)
        dash_col1.metric("DSCR Underwriting Status", dscr_light, f"Actual: {actual_dscr:.2f}x (Target: {target_dscr_rate:.2f}x)", delta_color="normal" if dscr_pass else "inverse")
        dash_col2.metric("Capital Recovery Status", cash_light, f"${cash_surplus:,.0f} at Refi Close", delta_color="normal" if cash_pass else "inverse")
        dash_col3.metric("Day-1 Wealth Creation", f"${day1_wealth:,.0f}", f"${day1_wealth/units:,.0f} per door", delta_color="normal")


    # --- BOTTOM PERFORMANCE SECTIONS ---
    st.markdown("### 💸 Refinance Cash Waterfall & Day-1 Wealth")
    st.caption("This explicit Cash-Out Waterfall shows exactly how the Permanent Loan pays off the Construction phase at the title company, isolating your true Cash Surplus.")
    
    waterfall_data = {
        "Refinance Closing Line Item": [
            "(+) Permanent Takeout Loan Proceeds",
            "(-) Construction Loan Principal Payoff",
            "(-) Const. Loan Accrued Interest Payoff",
            "(-) Refinance Closing Fees",
            "(-) Rate Buydown Points Cost",
            "= Net Cash Distributed to Sponsor at Closing",
            "(-) Initial Sponsor Seed Capital Invested",
            "= Final Tax-Free Cash Surplus / (Trapped Capital)"
        ],
        "Amount ($)": [
            f"${loan_total:,.0f}",
            f"-${actual_const_loan:,.0f}",
            f"-${default_carry_int:,.0f}",
            f"-${refi_closing_fee:,.0f}",
            f"-${default_buydown_cost:,.0f}",
            f"${net_cash_at_closing:,.0f}",
            f"-${seed_capital:,.0f}",
            f"${cash_surplus:,.0f}"
        ]
    }
    st.dataframe(pd.DataFrame(waterfall_data), hide_index=True, use_container_width=True)
    
    wealth_data = {
        "Pocket Component": ["Pocket 1: Active GC Fee Revenue", "Pocket 2: Tax-Free Cash Surplus at Close", "Pocket 3: Retained Asset Equity", "TOTAL DAY-1 CREATED VALUE"],
        "Value ($)": [f"${default_gc_fee:,.0f}", f"${cash_surplus:,.0f}", f"${retained_equity:,.0f}", f"${day1_wealth:,.0f}"]
    }
    st.dataframe(pd.DataFrame(wealth_data), hide_index=True, use_container_width=True)
    st.divider()

    if cost_calc_mode in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"]:
        st.markdown("### 🔄 Retail Comp & Appraisal Reverse-Engineering Breakdown")
        
        reference_price = arv_per_unit if cost_calc_mode == 'Reverse-Engineer from Appraisal' else comp_equivalent_arv
        breakdown_data = {
            "Cost Category": [
                f"Baseline Reference Price (Comp / ARV)", "(-) Finished Lot Cost", "(-) Gross Margin (O&P)", 
                "(-) Sales & Marketing", "(-) Soft Costs & Finance", "= Total Hard Cost Budget", 
                "(-) Fixed Auxiliary & Elevation Costs", "= Available Budget for Heated Shell"
            ],
            "Value ($)": [
                f"${reference_price:,.0f}", 
                f"-${reference_price * lot_cost_pct:,.0f}", 
                f"-${reference_price * margin_pct:,.0f}", 
                f"-${reference_price * sales_pct:,.0f}", 
                f"-${reference_price * finance_pct:,.0f}", 
                f"${target_total_hard_cost:,.0f}", 
                f"-${our_aux_cost_total:,.0f}", 
                f"${target_heated_hard_cost:,.0f}"
            ],
            "Description": [
                "Derived directly from Primary Comp Sale Price or Takeout Appraisal.",
                "Raw land, engineering, road paving, wet/dry utility infrastructure.",
                "Builder gross overhead and corporate net margin.",
                "Realtor commissions, internal sales reps, buyer closing concessions.",
                "Impact fees, plan design, municipal permits, and loan interest carry.",
                "Total budget available for all physical construction.",
                "Locked budget required for specific outdoor/auxiliary footprint and foundation elevation.",
                f"Yields exactly ${base_direct_cost_sf:.2f} / SF across {sqft} Heated SF."
            ]
        }
        st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)
        st.divider()

    st.markdown("### 🏢 Operating Performance Summary")
    dscr_summary_data = {
        "Pro Forma Line Item": [
            "Gross Potential Rent (GPR)", f"(-) Vacancy Loss @ {vacancy_rate*100:.1f}%", "= Effective Gross Income (EGI)", 
            f"(-) Operating Expenses (OpEx) @ {opex_rate*100:.1f}%", "= Net Operating Income (NOI)", "(-) Total Debt Service (P&I)", "= Net Cash Flow",
            "---", "Actual DSCR Rate", "Target Lender DSCR", "DSCR Variance"
        ],
        "Monthly": [
            f"${total_gross_monthly_income:,.2f}", f"-${monthly_vacancy_loss:,.2f}", f"${annual_egi / 12:,.2f}", 
            f"-${annual_opex / 12:,.2f}", f"${monthly_noi:,.2f}", f"-${total_monthly_pi:,.2f}", f"${monthly_cash_flow:,.2f}",
            "---", f"{actual_dscr:.2f}x", f"{target_dscr_rate:.2f}x", f"{dscr_variance:+.2f}x"
        ],
        "Annual": [
            f"${total_gross_monthly_income * 12:,.2f}", f"-${annual_vacancy_loss:,.2f}", f"${annual_egi:,.2f}", 
            f"-${annual_opex:,.2f}", f"${annual_noi:,.2f}", f"${annual_debt_service:,.2f}", f"${monthly_cash_flow * 12:,.2f}",
            "---", f"{actual_dscr:.2f}x", f"{target_dscr_rate:.2f}x", f"{dscr_variance:+.2f}x"
        ]
    }
    st.dataframe(pd.DataFrame(dscr_summary_data), hide_index=True, use_container_width=True)

    # --- PDF GENERATION ENGINE ---
    class EnterpriseReport(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 8, 'Wickboldt Capital | BTR Pro Forma Report', border=0, ln=1, align='C')
            self.set_font('Arial', 'I', 10)
            self.cell(0, 6, "Today's Foundation. Tomorrow's Legacy.", border=0, ln=1, align='C')
            self.line(10, 25, 200, 25)
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()} | Prepared by: Stephen Wickboldt Jr. - Wickboldt Capital', 0, 0, 'C')

    def create_pdf(include_sublevels):
        pdf = EnterpriseReport()
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 12)
        p_name = project_name if project_name else "Untitled Development"
        p_address = project_address if project_address else "TBD"
        pdf.cell(0, 6, f"Project: {p_name}", ln=1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, f"Address: {p_address}", ln=1)
        pdf.cell(0, 6, f"Scale: {units} Unit(s) | {project_beds} Beds / {project_baths} Baths | Under-Roof: {total_under_roof_sqft:,} SF/Unit", ln=1)
        pdf.cell(0, 6, f"Date: {report_date}", ln=1)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 1. Executive Summary & Wealth Creation", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(100, 7, "Total Project Basis:", 0, 0)
        pdf.cell(90, 7, f"${total_project_basis:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, "Total Appraised Value (ARV):", 0, 0)
        pdf.cell(90, 7, f"${total_arv:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, f"Const. Loan Proceeds (Payoff):", 0, 0)
        pdf.cell(90, 7, f"${actual_const_loan:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, f"Takeout Loan Proceeds ({refi_ltv*100:.0f}% LTV):", 0, 0)
        pdf.cell(90, 7, f"${loan_total:,.0f}", 0, 1, 'R')
        
        surplus_label = "Tax-Free Cash Surplus (At Closing):" if cash_surplus >= 0 else "Trapped Seed Capital (At Closing):"
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 7, surplus_label, 0, 0)
        pdf.cell(90, 7, f"${cash_surplus:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, "Total Day-1 Wealth Created:", 0, 0)
        pdf.cell(90, 7, f"${day1_wealth:,.0f}", 0, 1, 'R')
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, " 2. Const. Bank DSCR Limits & Loan Cap", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(100, 7, "Bank Assumed Rent & Target DSCR:", 0, 0)
        pdf.cell(90, 7, f"${const_bank_rent:,.0f}/mo | {const_bank_dscr:.2f}x DSCR", 0, 1, 'R')
        pdf.cell(100, 7, "Bank OpEx & Vacancy Deductions:", 0, 0)
        pdf.cell(90, 7, f"{const_bank_opex_pct*100:.1f}% OpEx | {const_bank_vac_pct*100:.1f}% Vac", 0, 1, 'R')
        pdf.cell(100, 7, "Standard Const. Loan Baseline (LTC):", 0, 0)
        pdf.cell(90, 7, f"${normal_const_loan:,.0f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 7, "Bank DSCR Capped Proceeds:", 0, 0)
        pdf.cell(90, 7, f"${actual_const_loan:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, "Capital Shortfall (Day-1 Equity Required):", 0, 0)
        pdf.cell(90, 7, f"${gap_proceeds:,.0f}", 0, 1, 'R')
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, " 3. Detailed Construction Cost Breakdown", fill=True, ln=1)
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(100, 7, "Total Direct Hard Costs:", 0, 0)
        pdf.cell(90, 7, f"${total_hard_cost:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, "Indirect General Conditions & Premiums:", 0, 0)
        pdf.cell(90, 7, f"${default_gcond + default_premium:,.0f}", 0, 1, 'R')
        
        gc_label = "Consolidated GC Flat Fee:" if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else "GC Management Fee:"
        pdf.cell(100, 7, gc_label, 0, 0)
        pdf.cell(90, 7, f"${default_gc_fee:,.0f}", 0, 1, 'R')
        
        pdf.cell(100, 7, "Land Acquisition Basis:", 0, 0)
        pdf.cell(90, 7, f"${total_land_default:,.0f}", 0, 1, 'R')
        
        pdf.cell(100, 7, "Const. Loan Capitalized Interest:", 0, 0)
        pdf.cell(90, 7, f"${carry_int_base:,.0f}", 0, 1, 'R')
            
        pdf.cell(100, 7, "Total Soft Costs & Closing Fees:", 0, 0)
        pdf.cell(90, 7, f"${total_soft_default + const_closing_fee + refi_closing_fee + default_buydown_cost:,.0f}", 0, 1, 'R')
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 4. Granular Direct Hard Cost Buildup", ln=1, fill=True)
        pdf.set_font("Arial", 'B', 9)
        
        pdf.cell(90, 6, "Division / Trade Level", 1, 0, 'C')
        pdf.cell(30, 6, "Live Cost / SF", 1, 0, 'C')
        pdf.cell(35, 6, f"Per Unit ({sqft} SF)", 1, 0, 'C')
        pdf.cell(35, 6, "Project Total", 1, 1, 'C')
        
        for name, live_sf, unit_cost, proj_cost, is_header in pdf_granular_data:
            if granular_mode == "Auto-Proportional (Linked to Master Model)":
                if not st.session_state.get("pdf_include_sublevels", True) and not is_header:
                    continue
            if is_header:
                pdf.set_font("Arial", 'B', 9)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(90, 6, name, 1, 0, 'L', fill=True)
                pdf.cell(30, 6, f"${live_sf:.2f}", 1, 0, 'R', fill=True)
                pdf.cell(35, 6, f"${unit_cost:,.0f}", 1, 0, 'R', fill=True)
                pdf.cell(35, 6, f"${proj_cost:,.0f}", 1, 1, 'R', fill=True)
            else:
                pdf.set_font("Arial", '', 9)
                pdf.cell(90, 6, name, 1, 0, 'L')
                pdf.cell(30, 6, f"${live_sf:.2f}", 1, 0, 'R')
                pdf.cell(35, 6, f"${unit_cost:,.0f}", 1, 0, 'R')
                pdf.cell(35, 6, f"${proj_cost:,.0f}", 1, 1, 'R')
                
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 5. Refinance Cash Waterfall (Payoff & Cash-Out)", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(130, 7, "(+) Permanent Takeout Loan Proceeds:", 0, 0)
        pdf.cell(60, 7, f"${loan_total:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Construction Loan Principal Payoff:", 0, 0)
        pdf.cell(60, 7, f"-${actual_const_loan:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Const. Loan Accrued Interest Payoff:", 0, 0)
        pdf.cell(60, 7, f"-${default_carry_int:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Refinance Closing Fees & Buydown Points:", 0, 0)
        pdf.cell(60, 7, f"-${refi_closing_fee + default_buydown_cost:,.0f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 7, "= Net Cash Distributed to Sponsor at Closing:", 0, 0)
        pdf.cell(60, 7, f"${net_cash_at_closing:,.0f}", 0, 1, 'R')
        pdf.set_font("Arial", '', 10)
        pdf.cell(130, 7, "(-) Initial Sponsor Seed Capital Invested:", 0, 0)
        pdf.cell(60, 7, f"-${seed_capital:,.0f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 7, "= Final Tax-Free Cash Surplus / (Trapped Capital):", 0, 0)
        pdf.cell(60, 7, f"${cash_surplus:,.0f}", 0, 1, 'R')
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            with open(tmp.name, "rb") as f:
                return f.read()

    with download_placeholder:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📄 Download Enterprise Report (PDF)",
            data=create_pdf(st.session_state.get("pdf_include_sublevels", True)),
            file_name=f"Wickboldt_Capital_ProForma_{report_date.replace(' ', '_').replace(',', '')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
