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
    "sqft": 1173,
    "aux_cost_mode": "Percentage of Heated Rate (%)",
    "aux_rate_pct": 50.0,
    "aux_fixed_cost_sf": 35.0,
    "structure_type": "Carport", 
    "struct_sqft": 213,
    "front_porch_sqft": 49,
    "back_porch_sqft": 0,
    "storage_sqft": 49,
    "additional_foundation_cost": 3000,
    
    "gross_monthly_rent": 1600,
    "target_dscr_rate": 1.20,
    "vacancy_rate_pct": 5.0,
    "opex_rate_pct": 25.0,
    
    "const_ltv_pct": 80.0,
    "build_months": 7,
    "const_rate_pct": 7.50,
    "avg_draw_pct": 50.0,
    "const_closing_fee": 6000,
    
    # Construction Lender Stress Constraints
    "const_bank_rent": 1500,
    "const_bank_ltv_pct": 80.0,
    "const_bank_val_mode": "DSCR Stress Test",
    "const_bank_grm": 10.0,
    "const_bank_opex_pct": 30.0,
    "const_bank_vac_pct": 5.0,
    "const_bank_dscr": 1.20,
    "const_bank_qual_rate_pct": 7.25,
    "const_bank_amort_yrs": 30,
    "reserve_accrual_pct": 100.0,
    
    "refi_ltv_pct": 80.0,
    "refi_term_years": 30,
    "base_refi_rate_pct": 7.00,
    "refi_closing_fee": 5000,
    "apply_buydown": True,
    "buydown_pts": 3.0,
    
    "gc_fee_mode": "Percentage of Hard Costs (%)",
    "gc_fee_pct": 7.0,
    "custom_gc_fee": 20000,
    "land_basis": 15000,
    
    "appraisal_mode": "Income Approach (GRM)",
    "target_grm": 10.0,
    
    "cost_calc_mode": "Reverse-Engineer from Primary Comp",
    "base_direct_cost_sf": 75.0, # Placeholder strictly required for Manual Mode slider
    "lot_cost_pct": 18.0,
    "margin_pct": 20.0,
    "sales_pct": 8.0,
    "finance_pct": 4.0,
    "pdf_include_sublevels": True,
    
    "comp_address": "",
    "comp_price": 182600,
    "comp_heated_sf": 1150,
    "comp_struct_sf": 213,
    "comp_front_sf": 49,
    "comp_back_sf": 49,
    "comp_storage_sf": 0
}

def load_defaults():
    if os.path.exists(DEFAULT_FILE):
        try:
            with open(DEFAULT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return HARDCODED_DRIVERS

GLOBAL_DRIVERS = load_defaults()
for key, value in GLOBAL_DRIVERS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "raw_api_data" not in st.session_state: st.session_state.raw_api_data = None


# ==========================================
# --- SIDEBAR (Live Underwriting Controls) ---
# ==========================================
st.sidebar.header("Master Model Drivers")

with st.sidebar.container():
    st.subheader("1. Project Scale")
    st.number_input("Number of Units (Doors)", min_value=1, step=1, format="%d", key="units")

with st.sidebar.container():
    st.subheader("2. Market Comp Valuation & Benchmark")
    st.radio("Comparable Data Entry Mode", ["Manual Entry", "RentCast Live API Fetch"], key="comp_entry_mode")

    if st.session_state.comp_entry_mode == "RentCast Live API Fetch":
        search_address = st.text_input("Property Address", placeholder="e.g. 1103 S Spruce St, Hammond, LA")
        with st.expander("⚙️ API Configuration (Optional)"):
            manual_key = st.text_input("RentCast API Key Override", type="password")

        if st.button("Fetch Live Data", use_container_width=True):
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
    is_rentcast = st.session_state.comp_entry_mode == "RentCast Live API Fetch"
    st.text_input("Comparable Property Address", key="comp_address", disabled=is_rentcast)
    st.number_input("Comp Sale Price ($)", step=1000, key="comp_price", disabled=is_rentcast)
    st.number_input("Comp Heated SF", step=50, key="comp_heated_sf", disabled=is_rentcast)

    st.markdown("##### 2. Comp Auxiliary Spaces")
    c_aux1, c_aux2 = st.columns(2)
    c_aux1.number_input("Aux SF", step=25, format="%d", key="comp_struct_sf", help="Garage or Carport")
    c_aux2.number_input("Front Porch SF", step=10, format="%d", key="comp_front_sf")
    c_aux3, c_aux4 = st.columns(2)
    c_aux3.number_input("Back Porch SF", step=10, format="%d", key="comp_back_sf")
    c_aux4.number_input("Storage SF", step=5, format="%d", key="comp_storage_sf")

with st.sidebar.container():
    st.subheader("3. Physical Footprint & Aux Costs")
    st.number_input("Heated SqFt per Unit", step=50, format="%d", key="sqft")
    
    st.radio("Auxiliary Rate Method", ["Percentage of Heated Rate (%)", "Fixed Cost ($ / SF)"], key="aux_cost_mode")
    
    if st.session_state.aux_cost_mode == "Percentage of Heated Rate (%)":
        st.slider("Auxiliary Rate (% of Heated Cost)", min_value=10.0, max_value=100.0, step=5.0, key="aux_rate_pct", help="Values unheated carport/porch space as a direct percentage of the heated shell rate per square foot for both the Comp and Project.")
    else:
        st.slider("Auxiliary Fixed Cost ($ / SF)", min_value=15.0, max_value=90.0, step=1.0, key="aux_fixed_cost_sf")
    
    st.selectbox("Aux Structure Type", ["Carport", "Garage"], key="structure_type")
    st.number_input(f"{st.session_state.structure_type} SqFt per Unit", step=25, format="%d", key="struct_sqft")
    st.number_input("Front Porch SqFt", step=10, format="%d", key="front_porch_sqft")
    st.number_input("Back Porch SqFt", step=10, format="%d", key="back_porch_sqft")
    st.number_input("Storage Room SqFt", step=5, format="%d", key="storage_sqft")
        
    st.number_input("Additional Foundation / Elevation Cost ($)", step=500, format="%d", key="additional_foundation_cost")

with st.sidebar.container():
    st.subheader("4. Takeout Appraisal Methodology")
    st.radio("Valuation Mode", ["Sales Comp (Price/SF)", "Income Approach (GRM)"], key="appraisal_mode")
    if st.session_state.appraisal_mode == "Income Approach (GRM)":
        st.number_input("Gross Rent Multiplier (GRM)", min_value=4.0, max_value=25.0, step=0.1, key="target_grm")

with st.sidebar.container():
    st.subheader("5. Cost Target Mode (Reverse Engineer)")
    st.radio("Calculation Logic", ["Manual Set (Heated SF)", "Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"], key="cost_calc_mode")
    if st.session_state.cost_calc_mode == "Manual Set (Heated SF)":
        st.slider("Direct Build Cost / SF ($)", min_value=40.0, max_value=150.0, step=1.0, key="base_direct_cost_sf")
    else:
        st.slider("Finished Lot Cost (%)", min_value=0.0, max_value=30.0, step=0.5, key="lot_cost_pct")
        st.slider("Gross Margin (O&P) (%)", min_value=0.0, max_value=30.0, step=0.5, key="margin_pct")
        st.slider("Sales & Marketing (%)", min_value=0.0, max_value=15.0, step=0.5, key="sales_pct")
        st.slider("Soft Costs & Finance (%)", min_value=0.0, max_value=15.0, step=0.5, key="finance_pct")

with st.sidebar.container():
    st.subheader("6. GC Fee & Land Costs")
    st.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"], key="gc_fee_mode")
    if st.session_state.gc_fee_mode == "Percentage of Hard Costs (%)":
        st.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, step=0.5, key="gc_fee_pct")
    else:
        st.number_input("Total Consolidated GC Fee ($)", step=1000, format="%d", key="custom_gc_fee")
    st.number_input("Land Basis per Lot ($)", step=1000, format="%d", key="land_basis")

with st.sidebar.container():
    st.subheader("7. Financing & Operations")
    st.number_input("Gross Monthly Rental Income per Unit ($)", step=50, format="%d", key="gross_monthly_rent")
    st.number_input("Target Lender DSCR Rate", min_value=1.0, max_value=1.5, step=0.05, key="target_dscr_rate")
    st.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, step=1.0, key="vacancy_rate_pct")
    st.slider("Operating Expenses (OpEx) Rate of EGI (%)", min_value=15.0, max_value=50.0, step=1.0, key="opex_rate_pct")
    
    st.slider("Construction / Bank LTC (%)", min_value=60.0, max_value=100.0, step=5.0, key="const_ltv_pct")
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
    st.subheader("8. Const. Lender Limits")
    st.number_input("Bank Underwriting Rent ($)", step=50, format="%d", key="const_bank_rent")
    st.slider("Bank Underwriting LTV (%)", min_value=50.0, max_value=100.0, step=5.0, key="const_bank_ltv_pct")
    st.radio("Bank Valuation Method", ["DSCR Stress Test", "Gross Rent Multiplier (GRM)"], key="const_bank_val_mode")
    
    if st.session_state.const_bank_val_mode == "DSCR Stress Test":
        st.slider("Bank Underwriting OpEx (%)", min_value=15.0, max_value=50.0, step=1.0, key="const_bank_opex_pct")
        st.slider("Bank Underwriting Vacancy (%)", min_value=0.0, max_value=15.0, step=1.0, key="const_bank_vac_pct")
        st.number_input("Bank Target DSCR", min_value=1.0, max_value=1.5, step=0.05, key="const_bank_dscr")
        st.slider("Bank Qualifying Rate (%)", min_value=4.0, max_value=14.0, step=0.25, key="const_bank_qual_rate_pct")
        st.selectbox("Bank Amortization (Years)", [15, 20, 25, 30], key="const_bank_amort_yrs")
    else:
        st.number_input("Bank Underwriting GRM", min_value=4.0, max_value=25.0, step=0.1, key="const_bank_grm")

with st.sidebar.container():
    st.subheader("PDF Export Options")
    st.checkbox("Include Detailed Sub-Levels in PDF Report", key="pdf_include_sublevels")


# ==========================================
# --- SAFE VARIABLE EXTRACTION FOR MATH ---
# ==========================================
units = st.session_state.get("units", 1)
sqft = st.session_state.get("sqft", 1173)

# Core Auxiliary logic 
aux_cost_mode = st.session_state.get("aux_cost_mode", "Percentage of Heated Rate (%)")
aux_ratio = st.session_state.get("aux_rate_pct", 50.0) / 100.0
aux_fixed_cost_sf = st.session_state.get("aux_fixed_cost_sf", 35.0)

struct_sqft = st.session_state.get("struct_sqft", 213)
front_porch_sqft = st.session_state.get("front_porch_sqft", 49)
back_porch_sqft = st.session_state.get("back_porch_sqft", 0)
storage_sqft = st.session_state.get("storage_sqft", 49)
additional_foundation_cost = st.session_state.get("additional_foundation_cost", 3000)

gross_monthly_rent = st.session_state.get("gross_monthly_rent", 1600)
target_dscr_rate = st.session_state.get("target_dscr_rate", 1.20)
vacancy_rate = st.session_state.get("vacancy_rate_pct", 5.0) / 100.0
opex_rate = st.session_state.get("opex_rate_pct", 25.0) / 100.0
const_ltv = st.session_state.get("const_ltv_pct", 80.0) / 100.0
build_months = st.session_state.get("build_months", 7)
const_rate = st.session_state.get("const_rate_pct", 7.50) / 100.0
avg_draw_pct = st.session_state.get("avg_draw_pct", 50.0) / 100.0
const_closing_fee = st.session_state.get("const_closing_fee", 6000)

const_bank_rent = st.session_state.get("const_bank_rent", 1500)
const_bank_ltv = st.session_state.get("const_bank_ltv_pct", 80.0) / 100.0
const_bank_val_mode = st.session_state.get("const_bank_val_mode", "DSCR Stress Test")
const_bank_grm = st.session_state.get("const_bank_grm", 10.0)
const_bank_opex_pct = st.session_state.get("const_bank_opex_pct", 30.0) / 100.0
const_bank_vac_pct = st.session_state.get("const_bank_vac_pct", 5.0) / 100.0
const_bank_dscr = st.session_state.get("const_bank_dscr", 1.20)
const_bank_qual_rate = st.session_state.get("const_bank_qual_rate_pct", 7.25) / 100.0
const_bank_amort_yrs = st.session_state.get("const_bank_amort_yrs", 30)

refi_ltv = st.session_state.get("refi_ltv_pct", 80.0) / 100.0
refi_term_years = st.session_state.get("refi_term_years", 30)
base_refi_rate = st.session_state.get("base_refi_rate_pct", 7.00) / 100.0
refi_closing_fee = st.session_state.get("refi_closing_fee", 5000)
apply_buydown = st.session_state.get("apply_buydown", True)
buydown_pts = st.session_state.get("buydown_pts", 3.0)
net_refi_rate = max(0.01, base_refi_rate - (buydown_pts * 0.0025)) if apply_buydown else base_refi_rate

gc_fee_mode = st.session_state.get("gc_fee_mode", "Percentage of Hard Costs (%)")
gc_fee_pct = st.session_state.get("gc_fee_pct", 7.0) / 100.0
custom_gc_fee = st.session_state.get("custom_gc_fee", 20000)
land_basis = st.session_state.get("land_basis", 15000)
appraisal_mode = st.session_state.get("appraisal_mode", "Income Approach (GRM)")
target_grm = st.session_state.get("target_grm", 10.0)

cost_calc_mode = st.session_state.get("cost_calc_mode", "Reverse-Engineer from Primary Comp")
base_direct_cost_sf_input = st.session_state.get("base_direct_cost_sf", 75.0)
lot_cost_pct = st.session_state.get("lot_cost_pct", 18.0) / 100.0
margin_pct = st.session_state.get("margin_pct", 20.0) / 100.0
sales_pct = st.session_state.get("sales_pct", 8.0) / 100.0
finance_pct = st.session_state.get("finance_pct", 4.0) / 100.0

comp_price = st.session_state.get("comp_price", 182600)
comp_heated_sf = st.session_state.get("comp_heated_sf", 1150)
comp_struct_sf = st.session_state.get("comp_struct_sf", 213)
comp_front_sf = st.session_state.get("comp_front_sf", 49)
comp_back_sf = st.session_state.get("comp_back_sf", 49)
comp_storage_sf = st.session_state.get("comp_storage_sf", 0)


# ==========================================
# --- CORE PRE-RENDER MATHEMATICS ---
# ==========================================
aux_sqft_total = struct_sqft + front_porch_sqft + back_porch_sqft + storage_sqft
total_under_roof_sqft = sqft + aux_sqft_total

comp_aux_sqft = comp_struct_sf + comp_front_sf + comp_back_sf + comp_storage_sf
comp_total_sf = comp_heated_sf + comp_aux_sqft
raw_comp_price_sf = comp_price / comp_heated_sf if comp_heated_sf > 0 else 0

target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)

# 1. Evaluate Primary Comp and Isolate Heated Shell Rate
if aux_cost_mode == "Percentage of Heated Rate (%)":
    effective_comp_heated_sf = comp_heated_sf + (comp_aux_sqft * aux_ratio)
    isolated_heated_rate = comp_price / effective_comp_heated_sf if effective_comp_heated_sf > 0 else 0
    comp_aux_rate_sf = isolated_heated_rate * aux_ratio
    comp_aux_value = comp_aux_sqft * comp_aux_rate_sf
else:
    comp_aux_rate_sf = aux_fixed_cost_sf
    comp_aux_value = comp_aux_sqft * comp_aux_rate_sf
    comp_isolated_heated_value = max(0, comp_price - comp_aux_value)
    isolated_heated_rate = comp_isolated_heated_value / comp_heated_sf if comp_heated_sf > 0 else 0

# 2. Derive Valuation & Hard Cost Target
if appraisal_mode == "Income Approach (GRM)":
    arv_per_unit = (gross_monthly_rent * 12) * target_grm
else:
    arv_per_unit = 0 

if aux_cost_mode == "Percentage of Heated Rate (%)":
    if cost_calc_mode == "Manual Set (Heated SF)":
        direct_cost_sf = base_direct_cost_sf_input
        struct_cost_sf = direct_cost_sf * aux_ratio
        our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
        target_heated_hard_cost = direct_cost_sf * sqft
        target_total_hard_cost = target_heated_hard_cost + our_aux_cost_total
        comp_equivalent_arv = (isolated_heated_rate * sqft) + (aux_sqft_total * (isolated_heated_rate * aux_ratio)) + additional_foundation_cost
        if appraisal_mode != "Income Approach (GRM)":
            arv_per_unit = comp_equivalent_arv
            
    elif cost_calc_mode == "Reverse-Engineer from Appraisal":
        target_total_hard_cost = arv_per_unit * target_hard_cost_pct
        effective_project_heated_sf = sqft + (aux_sqft_total * aux_ratio)
        direct_cost_sf = max(0, (target_total_hard_cost - additional_foundation_cost) / effective_project_heated_sf) if effective_project_heated_sf > 0 else 0
        struct_cost_sf = direct_cost_sf * aux_ratio
        our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
        target_heated_hard_cost = direct_cost_sf * sqft
        comp_equivalent_arv = arv_per_unit
        
    else: # Reverse-Engineer from Primary Comp
        comp_equivalent_arv = (isolated_heated_rate * sqft) + (aux_sqft_total * (isolated_heated_rate * aux_ratio)) + additional_foundation_cost
        target_total_hard_cost = comp_equivalent_arv * target_hard_cost_pct
        effective_project_heated_sf = sqft + (aux_sqft_total * aux_ratio)
        direct_cost_sf = max(0, (target_total_hard_cost - additional_foundation_cost) / effective_project_heated_sf) if effective_project_heated_sf > 0 else 0
        struct_cost_sf = direct_cost_sf * aux_ratio
        our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
        target_heated_hard_cost = direct_cost_sf * sqft
        if appraisal_mode != "Income Approach (GRM)":
            arv_per_unit = comp_equivalent_arv

else: # Fixed Aux Cost Mode
    struct_cost_sf = aux_fixed_cost_sf
    our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
    
    if appraisal_mode != "Income Approach (GRM)":
        arv_per_unit = (isolated_heated_rate * sqft) + our_aux_cost_total

    if cost_calc_mode == "Manual Set (Heated SF)":
        direct_cost_sf = base_direct_cost_sf_input
        target_heated_hard_cost = direct_cost_sf * sqft
        target_total_hard_cost = target_heated_hard_cost + our_aux_cost_total
        comp_equivalent_arv = 0 
    elif cost_calc_mode == "Reverse-Engineer from Appraisal":
        target_total_hard_cost = arv_per_unit * target_hard_cost_pct
        target_heated_hard_cost = max(0, target_total_hard_cost - our_aux_cost_total)
        direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0
        comp_equivalent_arv = arv_per_unit
    else: # Reverse from Comp
        comp_equivalent_arv = (isolated_heated_rate * sqft) + our_aux_cost_total
        target_total_hard_cost = comp_equivalent_arv * target_hard_cost_pct
        target_heated_hard_cost = max(0, target_total_hard_cost - our_aux_cost_total)
        direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0

# Unified component rates across UI display
front_porch_cost_sf = struct_cost_sf
back_porch_cost_sf = struct_cost_sf
storage_cost_sf = struct_cost_sf

struct_total_cost = struct_sqft * struct_cost_sf
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf
storage_cost = storage_sqft * storage_cost_sf

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

cb_gross_annual_rent = const_bank_rent * units * 12.0

if const_bank_val_mode == "DSCR Stress Test":
    cb_noi = cb_gross_annual_rent * (1.0 - const_bank_vac_pct) * (1.0 - const_bank_opex_pct)
    cb_max_annual_ds = cb_noi / const_bank_dscr
    cb_monthly_rate = const_bank_qual_rate / 12.0
    cb_term_months = const_bank_amort_yrs * 12

    if cb_monthly_rate > 0:
        bank_stressed_value = (cb_max_annual_ds / 12.0) * ((1.0 - (1.0 + cb_monthly_rate)**-cb_term_months) / cb_monthly_rate)
    else:
        bank_stressed_value = (cb_max_annual_ds / 12.0) * cb_term_months
else:
    bank_stressed_value = cb_gross_annual_rent * const_bank_grm

actual_const_loan = bank_stressed_value * const_bank_ltv

time_years = build_months / 12.0
carry_int_base = actual_const_loan * avg_draw_pct * const_rate * time_years

default_buydown_cost = loan_total * (buydown_pts / 100.0) if apply_buydown else 0
total_const = total_hard_cost + default_gcond + default_gc_fee + default_premium
total_project_costs_ex_interest = total_land_default + total_const + total_soft_default + const_closing_fee

total_construction_basis = total_project_costs_ex_interest + carry_int_base
total_project_basis = total_construction_basis + refi_closing_fee + default_buydown_cost

seed_capital = total_construction_basis - actual_const_loan


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

net_cash_at_closing = loan_total - actual_const_loan - refi_closing_fee - default_buydown_cost
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

    # --- COMP AUDIT DASHBOARD ---
    st.markdown("### 🔍 Market Comp Valuation Audit")
    
    if st.session_state.comp_address:
        st.caption(f"📍 **Active Comp:** {st.session_state.comp_address} | Isolated Heated Shell Rate: **${isolated_heated_rate:.2f} / SF** | Implied Aux Rate: **${comp_aux_rate_sf:.2f} / SF**")
    else:
        st.caption(f"📊 Isolated Heated Shell Rate: **${isolated_heated_rate:.2f} / SF** | Implied Aux Rate: **${comp_aux_rate_sf:.2f} / SF**")

    with st.expander("🧮 View Comp Math Audit & Raw API Data", expanded=False):
        st.markdown("**1. Raw Retail Heated Rate (Unadjusted)**")
        st.code(f"${comp_price:,.0f} ÷ {comp_heated_sf:,.0f} SF = ${raw_comp_price_sf:.2f} / SF")
        
        if aux_cost_mode == "Percentage of Heated Rate (%)":
            st.markdown(f"**2. True Isolated Heated Shell Rate (Aux valued at {aux_ratio*100:.0f}% of Heated Shell)**")
            st.code(f"Effective Heated SF: {comp_heated_sf:,.0f} + ({comp_aux_sqft:,.0f} Aux SF × {aux_ratio:.2f}) = {effective_comp_heated_sf:,.1f} SF\n${comp_price:,.0f} ÷ {effective_comp_heated_sf:,.1f} SF = ${isolated_heated_rate:.2f} / SF (Aux Rate: ${comp_aux_rate_sf:.2f} / SF)")
        else:
            st.markdown(f"**2. True Isolated Heated Shell Rate (Fixed Aux Value: ${aux_fixed_cost_sf:.2f} / SF)**")
            st.code(f"(${comp_price:,.0f} - ${comp_aux_value:,.0f} Aux) ÷ {comp_heated_sf:,.0f} SF = ${isolated_heated_rate:.2f} / SF")
            
        if st.session_state.raw_api_data and st.session_state.get("comp_entry_mode") == "RentCast Live API Fetch":
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
    raw_struct_divs = [("AUXILIARY: CARPORT / GARAGE", 35.00, True)]
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
            live_sf = struct_cost_sf * (base_val / 35.0)
            s_data["Component Level"].append(name)
            s_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            s_data["Per Unit Cost"].append(f"${live_sf * struct_sqft:,.0f}")
        st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True)
    else:
        st.markdown(f"#### 1. Heated Living Area ({sqft} SF)")
        hl_heated = [{"Division / Trade Level": name, "Cost / SF": direct_cost_sf * (base/74.0)} for name, base, is_h, scope in raw_heated_divs]
        edited_h = st.data_editor(pd.DataFrame(hl_heated), column_config={"Division / Trade Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True)
        direct_cost_sf = edited_h["Cost / SF"].sum()
        for index, row in edited_h.iterrows():
            live_sf = row["Cost / SF"]
            pdf_granular_data.append((row["Division / Trade Level"], live_sf, live_sf * sqft, live_sf * sqft * units, True))
        
        st.markdown(f"#### 2. {st.session_state.structure_type} Auxiliary ({struct_sqft} SF)")
        hl_struct = [{"Component Level": name, "Cost / SF": struct_cost_sf * (base/35.0)} for name, base, is_h in raw_struct_divs]
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
    
    # --- BANK STRESS TEST BREAKDOWN ---
    st.markdown("### 🏦 Construction Lender Loan Cap")
    
    if const_bank_val_mode == "DSCR Stress Test":
        st.caption("The bank determines the implied asset value based on their DSCR test, applies their LTV to get the Loan Value, and subtracts that from the Total Basis to find your required Seed Capital.")
        stress_test_data = {
            "Bank Underwriting Step": [
                "1. Gross Potential Rent (Bank Model)",
                "2. Less: Bank Vacancy & OpEx Deductions",
                "3. Bank Qualified Net Operating Income (NOI)",
                "4. Target Construction DSCR Constraint",
                "5. Bank Implied Asset Value (Value of the House)",
                f"6. Const. Lender Loan Value ({const_bank_ltv*100:.1f}% Bank LTV)",
                "7. Total Capitalized Construction Basis",
                "8. Required Seed Capital Reserve (Basis - Loan Value)"
            ],
            "Value": [
                f"${cb_gross_annual_rent:,.0f} / yr",
                f"-${cb_gross_annual_rent - cb_noi:,.0f} / yr",
                f"${cb_noi:,.0f} / yr",
                f"{const_bank_dscr:.2f}x",
                f"${bank_stressed_value:,.0f}",
                f"${actual_const_loan:,.0f}",
                f"${total_construction_basis:,.0f}",
                f"${seed_capital:,.0f}"
            ]
        }
    else:
        st.caption("The bank determines the implied asset value based on a Gross Rent Multiplier (GRM), applies their LTV to get the Loan Value, and subtracts that from the Total Basis to find your required Seed Capital.")
        stress_test_data = {
            "Bank Underwriting Step": [
                "1. Gross Potential Rent (Bank Model)",
                "2. Bank Underwriting GRM",
                "3. Bank Implied Asset Value (Value of the House)",
                f"4. Const. Lender Loan Value ({const_bank_ltv*100:.1f}% Bank LTV)",
                "5. Total Capitalized Construction Basis",
                "6. Required Seed Capital Reserve (Basis - Loan Value)"
            ],
            "Value": [
                f"${cb_gross_annual_rent:,.0f} / yr",
                f"{const_bank_grm:.1f}x",
                f"${bank_stressed_value:,.0f}",
                f"${actual_const_loan:,.0f}",
                f"${total_construction_basis:,.0f}",
                f"${seed_capital:,.0f}"
            ]
        }
    st.dataframe(pd.DataFrame(stress_test_data), hide_index=True, use_container_width=True)

    if seed_capital > 0:
        st.warning(f"**Seed Capital Required:** The bank will fund **${actual_const_loan:,.0f}** based on the appraised value. Your Total Construction Basis is **${total_construction_basis:,.0f}**. You must bring **${seed_capital:,.0f}** in Day-1 Seed Capital (Reserves).")
    else:
        st.success(f"**Fully Funded:** The bank's loan value of **${actual_const_loan:,.0f}** covers your entire construction basis. No Day-1 Seed Capital is required.")
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
            "(-) Construction Loan Payoff (Prin. & Int.)",
            "(-) Refinance Closing Fees",
            "(-) Rate Buydown Points Cost",
            "= Net Cash Distributed to Sponsor at Closing",
            "(-) Initial Sponsor Seed Capital Invested",
            "= Final Tax-Free Cash Surplus / (Trapped Capital)"
        ],
        "Amount ($)": [
            f"${loan_total:,.0f}",
            f"-${actual_const_loan:,.0f}",
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
                f"Yields exactly ${direct_cost_sf:.2f} / SF across {sqft} Heated SF."
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
            f"-${annual_opex / 12:,.2f}", f"${annual_noi:,.2f}", f"${annual_debt_service:,.2f}", f"${monthly_cash_flow * 12:,.2f}",
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
        pdf.cell(100, 7, "Const. Loan Proceeds (Payoff):", 0, 0)
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
        pdf.cell(0, 8, " 2. Const. Bank Limits & Loan Cap", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        
        if const_bank_val_mode == "DSCR Stress Test":
            pdf.cell(100, 7, "Bank Assumed Rent & Target DSCR:", 0, 0)
            pdf.cell(90, 7, f"${const_bank_rent:,.0f}/mo | {const_bank_dscr:.2f}x DSCR", 0, 1, 'R')
            pdf.cell(100, 7, "Bank OpEx & Vacancy Deductions:", 0, 0)
            pdf.cell(90, 7, f"{const_bank_opex_pct*100:.1f}% OpEx | {const_bank_vac_pct*100:.1f}% Vac", 0, 1, 'R')
            pdf.cell(100, 7, "Bank Implied Asset Value (Refi Stress Test):", 0, 0)
            pdf.cell(90, 7, f"${bank_stressed_value:,.0f}", 0, 1, 'R')
        else:
            pdf.cell(100, 7, "Bank Assumed Rent & Target GRM:", 0, 0)
            pdf.cell(90, 7, f"${const_bank_rent:,.0f}/mo | {const_bank_grm:.1f}x GRM", 0, 1, 'R')
            pdf.cell(100, 7, "Bank Implied Asset Value (GRM Stress Test):", 0, 0)
            pdf.cell(90, 7, f"${bank_stressed_value:,.0f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 7, f"Const. Lender Loan Value ({const_bank_ltv*100:.1f}% Bank LTV):", 0, 0)
        pdf.cell(60, 7, f"${actual_const_loan:,.0f}", 0, 1, 'R')
        
        pdf.cell(130, 7, "Total Capitalized Construction Basis:", 0, 0)
        pdf.cell(60, 7, f"${total_construction_basis:,.0f}", 0, 1, 'R')
        
        pdf.cell(130, 7, "Required Seed Capital Reserve (Basis - Loan Value):", 0, 0)
        pdf.cell(60, 7, f"${seed_capital:,.0f}", 0, 1, 'R')
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
        pdf.cell(130, 7, "(-) Construction Loan Payoff (Prin. & Int.):", 0, 0)
        pdf.cell(60, 7, f"-${actual_const_loan:,.0f}", 0, 1, 'R')
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
