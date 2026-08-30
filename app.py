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
# --- MASTER DEFAULTS DICTIONARY ---
# ==========================================
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
    "target_min_cashflow_per_door": 200.0,
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
    "const_bank_val_mode": "Gross Rent Multiplier (GRM)",
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
    
    # NAHB & Indirect Cost Breakdowns
    "cost_calc_mode": "Reverse-Engineer from Primary Comp",
    "base_direct_cost_sf": 75.0,
    "lot_cost_pct": 13.7,
    "profit_margin_pct": 11.0,
    "overhead_pct": 5.7,
    "sales_pct": 3.6,
    "finance_pct": 1.5,
    "indirect_permits_pct": 4.5,
    "indirect_temp_facilities_pct": 3.5,
    
    "comp_address": "",
    "comp_price": 195000,
    "comp_heated_sf": 1275,
    "comp_struct_sf": 213,
    "comp_front_sf": 49,
    "comp_back_sf": 49,
    "comp_storage_sf": 0
}

GLOBAL_DRIVERS = HARDCODED_DRIVERS.copy()
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

    st.markdown("##### 2.1 Primary Comp Metrics")
    is_rentcast = st.session_state.comp_entry_mode == "RentCast Live API Fetch"
    st.text_input("Comparable Property Address", key="comp_address", disabled=is_rentcast)
    st.number_input("Comp Sale Price ($)", min_value=0, step=1000, key="comp_price", disabled=is_rentcast)
    st.number_input("Comp Heated SF", min_value=0, step=50, key="comp_heated_sf", disabled=is_rentcast)

    st.markdown("##### 2.2 Comp Auxiliary Spaces")
    c_aux1, c_aux2 = st.columns(2)
    c_aux1.number_input("Aux SF", min_value=0, step=25, format="%d", key="comp_struct_sf", help="Garage or Carport")
    c_aux2.number_input("Front Porch SF", min_value=0, step=10, format="%d", key="comp_front_sf")
    c_aux3, c_aux4 = st.columns(2)
    c_aux3.number_input("Back Porch SF", min_value=0, step=10, format="%d", key="comp_back_sf")
    c_aux4.number_input("Storage SF", min_value=0, step=5, format="%d", key="comp_storage_sf")

with st.sidebar.container():
    st.subheader("3. Physical Footprint & Aux Costs")
    st.number_input("Heated SqFt per Unit", min_value=0, step=50, format="%d", key="sqft")
    
    st.radio("Auxiliary Rate Method", ["Percentage of Heated Rate (%)", "Fixed Cost ($ / SF)"], key="aux_cost_mode")
    
    if st.session_state.aux_cost_mode == "Percentage of Heated Rate (%)":
        st.slider("Auxiliary Rate (% of Heated Cost)", min_value=10.0, max_value=100.0, step=5.0, key="aux_rate_pct", help="Values unheated carport/porch space as a direct percentage of the heated shell rate per square foot for both the Comp and Project.")
    else:
        st.slider("Auxiliary Fixed Cost ($ / SF)", min_value=15.0, max_value=90.0, step=1.0, key="aux_fixed_cost_sf")
    
    st.selectbox("Aux Structure Type", ["Carport", "Garage"], key="structure_type")
    st.number_input(f"{st.session_state.structure_type} SqFt per Unit", min_value=0, step=25, format="%d", key="struct_sqft")
    st.number_input("Front Porch SqFt", min_value=0, step=10, format="%d", key="front_porch_sqft")
    st.number_input("Back Porch SqFt", min_value=0, step=10, format="%d", key="back_porch_sqft")
    st.number_input("Storage Room SqFt", min_value=0, step=5, format="%d", key="storage_sqft")
        
    st.number_input("Additional Foundation / Elevation Cost ($)", min_value=0, step=500, format="%d", key="additional_foundation_cost")

with st.sidebar.container():
    st.subheader("4. Takeout Appraisal Methodology")
    st.radio("Valuation Mode", ["Sales Comp (Price/SF)", "Income Approach (GRM)"], key="appraisal_mode")
    if st.session_state.appraisal_mode == "Income Approach (GRM)":
        st.number_input("Gross Rent Multiplier (GRM)", min_value=4.0, max_value=25.0, value=float(GLOBAL_DRIVERS.get("target_grm", 10.0)), step=0.1, key="target_grm")

with st.sidebar.container():
    st.subheader("5. Cost Target Mode (Reverse Engineer)")
    st.radio("Calculation Logic", ["Manual Set (Heated SF)", "Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"], key="cost_calc_mode")
    if st.session_state.cost_calc_mode == "Manual Set (Heated SF)":
        st.slider("Direct Build Cost / SF ($)", min_value=40.0, max_value=150.0, step=1.0, key="base_direct_cost_sf")
    else:
        st.slider("Finished Lot Cost (%)", min_value=0.0, max_value=30.0, step=0.1, key="lot_cost_pct")
        st.slider("Builder Profit (Pre-tax) (%)", min_value=0.0, max_value=30.0, step=0.1, key="profit_margin_pct")
        st.slider("Overhead & General Expenses (%)", min_value=0.0, max_value=15.0, step=0.1, key="overhead_pct")
        st.slider("Sales & Marketing Commissions (%)", min_value=0.0, max_value=15.0, step=0.1, key="sales_pct")
        st.slider("Financing Costs (%)", min_value=0.0, max_value=10.0, step=0.1, key="finance_pct")

with st.sidebar.container():
    st.subheader("6. Indirect Costs, GC Fee & Land")
    st.slider("Permits, Fees, & Insurance (% of Direct)", min_value=0.0, max_value=15.0, step=0.5, key="indirect_permits_pct")
    st.slider("Temporary Site Facilities (% of Direct)", min_value=0.0, max_value=15.0, step=0.5, key="indirect_temp_facilities_pct")
    st.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"], key="gc_fee_mode")
    if st.session_state.gc_fee_mode == "Percentage of Hard Costs (%)":
        st.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, step=0.5, key="gc_fee_pct")
    else:
        st.number_input("Total Consolidated GC Fee ($)", min_value=0, step=1000, format="%d", key="custom_gc_fee")
    st.number_input("Land Basis per Lot ($)", min_value=0, step=1000, format="%d", key="land_basis")

with st.sidebar.container():
    st.subheader("7. Construction Loan Terms")
    st.slider("Construction / Bank LTC (%)", min_value=60.0, max_value=100.0, step=5.0, key="const_ltv_pct")
    st.slider("Construction Duration (Months)", min_value=3, max_value=18, step=1, key="build_months")
    st.slider("Construction Loan Rate (%)", min_value=4.0, max_value=14.0, step=0.5, key="const_rate_pct")
    st.slider("Avg Draw Utilization (%)", min_value=20.0, max_value=100.0, step=5.0, key="avg_draw_pct")
    st.number_input("Const Loan Closing Fee ($ total)", min_value=0, step=500, format="%d", key="const_closing_fee")

with st.sidebar.container():
    st.subheader("8. Const. Lender Limits")
    st.number_input("Bank Underwriting Rent ($)", min_value=0, step=50, format="%d", key="const_bank_rent")
    st.slider("Bank Underwriting LTV (%)", min_value=50.0, max_value=100.0, step=5.0, key="const_bank_ltv_pct")
    
    st.radio("Bank Valuation Method", ["Gross Rent Multiplier (GRM)", "DSCR Stress Test"], key="const_bank_val_mode")
    
    if st.session_state.const_bank_val_mode == "Gross Rent Multiplier (GRM)":
        st.number_input("Bank Underwriting GRM", min_value=4.0, max_value=25.0, value=float(GLOBAL_DRIVERS.get("const_bank_grm", 10.0)), step=0.1, key="const_bank_grm")
    else:
        st.slider("Bank Underwriting Vacancy (%)", min_value=0.0, max_value=15.0, step=1.0, key="const_bank_vac_pct")
        st.slider("Bank Underwriting OpEx (%)", min_value=15.0, max_value=50.0, step=1.0, key="const_bank_opex_pct")
        st.number_input("Bank Target DSCR", min_value=1.0, max_value=1.5, value=float(GLOBAL_DRIVERS.get("const_bank_dscr", 1.20)), step=0.05, key="const_bank_dscr")
        st.slider("Bank Qualifying Rate (%)", min_value=4.0, max_value=14.0, step=0.25, key="const_bank_qual_rate_pct")
        st.selectbox("Bank Amortization (Years)", [15, 20, 25, 30], key="const_bank_amort_yrs")

with st.sidebar.container():
    st.subheader("9. Operating Pro Forma (DSCR)")
    st.number_input("Gross Monthly Rental Income per Unit ($)", min_value=0, step=50, format="%d", key="gross_monthly_rent")
    st.number_input("Target Lender DSCR Rate", min_value=1.0, max_value=1.5, value=float(GLOBAL_DRIVERS.get("target_dscr_rate", 1.20)), step=0.05, key="target_dscr_rate")
    st.number_input("Min. Acceptable Cash Flow / Door ($)", min_value=0.0, max_value=1000.0, value=float(GLOBAL_DRIVERS.get("target_min_cashflow_per_door", 200.0)), step=25.0, key="target_min_cashflow_per_door")
    st.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, step=1.0, key="vacancy_rate_pct")
    st.slider("Operating Expenses (OpEx) Rate of EGI (%)", min_value=15.0, max_value=50.0, step=1.0, key="opex_rate_pct")

with st.sidebar.container():
    st.subheader("10. Takeout Refinance Terms")
    st.slider("Refinance LTV (%)", min_value=60.0, max_value=85.0, step=5.0, key="refi_ltv_pct")
    st.selectbox("Amortization Term (Years)", [15, 20, 25, 30], key="refi_term_years")
    st.slider("Base Refi Interest Rate (%)", min_value=4.0, max_value=10.0, step=0.25, key="base_refi_rate_pct")
    st.number_input("Refinance Closing Fee ($ total)", min_value=0, step=250, format="%d", key="refi_closing_fee")
    st.checkbox("Apply Interest Rate Buydown Points?", key="apply_buydown")
    if st.session_state.apply_buydown:
        st.number_input("Discount Points", min_value=0.0, max_value=5.0, value=float(GLOBAL_DRIVERS.get("buydown_pts", 3.0)), step=0.5, key="buydown_pts")
        net_rate = max(0.01, (st.session_state.base_refi_rate_pct / 100.0) - (st.session_state.buydown_pts * 0.0025))
        st.markdown(f"📉 **Buydown Net Rate:** `{net_rate*100:.3f}%`")


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
target_min_cashflow_per_door = st.session_state.get("target_min_cashflow_per_door", 200.0)
vacancy_rate = st.session_state.get("vacancy_rate_pct", 5.0) / 100.0
opex_rate = st.session_state.get("opex_rate_pct", 25.0) / 100.0
const_ltv = st.session_state.get("const_ltv_pct", 80.0) / 100.0
build_months = st.session_state.get("build_months", 7)
const_rate = st.session_state.get("const_rate_pct", 7.50) / 100.0
avg_draw_pct = st.session_state.get("avg_draw_pct", 50.0) / 100.0
const_closing_fee = st.session_state.get("const_closing_fee", 6000)

const_bank_rent = st.session_state.get("const_bank_rent", 1500)
const_bank_ltv = st.session_state.get("const_bank_ltv_pct", 80.0) / 100.0
const_bank_val_mode = st.session_state.get("const_bank_val_mode", "Gross Rent Multiplier (GRM)")
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

# NAHB & Indirect Cost Breakdowns
cost_calc_mode = st.session_state.get("cost_calc_mode", "Reverse-Engineer from Primary Comp")
base_direct_cost_sf_input = st.session_state.get("base_direct_cost_sf", 75.0)
lot_cost_pct = st.session_state.get("lot_cost_pct", 13.7) / 100.0
profit_margin_pct = st.session_state.get("profit_margin_pct", 11.0) / 100.0
overhead_pct = st.session_state.get("overhead_pct", 5.7) / 100.0
sales_pct = st.session_state.get("sales_pct", 3.6) / 100.0
finance_pct = st.session_state.get("finance_pct", 1.5) / 100.0

indirect_permits_pct = st.session_state.get("indirect_permits_pct", 4.5) / 100.0
indirect_temp_facilities_pct = st.session_state.get("indirect_temp_facilities_pct", 3.5) / 100.0

comp_price = st.session_state.get("comp_price", 195000)
comp_heated_sf = st.session_state.get("comp_heated_sf", 1275)
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

# The combined deduction percentage used to extract the NAHB Construction Budget
combined_deductions_pct = lot_cost_pct + profit_margin_pct + overhead_pct + sales_pct + finance_pct
target_const_budget_pct = max(0, 1.0 - combined_deductions_pct)

# Multiplier to extract Direct Hard Cost from Total Construction Budget
indirect_multiplier = 1.0 + indirect_permits_pct + indirect_temp_facilities_pct

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
    effective_project_heated_sf = sqft + (aux_sqft_total * aux_ratio)
    
    if cost_calc_mode == "Manual Set (Heated SF)":
        direct_cost_sf = base_direct_cost_sf_input
        struct_cost_sf = direct_cost_sf * aux_ratio
        our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
        target_heated_hard_cost = direct_cost_sf * sqft
        target_direct_hard_cost = target_heated_hard_cost + our_aux_cost_total
        comp_equivalent_arv = (isolated_heated_rate * sqft) + (aux_sqft_total * (isolated_heated_rate * aux_ratio)) + additional_foundation_cost
        if appraisal_mode != "Income Approach (GRM)":
            arv_per_unit = comp_equivalent_arv
            
        total_construction_budget = target_direct_hard_cost * indirect_multiplier * (1.0 + gc_fee_pct) if gc_fee_mode == "Percentage of Hard Costs (%)" else (target_direct_hard_cost * indirect_multiplier) + custom_gc_fee
            
    elif cost_calc_mode == "Reverse-Engineer from Appraisal":
        total_construction_budget = arv_per_unit * target_const_budget_pct
        if gc_fee_mode == "Percentage of Hard Costs (%)":
            target_direct_hard_cost = total_construction_budget / (indirect_multiplier * (1.0 + gc_fee_pct))
        else:
            target_direct_hard_cost = (total_construction_budget - custom_gc_fee) / indirect_multiplier
            
        direct_cost_sf = max(0, (target_direct_hard_cost - additional_foundation_cost) / effective_project_heated_sf) if effective_project_heated_sf > 0 else 0
        struct_cost_sf = direct_cost_sf * aux_ratio
        our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
        target_heated_hard_cost = direct_cost_sf * sqft
        comp_equivalent_arv = arv_per_unit
        
    else: # Reverse-Engineer from Primary Comp
        comp_equivalent_arv = (isolated_heated_rate * sqft) + (aux_sqft_total * (isolated_heated_rate * aux_ratio)) + additional_foundation_cost
        total_construction_budget = comp_equivalent_arv * target_const_budget_pct
        if gc_fee_mode == "Percentage of Hard Costs (%)":
            target_direct_hard_cost = total_construction_budget / (indirect_multiplier * (1.0 + gc_fee_pct))
        else:
            target_direct_hard_cost = (total_construction_budget - custom_gc_fee) / indirect_multiplier
            
        direct_cost_sf = max(0, (target_direct_hard_cost - additional_foundation_cost) / effective_project_heated_sf) if effective_project_heated_sf > 0 else 0
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
        target_direct_hard_cost = target_heated_hard_cost + our_aux_cost_total
        comp_equivalent_arv = 0 
        total_construction_budget = target_direct_hard_cost * indirect_multiplier * (1.0 + gc_fee_pct) if gc_fee_mode == "Percentage of Hard Costs (%)" else (target_direct_hard_cost * indirect_multiplier) + custom_gc_fee

    elif cost_calc_mode == "Reverse-Engineer from Appraisal":
        total_construction_budget = arv_per_unit * target_const_budget_pct
        if gc_fee_mode == "Percentage of Hard Costs (%)":
            target_direct_hard_cost = total_construction_budget / (indirect_multiplier * (1.0 + gc_fee_pct))
        else:
            target_direct_hard_cost = (total_construction_budget - custom_gc_fee) / indirect_multiplier
        target_heated_hard_cost = max(0, target_direct_hard_cost - our_aux_cost_total)
        direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0
        comp_equivalent_arv = arv_per_unit
        
    else: # Reverse from Comp
        comp_equivalent_arv = (isolated_heated_rate * sqft) + our_aux_cost_total
        total_construction_budget = comp_equivalent_arv * target_const_budget_pct
        if gc_fee_mode == "Percentage of Hard Costs (%)":
            target_direct_hard_cost = total_construction_budget / (indirect_multiplier * (1.0 + gc_fee_pct))
        else:
            target_direct_hard_cost = (total_construction_budget - custom_gc_fee) / indirect_multiplier
        target_heated_hard_cost = max(0, target_direct_hard_cost - our_aux_cost_total)
        direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0

# Unified component rates across UI display
front_porch_cost_sf = struct_cost_sf
back_porch_cost_sf = struct_cost_sf
storage_cost_sf = struct_cost_sf

struct_total_cost = struct_sqft * struct_cost_sf
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf
storage_cost = storage_sqft * storage_cost_sf
outdoor_aux_subtotal_unit = front_porch_cost + back_porch_cost + storage_cost

heated_hard_cost = sqft * direct_cost_sf
blended_cost_per_sf = (heated_hard_cost + our_aux_cost_total) / total_under_roof_sqft if total_under_roof_sqft > 0 else 0

# Base project hard costs
total_hard_cost = target_direct_hard_cost * units
total_arv = arv_per_unit * units
loan_total = total_arv * refi_ltv

# 5.2 Indirects Build Up
permits_insurance_cost = total_hard_cost * indirect_permits_pct
temp_facilities_cost = total_hard_cost * indirect_temp_facilities_pct
fee_basis = total_hard_cost + permits_insurance_cost + temp_facilities_cost
default_gc_fee = custom_gc_fee if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else fee_basis * gc_fee_pct
total_indirect_costs = permits_insurance_cost + temp_facilities_cost + default_gc_fee

total_land_default = land_basis * units
total_soft_default = 5500 * units


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

total_const = total_hard_cost + total_indirect_costs
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
dscr_variance = actual_dscr - target_dscr_rate
monthly_cash_flow = monthly_noi - total_monthly_pi
monthly_cash_flow_per_door = monthly_cash_flow / units if units > 0 else 0

net_cash_at_closing = loan_total - actual_const_loan - refi_closing_fee - default_buydown_cost
cash_surplus = net_cash_at_closing - seed_capital
retained_equity = total_arv - loan_total
day1_wealth = default_gc_fee + max(0.0, cash_surplus) + retained_equity

btr_finance_closing = carry_int_base + const_closing_fee + refi_closing_fee + default_buydown_cost
lot_benchmark = total_arv * lot_cost_pct
developer_margin = total_arv - (lot_benchmark + total_hard_cost + total_indirect_costs + total_soft_default + btr_finance_closing)

# ==========================================
# --- PAGE HEADER ---
# ==========================================
st.title("🏗️ BTR Pro Forma Engine")
st.markdown("### Wickboldt Capital — *Today's Foundation. Tomorrow's Legacy.*")
st.divider()

# --- PROJECT INFO ---
st.markdown("### 📋 Project Information")
top_col1, top_col2, top_col3 = st.columns([2, 2, 1])
project_name = top_col1.text_input("Project Title", placeholder="e.g. Phase 1 - 24-Lot Build-to-Rent")
project_address = top_col2.text_input("Project Address", placeholder="e.g. Rogers Moore Parkway, Hammond, LA")
report_date = datetime.now().strftime("%B %d, %Y")

sub_col1, sub_col2, sub_col3 = st.columns([1, 1, 2])
project_beds = sub_col1.number_input("Beds per Unit", min_value=1, value=3, step=1)
project_baths = sub_col2.number_input("Baths per Unit", min_value=1.0, value=2.0, step=0.5)

# --- DYNAMIC EXECUTIVE SUMMARY ---
address_display = project_address if project_address else "[Project Address]"
capital_recovery_text = "nearly 100% capital recovery" if -5000 <= cash_surplus <= 5000 else (f"a complete capital recovery with a \${cash_surplus:,.0f} surplus" if cash_surplus > 5000 else f"a capital recovery requiring \${-cash_surplus:,.0f} in retained seed capital")

executive_summary_text = (
    f"**Executive Summary:**\n"
    f"This technical brief outlines the pro forma and operational mechanics for a {units}-unit Build-to-Rent (BTR) "
    f"single-family residential project located at {address_display}. Utilizing a {sqft:,.0f} SF heated footprint "
    f"with a {struct_sqft:,.0f} SF integrated {st.session_state.structure_type.lower()}, the model reverse-engineers "
    f"national production builder economics to establish a target appraisal value (ARV) of \${arv_per_unit:,.0f} per home. "
    f"By deploying Wickboldt Capital as the managing general contractor, the project successfully captures active "
    f"construction management revenue while executing a commercial takeout refinance.\n\n"
    f"With a {build_months}-month construction timeline factored into carrying costs, this structure achieves "
    f"{capital_recovery_text}, a compliant {actual_dscr:.2f}x DSCR generating \${monthly_cash_flow_per_door:,.0f}/month "
    f"in net passive cash flow per door, and scalable wealth creation totaling \${day1_wealth:,.0f} across the "
    f"{units}-unit build program."
)

st.info(executive_summary_text.replace("$", r"\$"))
st.divider()

ui_top_metrics = st.container()
ui_op_metrics = st.container()
ui_decision_dashboard = st.container()
st.divider()

# ==========================================
# --- 1. POPULATE EXECUTIVE METRICS DASHBOARD ---
# ==========================================
with ui_top_metrics:
    st.markdown("### 1. Project Capital & Valuation Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    # Metric 1: Takeout Loan vs Total Project Basis
    refi_vs_basis = loan_total - total_project_basis
    col1.metric("Takeout Loan Proceeds", f"${loan_total:,.0f}", f"{refi_vs_basis:+,.0f} vs Project Basis", delta_color="normal")
    
    # Metric 2: Day-1 Seed Capital Status
    if seed_capital > 0:
        col2.metric("Day-1 Seed Capital", f"${seed_capital:,.0f}", "-Requires Cash Reserves", delta_color="normal")
    else:
        col2.metric("Day-1 Seed Capital", "$0", "Fully Funded", delta_color="normal")
        
    # Metric 3 & 4
    if cash_surplus >= 0:
        deal_health_color = "normal" 
        surplus_title = "Tax-Free Cash Surplus"
        surplus_delta = "Capital Recovered"
    else:
        deal_health_color = "inverse" 
        surplus_title = "Trapped Seed Capital"
        surplus_delta = "Loss at Closing"
        
    col3.metric("Under-Roof Blended Cost", f"${blended_cost_per_sf:.2f} / SF", f"{total_under_roof_sqft:,} Total SF Under Roof")
    col4.metric(surplus_title, f"${cash_surplus:,.0f}", surplus_delta, delta_color=deal_health_color)

with ui_op_metrics:
    st.markdown("### 🏢 Operating & DSCR Metrics")
    op1, op2, op3, op4 = st.columns(4)
    
    cf_pass = monthly_cash_flow_per_door >= target_min_cashflow_per_door
    
    arv_label = "Derived Unit ARV (Price/SF)" if appraisal_mode == "Sales Comp (Price/SF)" else "Derived Unit ARV (GRM)"
    op1.metric(arv_label, f"${arv_per_unit:,.0f}", f"${total_arv:,.0f} Total ARV")
    op2.metric("Actual DSCR Rate", f"{actual_dscr:.2f}x", f"Target: {target_dscr_rate:.2f}x", delta_color="normal" if actual_dscr >= target_dscr_rate else "inverse")
    op3.metric("Monthly Cash Flow", f"${monthly_cash_flow:,.0f} /mo", f"${monthly_cash_flow*12:,.0f} Annual", delta_color="normal" if cf_pass else "inverse")
    op4.metric("Monthly P&I Payment", f"${total_monthly_pi:,.0f} /mo", f"{refi_term_years}Yr @ {net_refi_rate*100:.3f}%")

with ui_decision_dashboard:
    st.markdown("### 🚦 Go/No-Go Investment Decision Dashboard")
    dscr_pass = actual_dscr >= target_dscr_rate
    cash_pass = cash_surplus >= 0
    
    dscr_light = "🟢 GREEN LIGHT" if dscr_pass else "🔴 RED LIGHT"
    cf_light = "🟢 GREEN LIGHT" if cf_pass else "🔴 RED LIGHT"
    cash_light = "🟢 GREEN LIGHT" if cash_pass else "🔴 RED LIGHT"

    dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
    dash_col1.metric("DSCR Underwriting Status", dscr_light, f"Actual: {actual_dscr:.2f}x (Target: {target_dscr_rate:.2f}x)", delta_color="normal" if dscr_pass else "inverse")
    dash_col2.metric("Cash Flow Status", cf_light, f"Actual: ${monthly_cash_flow_per_door:,.0f}/door (Target: ${target_min_cashflow_per_door:,.0f})", delta_color="normal" if cf_pass else "inverse")
    dash_col3.metric("Capital Recovery Status", cash_light, f"${cash_surplus:,.0f} at Refi Close", delta_color="normal" if cash_pass else "inverse")
    dash_col4.metric("Day-1 Wealth Creation", f"${day1_wealth:,.0f}", f"${day1_wealth/units:,.0f} per door", delta_color="normal")


# ==========================================
# --- 2. COMP AUDIT DASHBOARD ---
# ==========================================
st.markdown("### 2. Market Comp Valuation Audit")

if st.session_state.comp_address:
    st.caption(f"📍 **Active Comp:** {st.session_state.comp_address} | Isolated Heated Shell Rate: **\${isolated_heated_rate:.2f} / SF** | Implied Aux Rate: **\${comp_aux_rate_sf:.2f} / SF**")
else:
    st.caption(f"📊 Isolated Heated Shell Rate: **\${isolated_heated_rate:.2f} / SF** | Implied Aux Rate: **\${comp_aux_rate_sf:.2f} / SF**")

with st.expander("🧮 View Comp Math Audit & Raw API Data", expanded=False):
    comp_under_roof = comp_heated_sf + comp_aux_sqft
    comp_blended_rate = comp_price / comp_under_roof if comp_under_roof > 0 else 0
    
    st.markdown("**2.1 Raw Blended Rate (Total Price ÷ Total Under-Roof SF)**")
    st.code(f"${comp_price:,.0f} ÷ {comp_under_roof:,.0f} Total SF = ${comp_blended_rate:.2f} / SF (Blended)")
    
    if aux_cost_mode == "Percentage of Heated Rate (%)":
        st.markdown(f"**2.2 True Isolated Heated Shell Rate (Algebraic Extraction)**")
        st.caption(f"If we simply halved the blended rate for the aux space, the total price would fall short. To perfectly distribute the \${comp_price:,.0f} across the spaces at a 100% / {aux_ratio*100:.0f}% ratio, we solve for the 'Effective Equivalent' square footage:")
        st.code(f"Step 1: Find Equivalent SF\n{comp_heated_sf:,.0f} Heated SF + ({comp_aux_sqft:,.0f} Aux SF × {aux_ratio:.2f}) = {effective_comp_heated_sf:,.1f} Eq. SF\n\nStep 2: Solve for True Heated Rate\n${comp_price:,.0f} ÷ {effective_comp_heated_sf:,.1f} Eq. SF = ${isolated_heated_rate:.2f} / Heated SF\n\nStep 3: Solve for True Aux Rate\n${isolated_heated_rate:.2f} × {aux_ratio:.2f} = ${comp_aux_rate_sf:.2f} / Aux SF")
    else:
        st.markdown(f"**2.2 True Isolated Heated Shell Rate (Fixed Aux Value: \${aux_fixed_cost_sf:.2f} / SF)**")
        st.code(f"(${comp_price:,.0f} - ${comp_aux_value:,.0f} Aux Value) ÷ {comp_heated_sf:,.0f} SF = ${isolated_heated_rate:.2f} / SF")
        
    if st.session_state.raw_api_data and st.session_state.get("comp_entry_mode") == "RentCast Live API Fetch":
        st.json(st.session_state.raw_api_data)
st.divider()


# ==========================================
# --- 3. GRANULAR DIRECT HARD COST BUILDUP & ROLL-UP ---
# ==========================================
st.markdown("### 3. Granular Direct Hard Cost Buildup & Roll-up")

granular_summary_text = (
    f"Below is the itemized cost buildup per trade division required to achieve the baseline "
    f"**\${direct_cost_sf:.2f}/SF (\${heated_hard_cost:,.0f})** heated living area cost and the "
    f"**\${struct_cost_sf:.2f}/SF (\${struct_total_cost:,.0f})** {st.session_state.structure_type.lower()} cost, "
    f"yielding a blended direct hard cost of **\${blended_cost_per_sf:.2f}/SF (\${target_direct_hard_cost:,.0f})** under roof per unit."
)
st.info(granular_summary_text.replace("$", r"\$"))

granular_mode = st.radio("Buildup Entry Mode", ["Auto-Proportional (Linked to Master Model)", "Manual Custom Entry (Bottom-Up)"], horizontal=True)

# Exact NAHB 8 Stages & 36 Components Mapping
raw_heated_divs = [
    ("I. SITE WORK", 7.6, True),
    ("- Building Permit Fees", 1.8, False),
    ("- Impact Fee", 1.5, False),
    ("- Water & Sewer Fees / Inspections", 1.5, False),
    ("- Architecture & Engineering", 1.5, False),
    ("- Site Work - Other", 1.3, False),

    ("II. FOUNDATIONS", 10.5, True),
    ("- Excavation, Foundation, Concrete, Backfill", 10.0, False),
    ("- Foundations - Other", 0.5, False),

    ("III. FRAMING", 16.6, True),
    ("- Framing (including roof)", 11.6, False),
    ("- Trusses", 3.0, False),
    ("- Sheathing", 1.5, False),
    ("- General Metal, Steel", 0.4, False),
    ("- Framing - Other", 0.1, False),

    ("IV. EXTERIOR FINISHES", 13.4, True),
    ("- Exterior Wall Finish", 5.7, False),
    ("- Roofing", 3.9, False),
    ("- Windows and Doors (incl. garage door)", 3.7, False),
    ("- Exterior Finishes - Other", 0.1, False),

    ("V. MAJOR SYSTEMS ROUGH-INS", 19.2, True),
    ("- Plumbing (except fixtures)", 6.3, False),
    ("- Electrical (except fixtures)", 6.4, False),
    ("- HVAC", 6.3, False),
    ("- Major Systems - Other", 0.2, False),

    ("VI. INTERIOR FINISHES", 24.1, True),
    ("- Insulation", 1.6, False),
    ("- Drywall", 3.3, False),
    ("- Interior Trims, Doors, and Mirrors", 3.0, False),
    ("- Painting", 2.6, False),
    ("- Lighting", 1.3, False),
    ("- Cabinets, Countertops", 4.4, False),
    ("- Appliances", 1.7, False),
    ("- Flooring", 3.6, False),
    ("- Plumbing Fixtures", 1.8, False),
    ("- Fireplace", 0.6, False),
    ("- Interior Finishes - Other", 0.2, False),

    ("VII. FINAL STEPS", 6.5, True),
    ("- Landscaping", 2.2, False),
    ("- Outdoor Structures (deck, patio, porches)", 1.1, False),
    ("- Driveway", 2.3, False),
    ("- Clean Up", 0.9, False),

    ("VIII. OTHER", 2.1, True),
    ("- Miscellaneous / Other", 2.1, False),
]

raw_struct_divs = [("AUXILIARY: CARPORT / GARAGE", 35.00, True)]
pdf_granular_data = []

if granular_mode == "Auto-Proportional (Linked to Master Model)":
    st.markdown(f"#### 3.1 Heated Living Area ({sqft} SF @ \${direct_cost_sf:.2f} / SF)")
    h_data = {"Division / Trade Level": [], "Live Cost / SF": [], "Per Unit Cost": []}
    for name, base_val, is_header in raw_heated_divs:
        live_sf = direct_cost_sf * (base_val / 100.0)
        if is_header:
            h_data["Division / Trade Level"].append(f"{name}")
            h_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            h_data["Per Unit Cost"].append(f"${live_sf * sqft:,.0f}")
            pdf_granular_data.append((name, live_sf, live_sf * sqft, live_sf * sqft * units, True))
        else:
            h_data["Division / Trade Level"].append(f"   {name}")
            h_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            h_data["Per Unit Cost"].append(f"${live_sf * sqft:,.0f}")
            pdf_granular_data.append((f"   {name}", live_sf, live_sf * sqft, live_sf * sqft * units, False))
    st.dataframe(pd.DataFrame(h_data), hide_index=True, use_container_width=True)
    
    st.markdown(f"#### 3.2 {st.session_state.structure_type} Auxiliary ({struct_sqft} SF @ \${struct_cost_sf:.2f} / SF)")
    s_data = {"Component Level": [], "Live Cost / SF": [], "Per Unit Cost": []}
    for name, base_val, is_header in raw_struct_divs:
        live_sf = struct_cost_sf * (base_val / 35.0)
        s_data["Component Level"].append(name)
        s_data["Live Cost / SF"].append(f"${live_sf:.2f}")
        s_data["Per Unit Cost"].append(f"${live_sf * struct_sqft:,.0f}")
    st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True)
else:
    st.markdown(f"#### 3.1 Heated Living Area ({sqft} SF)")
    hl_heated = []
    current_header = ""
    for name, base, is_h in raw_heated_divs:
        if is_h:
            current_header = name
        else:
            hl_heated.append({"Category": current_header, "Division / Component": name.replace("- ", ""), "Cost / SF": direct_cost_sf * (base/100.0)})
    
    df_manual = pd.DataFrame(hl_heated)
    edited_h = st.data_editor(df_manual.drop(columns=["Category"]), column_config={"Division / Component": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True)
    
    direct_cost_sf = edited_h["Cost / SF"].sum()
    df_manual["Cost / SF"] = edited_h["Cost / SF"]
    
    # Intelligently re-aggregate Manual Custom Items back into the 8 NAHB Headers for the PDF Engine
    for cat in df_manual["Category"].unique():
        cat_df = df_manual[df_manual["Category"] == cat]
        cat_sum = cat_df["Cost / SF"].sum()
        pdf_granular_data.append((cat, cat_sum, cat_sum * sqft, cat_sum * sqft * units, True))
        for _, row in cat_df.iterrows():
            live_sf = row["Cost / SF"]
            pdf_granular_data.append((f"   - {row['Division / Component']}", live_sf, live_sf * sqft, live_sf * sqft * units, False))
    
    st.markdown(f"#### 3.2 {st.session_state.structure_type} Auxiliary ({struct_sqft} SF)")
    hl_struct = [{"Component Level": name, "Cost / SF": struct_cost_sf * (base/35.0)} for name, base, is_h in raw_struct_divs]
    edited_s = st.data_editor(pd.DataFrame(hl_struct), column_config={"Component Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True)
    struct_cost_sf = edited_s["Cost / SF"].sum()

st.markdown("#### 3.3 Auxiliary, Foundation & Outdoor Living")
p_data = {
    "Component": ["Front Porch", "Back Porch", "Storage Room", "Addit. Foundation / Elevation", "TOTAL AUX/OUTDOOR"],
    "Area (SF)": [f"{front_porch_sqft} SF", f"{back_porch_sqft} SF", f"{storage_sqft} SF", "Site Specific", "Total"],
    "Cost / SF": [f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", f"${storage_cost_sf:.2f}", "-", "-"],
    "Total Amount": [f"${front_porch_cost:,.0f}", f"${back_porch_cost:,.0f}", f"${storage_cost:,.0f}", f"${additional_foundation_cost:,.0f}", f"${our_aux_cost_total:,.0f}"]
}
st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)

# Master Direct Hard Cost Roll-up Table
st.markdown("#### 3.4 Direct Hard Cost Master Roll-up")
direct_rollup_df = pd.DataFrame({
    "Category / Major Sub-Assembly": [
        f"1. Heated Living Area ({sqft:,} SF)",
        f"2. {st.session_state.structure_type} Structure ({struct_sqft:,} SF)",
        f"3. Outdoor & Storage Spaces ({front_porch_sqft + back_porch_sqft + storage_sqft:,} SF)",
        "4. Site Foundation & Elevation Premium",
        "TOTAL DIRECT HARD COST BUDGET"
    ],
    "Effective Rate": [
        f"${direct_cost_sf:.2f} / Heated SF",
        f"${struct_cost_sf:.2f} / SF",
        f"${struct_cost_sf:.2f} / SF (Avg)",
        "Flat Lump Sum",
        f"${blended_cost_per_sf:.2f} / SF Under Roof"
    ],
    "Per Unit Cost ($)": [
        heated_hard_cost,
        struct_total_cost,
        outdoor_aux_subtotal_unit,
        additional_foundation_cost,
        target_direct_hard_cost
    ],
    "Project Total ($)": [
        heated_hard_cost * units,
        struct_total_cost * units,
        outdoor_aux_subtotal_unit * units,
        additional_foundation_cost * units,
        total_hard_cost
    ]
})

st.dataframe(
    direct_rollup_df.style.format({
        "Per Unit Cost ($)": "${:,.0f}",
        "Project Total ($)": "${:,.0f}"
    }),
    hide_index=True,
    use_container_width=True
)
st.divider()


# ==========================================
# --- 4. BANK STRESS TEST BREAKDOWN ---
# ==========================================
st.markdown("### 4. Construction Lender Loan Cap & Stress Test")

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
    st.warning(f"**Seed Capital Required:** The bank will fund **\${actual_const_loan:,.0f}** based on the appraised value. Your Total Construction Basis is **\${total_construction_basis:,.0f}**. You must bring **\${seed_capital:,.0f}** in Day-1 Seed Capital (Reserves).")
else:
    st.success(f"**Fully Funded:** The bank's loan value of **\${actual_const_loan:,.0f}** covers your entire construction basis. No Day-1 Seed Capital is required.")
st.divider()


# ==========================================
# --- 5. DEVELOPER CAPITAL & CONSTRUCTION LEDGER ---
# ==========================================
st.markdown("### 5. Developer Capital & Construction Ledger")

land_eq_text = (
    f"**Land Equity Capture:** The Pro Forma valuation benchmark values the lot at {lot_cost_pct*100:.1f}% "
    f"(**\${lot_benchmark:,.0f}**), while the developer's actual out-of-pocket acquisition cost is "
    f"**\${total_land_default:,.0f}**. This gap represents immediate land equity."
)
st.info(land_eq_text.replace("$", r"\$"))

col1, col2 = st.columns(2)
with col1:
    st.markdown("#### Pro Forma Valuation Allocation")
    val_alloc_df = pd.DataFrame({
        "Component": [f"Finished Lot Benchmark ({lot_cost_pct*100:.1f}%)", "Adjusted BTR Hard Costs", "Indirects + GC Fee", "Soft Costs & Permitting", "Finance, Closing & Buydown", "Built-in Developer Margin", "Total Appraised Value (ARV)"],
        "Amount": [f"${lot_benchmark:,.0f}", f"${total_hard_cost:,.0f}", f"${total_indirect_costs:,.0f}", f"${total_soft_default:,.0f}", f"${btr_finance_closing:,.0f}", f"${developer_margin:,.0f}", f"${total_arv:,.0f}"]
    })
    st.dataframe(val_alloc_df, hide_index=True, use_container_width=True)
    
with col2:
    st.markdown("#### Financing Breakdown")
    fin_breakdown_df = pd.DataFrame({
        "Component": ["Const. Loan Closing Fees", "Carrying Interest", "Perm. Takeout Fees", f"Rate Buydown ({buydown_pts} pts)"],
        "Amount": [f"${const_closing_fee:,.0f}", f"${carry_int_base:,.0f}", f"${refi_closing_fee:,.0f}", f"${default_buydown_cost:,.0f}"],
        "Details": ["", f"({build_months} months @ {const_rate*100:.2f}% on {avg_draw_pct*100:.0f}% avg drawn balance)", "", ""]
    })
    st.dataframe(fin_breakdown_df, hide_index=True, use_container_width=True)

st.markdown("#### Capital Outlay & Transaction Scope")
transaction_df = pd.DataFrame({
    "Phase / Project Cash Event": ["1. Seed Capital Outlay", "2. Total Construction Cost", "3. Soft Costs & Permitting", "4. Construction Financing Costs", "5. Permanent Refinance Takeout", "Total Project Capital Basis"],
    "Transaction Scope": ["Out-of-pocket finished lot acquisition", "Baseline Hard Costs + Indirects + GC Fee", "Architecture, civil engineering, parish permits, builder's risk", f"Lender closing fees (\${const_closing_fee:,.0f}) & accrued interest (\${carry_int_base:,.0f})", f"Commercial fees (\${refi_closing_fee:,.0f}) + {buydown_pts} pt rate buydown (\${default_buydown_cost:,.0f})", "All-in total cost to build, finance, close, and stabilize"],
    "Actual Capital Outlay": [f"-${total_land_default:,.0f}", f"-${total_const:,.0f}", f"-${total_soft_default:,.0f}", f"-${const_closing_fee + carry_int_base:,.0f}", f"-${refi_closing_fee + default_buydown_cost:,.0f}", f"-${total_project_basis:,.0f}"]
})
st.dataframe(transaction_df, hide_index=True, use_container_width=True)
st.divider()


# ==========================================
# --- 6. OPERATING PERFORMANCE & DSCR ---
# ==========================================
st.markdown("### 6. Operating Performance Summary")
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
st.divider()


# ==========================================
# --- 7. REFINANCE WATERFALL & WEALTH ---
# ==========================================
st.markdown("### 7. Refinance Cash Waterfall & Day-1 Wealth")
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


# ==========================================
# --- 8. STRATEGY COMPARISON: RETAIL VS BTR ---
# ==========================================
st.markdown("### 8. Strategy Comparison: Retail Sell vs. Build-to-Rent")

strategy_comparison_text = (
    f"This comparison models the one-time taxable cash event of the National Builder model versus "
    f"the wealth-creation mechanics of the BTR model on the exact same project ({units} units, "
    f"{sqft:,.0f} SF heated with {struct_sqft:,.0f} SF {st.session_state.structure_type.lower()}, "
    f"\${total_arv:,.0f} ARV)."
)
st.caption(strategy_comparison_text.replace("$", r"\$"))

retail_sales_costs = total_arv * 0.08
retail_total_invested = total_land_default + total_const + total_soft_default + retail_sales_costs
retail_net_cash = total_arv - retail_total_invested

strategy_data = {
    "Financial Metric": [
        "Land Basis",
        "Direct Hard Costs",
        "Total Construction Cost (incl. GC & Indirects)",
        "Soft Costs & Permitting",
        "Sales & Transaction Closing Costs",
        "Total Capital Invested",
        "Gross Revenue / Permanent Loan Proceeds",
        "Net Cash Event at Closing",
        "Asset Retained on Balance Sheet?",
        "Ongoing Monthly Cash Flow"
    ],
    "National Builder (Retail Sell)": [
        f"${total_land_default:,.0f}",
        f"${total_hard_cost:,.0f} (Baseline)",
        f"${total_const:,.0f}",
        f"${total_soft_default:,.0f}",
        f"${retail_sales_costs:,.0f} (~8% Realtor & concessions)",
        f"${retail_total_invested:,.0f}",
        f"${total_arv:,.0f} (Retail sales price)",
        f"+${retail_net_cash:,.0f} (Taxable ordinary income)",
        "No",
        "$0"
    ],
    "Build-to-Rent (Commercial DSCR Takeout)": [
        f"${total_land_default:,.0f}",
        f"${total_hard_cost:,.0f}",
        f"${total_const:,.0f}",
        f"${total_soft_default:,.0f}",
        f"${btr_finance_closing:,.0f} (Const. finance, takeout, buydown)",
        f"${total_project_basis:,.0f}",
        f"${loan_total:,.0f} ({refi_ltv*100:.0f}% LTV DSCR Loan)",
        f"${cash_surplus:,.0f} (Seed Capital Retained)" if cash_surplus < 0 else f"+${cash_surplus:,.0f} (Tax-Free Cash Out)",
        f"Yes (${total_arv:,.0f} Asset, ${retained_equity:,.0f} Equity)",
        f"+${monthly_cash_flow_per_door:,.0f} / month / door"
    ]
}

st.dataframe(pd.DataFrame(strategy_data), hide_index=True, use_container_width=True)

strategy_footnote_text = (
    f"***Note:** The BTR model captures \${default_gc_fee:,.0f} in GC Fees during the build. "
    f"The {build_months}-month construction timeline incurs carrying costs such that the takeout distribution "
    f"yields a net cash event of \${cash_surplus:,.0f} at closing. Total Day-1 Created Value equals \${day1_wealth:,.0f}.*"
)
st.info(strategy_footnote_text.replace("$", r"\$"))
st.divider()


# ==========================================
# --- 9. REVERSE-ENGINEERING BREAKDOWN ---
# ==========================================
if cost_calc_mode in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"]:
    st.markdown("### 9. Retail Comp & Appraisal Reverse-Engineering Breakdown")
    
    reference_price = arv_per_unit if cost_calc_mode == 'Reverse-Engineer from Appraisal' else comp_equivalent_arv
    ref_price_sf = reference_price / sqft if sqft > 0 else 0
    
    rev_eng_summary = (
        f"**Reverse-Engineering the Target Budget:**\n\nBased on the comp's isolated rates, your specific "
        f"{sqft} SF project has an estimated ARV of **\${reference_price:,.0f}** (approximately "
        f"\${ref_price_sf:,.2f} per heated square foot). We are reverse-engineering *this* value to isolate "
        f"the pure direct hard costs from finished land, builder corporate margins, indirects, and soft costs. "
        f"This ensures the physical build budget perfectly aligns with proven market economics."
    )
    st.info(rev_eng_summary.replace("$", r"\$"))
    
    breakdown_data = {
        "Cost Category": [
            f"Project Target ARV (Derived from Comp)", 
            "(-) Finished Lot Cost", 
            "(-) Builder Profit (Pre-tax)", 
            "(-) Overhead & General Expenses",
            "(-) Sales & Marketing", 
            "(-) Financing Costs", 
            "= Total Construction Budget (Direct + Indirect)", 
            "(-) Indirects (Permits, Temp Site, GC Fee)",
            "= Direct Hard Cost Budget",
            "(-) Fixed Auxiliary & Elevation Costs", 
            "= Available Budget for Heated Shell"
        ],
        "Value ($)": [
            f"${reference_price:,.0f}", 
            f"-${reference_price * lot_cost_pct:,.0f}", 
            f"-${reference_price * profit_margin_pct:,.0f}", 
            f"-${reference_price * overhead_pct:,.0f}", 
            f"-${reference_price * sales_pct:,.0f}", 
            f"-${reference_price * finance_pct:,.0f}", 
            f"${total_construction_budget:,.0f}", 
            f"-${total_indirect_costs:,.0f}",
            f"${target_direct_hard_cost:,.0f}",
            f"-${our_aux_cost_total:,.0f}", 
            f"${target_heated_hard_cost:,.0f}"
        ],
        "Description": [
            "Projected value of your build using the Comp's isolated rates.",
            "Land acquisition, grading, and utility infrastructure.",
            "Net profit margin retained by the homebuilding company.",
            "Office staff, software, vehicles, insurance, and administrative tools.",
            "Sales commissions and marketing costs to close the deal.",
            "Short-term interest paid on the builder's construction loan.",
            "Total budget available for all physical construction (Direct + Indirect).",
            "Permits, site facilities, and GC management fees.",
            "Total budget exclusively for physical structure and materials.",
            "Locked budget required for outdoor footprint and foundation elevation.",
            f"Yields exactly ${direct_cost_sf:.2f} / SF across {sqft} Heated SF."
        ]
    }
    st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)
    st.divider()


# ==========================================
# --- 10. PDF GENERATION ENGINE ---
# ==========================================
st.markdown("### 🖨️ 10. Export Enterprise PDF Report")
pdf_detail_mode = st.radio(
    "Construction Budget Detail Level for PDF:",
    ["Full 36-Component Breakdown", "8 Major NAHB Categories Only", "High-Level Roll-up Only"],
    horizontal=True
)

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

def create_pdf(detail_mode):
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

    # 1. EXECUTIVE NARRATIVE SUMMARY
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 1. Executive Narrative Summary", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    clean_summary = executive_summary_text.replace("**Executive Summary:**\n", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_summary)
    pdf.ln(5)

    # 2. EXECUTIVE METRICS & WEALTH CREATION
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 2. Capital Metrics & Wealth Creation", ln=1, fill=True)
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
    
    pdf.cell(100, 7, "Net Monthly Cash Flow per Door:", 0, 0)
    pdf.cell(90, 7, f"${monthly_cash_flow_per_door:,.0f}", 0, 1, 'R')
    
    pdf.cell(100, 7, "Total Day-1 Wealth Created:", 0, 0)
    pdf.cell(90, 7, f"${day1_wealth:,.0f}", 0, 1, 'R')
    pdf.ln(5)

    # 3. REVERSE ENGINEERING (IF APPLICABLE)
    if cost_calc_mode in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"]:
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 3. Retail Comp & Appraisal Reverse-Engineering", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        
        # Add dynamic narrative to PDF
        rev_eng_summary_pdf = (
            f"Based on the comp's isolated rates, your specific {sqft} SF project has an estimated ARV "
            f"of ${reference_price:,.0f}. We are reverse-engineering this value to isolate the pure direct "
            f"hard costs from finished land, builder corporate margins, indirects, and soft costs. This ensures "
            f"the physical build budget perfectly aligns with proven market economics."
        )
        pdf.multi_cell(0, 6, rev_eng_summary_pdf.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(3)
        
        pdf.cell(130, 7, "Project Target ARV (Derived from Comp):", 0, 0)
        pdf.cell(60, 7, f"${reference_price:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Finished Lot Cost:", 0, 0)
        pdf.cell(60, 7, f"-${reference_price * lot_cost_pct:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Builder Profit (Pre-tax):", 0, 0)
        pdf.cell(60, 7, f"-${reference_price * profit_margin_pct:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Overhead & General Expenses:", 0, 0)
        pdf.cell(60, 7, f"-${reference_price * overhead_pct:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Sales & Marketing:", 0, 0)
        pdf.cell(60, 7, f"-${reference_price * sales_pct:,.0f}", 0, 1, 'R')
        pdf.cell(130, 7, "(-) Financing Costs:", 0, 0)
        pdf.cell(60, 7, f"-${reference_price * finance_pct:,.0f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 7, "= Total Construction Budget (Direct + Indirect):", 0, 0)
        pdf.cell(60, 7, f"${total_construction_budget:,.0f}", 0, 1, 'R')
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(130, 7, "(-) Indirects (Permits, Temp Site, GC Fee):", 0, 0)
        pdf.cell(60, 7, f"-${total_indirect_costs:,.0f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 7, "= Direct Hard Cost Budget:", 0, 0)
        pdf.cell(60, 7, f"${target_direct_hard_cost:,.0f}", 0, 1, 'R')
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(130, 7, "(-) Fixed Auxiliary & Elevation Costs:", 0, 0)
        pdf.cell(60, 7, f"-${our_aux_cost_total:,.0f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 7, "= Available Budget for Heated Shell:", 0, 0)
        pdf.cell(60, 7, f"${target_heated_hard_cost:,.0f}", 0, 1, 'R')
        pdf.ln(5)

    # 4. CONSTRUCTION BUILDUP SELECTION
    if detail_mode == "High-Level Roll-up Only":
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 4. Direct Hard Cost Master Roll-up", ln=1, fill=True)
        pdf.set_font("Arial", 'B', 9)
        
        pdf.set_font("Arial", '', 10)
        granular_summary_pdf = (
            f"Below is the itemized cost buildup per trade division required to achieve the baseline "
            f"${direct_cost_sf:.2f}/SF (${heated_hard_cost:,.0f}) heated living area cost and the "
            f"${struct_cost_sf:.2f}/SF (${struct_total_cost:,.0f}) {st.session_state.structure_type.lower()} cost, "
            f"yielding a blended hard cost of ${blended_cost_per_sf:.2f}/SF (${target_direct_hard_cost:,.0f}) under roof per unit."
        )
        pdf.multi_cell(0, 6, granular_summary_pdf.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(3)
        
        pdf.cell(85, 6, "Category / Major Sub-Assembly", 1, 0, 'C')
        pdf.cell(40, 6, "Effective Rate", 1, 0, 'C')
        pdf.cell(35, 6, "Per Unit Cost", 1, 0, 'C')
        pdf.cell(30, 6, "Project Total", 1, 1, 'C')
        
        for i, row in direct_rollup_df.iterrows():
            if i == len(direct_rollup_df) - 1:
                pdf.set_font("Arial", 'B', 9)
                pdf.set_fill_color(240, 240, 240)
                fill = True
            else:
                pdf.set_font("Arial", '', 9)
                fill = False
            
            pdf.cell(85, 6, str(row["Category / Major Sub-Assembly"]), 1, 0, 'L', fill=fill)
            pdf.cell(40, 6, str(row["Effective Rate"]), 1, 0, 'C', fill=fill)
            pdf.cell(35, 6, f"${row['Per Unit Cost ($)']:,.0f}", 1, 0, 'R', fill=fill)
            pdf.cell(30, 6, f"${row['Project Total ($)']:,.0f}", 1, 1, 'R', fill=fill)
            
    else:
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 4. Granular Direct Hard Cost Buildup", ln=1, fill=True)
        pdf.set_font("Arial", 'B', 9)
        
        pdf.set_font("Arial", '', 10)
        granular_summary_pdf = (
            f"Below is the itemized cost buildup per trade division required to achieve the baseline "
            f"${direct_cost_sf:.2f}/SF (${heated_hard_cost:,.0f}) heated living area cost and the "
            f"${struct_cost_sf:.2f}/SF (${struct_total_cost:,.0f}) {st.session_state.structure_type.lower()} cost, "
            f"yielding a blended hard cost of ${blended_cost_per_sf:.2f}/SF (${target_direct_hard_cost:,.0f}) under roof per unit."
        )
        pdf.multi_cell(0, 6, granular_summary_pdf.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(3)
        
        pdf.cell(90, 6, "Division / Trade Level", 1, 0, 'C')
        pdf.cell(30, 6, "Live Cost / SF", 1, 0, 'C')
        pdf.cell(35, 6, f"Per Unit ({sqft} SF)", 1, 0, 'C')
        pdf.cell(35, 6, "Project Total", 1, 1, 'C')
        
        for name, live_sf, unit_cost, proj_cost, is_header in pdf_granular_data:
            if detail_mode == "8 Major NAHB Categories Only" and not is_header:
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

    # 5. DEVELOPER CAPITAL & CONSTRUCTION LEDGER
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 5. Developer Capital & Construction Ledger", fill=True, ln=1)
    pdf.set_font("Arial", '', 10)
    
    land_eq_text_pdf = (
        f"The Pro Forma valuation benchmark values the lot at {lot_cost_pct*100:.1f}% (${lot_benchmark:,.0f}), "
        f"while the developer's actual out-of-pocket acquisition cost is ${total_land_default:,.0f}. "
        f"This gap represents immediate land equity."
    )
    pdf.multi_cell(0, 6, land_eq_text_pdf.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 6, "Pro Forma Valuation Allocation", 0, 0, 'L')
    pdf.cell(95, 6, "Financing Breakdown", 0, 1, 'L')
    
    pdf.set_font("Arial", '', 9)
    # Row 1
    pdf.cell(65, 5, f"Finished Lot Benchmark ({lot_cost_pct*100:.0f}%):", 0, 0, 'L')
    pdf.cell(30, 5, f"${lot_benchmark:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, "Const. Loan Closing Fees:", 0, 0, 'L')
    pdf.cell(30, 5, f"${const_closing_fee:,.0f}", 0, 1, 'R')
    # Row 2
    pdf.cell(65, 5, "Adjusted BTR Hard Costs:", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_hard_cost:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, "Carrying Interest:", 0, 0, 'L')
    pdf.cell(30, 5, f"${carry_int_base:,.0f}", 0, 1, 'R')
    # Row 3
    pdf.cell(65, 5, "Indirects + GC Fee:", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_indirect_costs:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, "Perm. Takeout Fees:", 0, 0, 'L')
    pdf.cell(30, 5, f"${refi_closing_fee:,.0f}", 0, 1, 'R')
    # Row 4
    pdf.cell(65, 5, "Soft Costs & Permitting:", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_soft_default:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, f"Rate Buydown ({buydown_pts} pts):", 0, 0, 'L')
    pdf.cell(30, 5, f"${default_buydown_cost:,.0f}", 0, 1, 'R')
    # Row 5
    pdf.cell(65, 5, "Finance, Closing & Buydown:", 0, 0, 'L')
    pdf.cell(30, 5, f"${btr_finance_closing:,.0f}", 0, 1, 'R')
    # Row 6
    pdf.cell(65, 5, "Built-in Developer Margin:", 0, 0, 'L')
    pdf.cell(30, 5, f"${developer_margin:,.0f}", 0, 1, 'R')
    # Row 7
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(65, 5, "Total Appraised Value (ARV):", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_arv:,.0f}", 0, 1, 'R')
    
    pdf.ln(5)
    
    # Transaction Table
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(50, 6, "Phase / Cash Event", 1, 0, 'C')
    pdf.cell(110, 6, "Transaction Scope", 1, 0, 'C')
    pdf.cell(30, 6, "Outlay", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    transactions = [
        ("1. Seed Capital Outlay", "Out-of-pocket finished lot acquisition", f"-${total_land_default:,.0f}"),
        ("2. Total Const. Cost", "Baseline Hard Costs + Indirects + GC Fee", f"-${total_const:,.0f}"),
        ("3. Soft Costs & Permitting", "Architecture, civil engineering, parish permits", f"-${total_soft_default:,.0f}"),
        ("4. Const. Finance Costs", f"Lender fees (${const_closing_fee:,.0f}) & interest (${carry_int_base:,.0f})", f"-${const_closing_fee + carry_int_base:,.0f}"),
        ("5. Perm. Takeout Fees", f"Comm. fees (${refi_closing_fee:,.0f}) + buydown (${default_buydown_cost:,.0f})", f"-${refi_closing_fee + default_buydown_cost:,.0f}")
    ]
    for e, s, a in transactions:
        pdf.cell(50, 6, e, 1, 0, 'L')
        pdf.cell(110, 6, s, 1, 0, 'L')
        pdf.cell(30, 6, a, 1, 1, 'R')
        
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(160, 6, "Total Project Capital Basis:", 1, 0, 'L')
    pdf.cell(30, 6, f"-${total_project_basis:,.0f}", 1, 1, 'R')
    pdf.ln(5)

    # 6. CONSTRUCTION LENDER LIMITS
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 6. Construction Bank Limits & Loan Cap", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    if const_bank_val_mode == "DSCR Stress Test":
        pdf.cell(100, 7, "Bank Assumed Rent & Target DSCR:", 0, 0)
        pdf.cell(90, 7, f"${const_bank_rent:,.0f}/mo | {const_bank_dscr:.2f}x DSCR", 0, 1, 'R')
        pdf.cell(100, 7, "Bank Vacancy & OpEx Deductions:", 0, 0)
        pdf.cell(90, 7, f"{const_bank_vac_pct*100:.1f}% Vac | {const_bank_opex_pct*100:.1f}% OpEx", 0, 1, 'R')
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

    # 7. REFINANCE CASH WATERFALL
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 7. Refinance Cash Waterfall (Payoff & Cash-Out)", ln=1, fill=True)
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
    pdf.ln(5)

    # 8. STRATEGY COMPARISON: RETAIL VS BTR
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 8. Strategy Comparison: Retail Sell vs. Build-to-Rent", ln=1, fill=True)
    pdf.set_font("Arial", '', 9)
    
    # Table Header
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(70, 6, "Financial Metric", 1, 0, 'C')
    pdf.cell(60, 6, "National Builder (Retail Sell)", 1, 0, 'C')
    pdf.cell(60, 6, "Build-to-Rent (DSCR Takeout)", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i in range(len(strategy_data["Financial Metric"])):
        metric = str(strategy_data["Financial Metric"][i])
        retail = str(strategy_data["National Builder (Retail Sell)"][i])
        btr = str(strategy_data["Build-to-Rent (Commercial DSCR Takeout)"][i])
        
        # Abbreviate for PDF constraints
        if "(~8% Realtor & concessions)" in retail:
            retail = retail.replace("(~8% Realtor & concessions)", "(8% Fees)")
        if "(Taxable ordinary income)" in retail:
            retail = retail.replace("(Taxable ordinary income)", "(Taxable)")
        if "(Const. finance, takeout, buydown)" in btr:
            btr = btr.replace("(Const. finance, takeout, buydown)", "(Financing Fees)")
        if "LTV DSCR Loan" in btr:
            btr = btr.replace(" LTV DSCR Loan", " LTV)")
        if "(Seed Capital Retained)" in btr:
            btr = btr.replace("(Seed Capital Retained)", "(Retained)")
        if "(Tax-Free Cash Out)" in btr:
            btr = btr.replace("(Tax-Free Cash Out)", "(Cash Out)")
            
        pdf.cell(70, 6, metric[:45], 1, 0, 'L')
        pdf.cell(60, 6, retail[:45], 1, 0, 'C')
        pdf.cell(60, 6, btr[:45], 1, 1, 'C')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 8)
    clean_footnote = strategy_footnote_text.replace("*Note: ", "Note: ").replace("*", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, clean_footnote)
    pdf.ln(5)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

st.download_button(
    label="📄 Download Enterprise Report (PDF)",
    data=create_pdf(pdf_detail_mode),
    file_name=f"Wickboldt_Capital_ProForma_{report_date.replace(' ', '_').replace(',', '')}.pdf",
    mime="application/pdf",
    type="primary",
    use_container_width=True
)
