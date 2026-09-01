import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os
from datetime import datetime
from business_plan_engine import create_business_plan_pdf
from technical_briefs_engine import create_tb1_lvp_pdf, create_tb2_shower_pdf

# Import Modular Project Engines
from config import HARDCODED_DRIVERS, NAHB_HEATED_DIVS, NAHB_STRUCT_DIVS, STRESS_SCENARIOS
from calculations import run_underwriting_engine
from pdf_engine import create_pdf, create_lender_letter_pdf
from presentation_engine import create_pptx, create_slide_pdf

# Page Configuration
st.set_page_config(page_title="Wickboldt Capital | Algorithmic Cost & Yield Optimization Engine", layout="wide")

# Initialize Session State Defaults
for key, value in HARDCODED_DRIVERS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "raw_api_data" not in st.session_state:
    st.session_state.raw_api_data = None

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
        st.slider("Auxiliary Rate (% of Heated Cost)", min_value=10.0, max_value=100.0, step=5.0, key="aux_rate_pct")
    else:
        st.slider("Auxiliary Fixed Cost ($ / SF)", min_value=15.0, max_value=90.0, step=1.0, key="aux_fixed_cost_sf")
    
    st.selectbox("Aux Structure Type", ["Carport", "Garage"], key="structure_type")
    st.number_input(f"{st.session_state.structure_type} SqFt per Unit", min_value=0, step=25, format="%d", key="struct_sqft")
    st.number_input("Front Porch SqFt", min_value=0, step=10, format="%d", key="front_porch_sqft")
    st.number_input("Back Porch SqFt", min_value=0, step=10, format="%d", key="back_porch_sqft")
    st.number_input("Storage Room SqFt", min_value=0, step=5, format="%d", key="storage_sqft")
    st.number_input("Additional Foundation / Elevation Cost ($)", min_value=0, step=500, format="%d", key="additional_foundation_cost")

with st.sidebar.container():
    st.subheader("4. Cost Target Mode (Reverse Engineer)")
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
    st.subheader("5. Horizontal Land Development")
    st.radio("Land Basis Entry Mode", ["Flat Lump Sum per Lot", "Detailed Horizontal Infrastructure (LF Parametrics)"], key="land_entry_mode")
    
    if st.session_state.land_entry_mode == "Flat Lump Sum per Lot":
        st.number_input("Finished Lot Basis per Lot ($)", min_value=0, step=1000, format="%d", key="land_basis")
    else:
        st.number_input("Raw Land Acquisition ($ Total)", min_value=0, step=5000, key="land_raw_cost")
        st.markdown("##### Subdivision Geometry & Sizing")
        c_geom1, c_geom2 = st.columns(2)
        c_geom1.number_input("Average Lot Frontage (ft)", min_value=10.0, step=5.0, key="frontage_per_lot")
        c_geom2.number_input("Average Lot Depth (ft)", min_value=50.0, step=10.0, key="lot_depth")
        
        st.radio("Infrastructure Scope", ["Auto-Calc LF (Based on Lot Frontage)", "Manual Total LF (Infill / Custom)"], key="site_type_mode")
        if st.session_state.site_type_mode == "Auto-Calc LF (Based on Lot Frontage)":
            st.radio("Street Layout / Orientation", ["Single-Sided Street (1 Lot per LF)", "Double-Sided Street (Yields 2 Lots per LF)"], key="road_layout")
        else:
            st.number_input("Total New Street & Main Ext. Length (LF)", min_value=0.0, step=10.0, key="manual_infra_lf")

        st.markdown("##### Earthwork & Fill Dirt Calculator")
        c_fill1, c_fill2 = st.columns(2)
        c_fill1.number_input("Lot Fill Depth (Inches)", min_value=0, max_value=48, step=6, key="lot_fill_inches")
        c_fill2.number_input("Road Fill Depth (Inches)", min_value=0, max_value=48, step=5, key="road_fill_inches")
        c_fill3, c_fill4 = st.columns(2)
        c_fill3.number_input("Fill Cost ($/CY Compacted)", min_value=0.0, step=1.0, key="fill_cost_cy")
        c_fill4.number_input("Base Clear/Grub ($/Lot)", min_value=0.0, step=500.0, key="clearing_per_lot")

        st.markdown("##### Roadway & Trenching Rates ($ / LF)")
        st.number_input("Road Width (Feet)", min_value=10.0, step=2.0, key="road_width")
        c_pave1, c_pave2 = st.columns(2)
        c_pave1.selectbox("Paving Material", ["Asphalt", "Concrete"], key="paving_type")
        c_pave2.number_input("Paving Rate ($/LF)", min_value=0.0, step=5.0, key="paving_cost_lf")
        c_drain1, c_drain2 = st.columns(2)
        c_drain1.selectbox("Street Drainage", ["Curb & Catch Basins", "Open Ditch / Swale"], key="drainage_type")
        c_drain2.number_input("Drainage Rate ($/LF)", min_value=0.0, step=5.0, key="drainage_cost_lf")
        c_ut1, c_ut2 = st.columns(2)
        c_ut1.number_input("Water Main Ext. ($/LF)", min_value=0.0, step=2.5, key="water_main_lf")
        c_ut2.number_input("Sewer Main Ext. ($/LF)", min_value=0.0, step=2.5, key="sewer_main_lf")
        c_ut3, c_ut4 = st.columns(2)
        c_ut3.number_input("Elec/Comm Trench ($/LF)", min_value=0.0, step=2.5, key="electric_main_lf")
        c_ut4.number_input("Gas Main Ext. ($/LF)", min_value=0.0, step=2.5, key="gas_main_lf")

        st.markdown("##### Site-Wide Amenities ($ Total)")
        st.number_input("Stormwater Detention Pond ($ Total)", min_value=0.0, step=2500.0, key="detention_pond")
        st.number_input("Street Lights, Signage & Landscaping ($ Total)", min_value=0.0, step=1000.0, key="site_amenities")

with st.sidebar.container():
    st.subheader("6. Soft Costs, Permitting & GC Fees")
    st.slider("Permits, Fees, & Insurance (% of Direct)", min_value=0.0, max_value=15.0, step=0.5, key="indirect_permits_pct")
    st.slider("Temporary Site Facilities (% of Direct)", min_value=0.0, max_value=15.0, step=0.5, key="indirect_temp_facilities_pct")
    st.slider("Construction Contingency (% of Direct)", min_value=0.0, max_value=10.0, step=0.5, key="contingency_pct")
    
    st.markdown("##### On-Lot Utility Hookups & Tap Fees ($ per Door)")
    st.number_input("Water Meter & Tap Fee", min_value=0.0, step=100.0, key="water_tap_fee")
    st.number_input("Sewer Tie-in Fee", min_value=0.0, step=100.0, key="sewer_tie_in")
    st.number_input("Electric Meter & Service Drop", min_value=0.0, step=100.0, key="electric_drop")
    st.number_input("Gas Service Lateral", min_value=0.0, step=100.0, key="gas_lateral")
    st.number_input("Municipal Impact Fees", min_value=0.0, step=250.0, key="impact_fees")

    st.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"], key="gc_fee_mode")
    if st.session_state.gc_fee_mode == "Percentage of Hard Costs (%)":
        st.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, step=0.5, key="gc_fee_pct")
    else:
        st.number_input("Total Consolidated GC Fee ($)", min_value=0, step=1000, format="%d", key="custom_gc_fee")

with st.sidebar.container():
    st.subheader("7. Construction Loan Terms")
    st.slider("Construction / Bank LTC (%)", min_value=60.0, max_value=100.0, step=5.0, key="const_ltv_pct")
    st.slider("Construction Duration (Months)", min_value=3, max_value=18, step=1, key="build_months")
    st.slider("Construction Loan Rate (%)", min_value=4.0, max_value=14.0, step=0.5, key="const_rate_pct")
    
    st.markdown("##### Lender Information")
    st.text_input("Construction Bank Name", key="const_bank_name")
    st.text_input("Contact Person", key="const_bank_contact")
    
    st.markdown("##### Closing Costs")
    st.radio("Closing Fee Entry Mode", ["Flat Lump Sum", "Detailed Enterprise Breakout"], key="const_closing_mode")
    if st.session_state.const_closing_mode == "Flat Lump Sum":
        st.number_input("Const Loan Closing Fee ($ total)", min_value=0, step=500, format="%d", key="const_closing_fee")
    else:
        with st.expander("💼 Detailed Closing Costs", expanded=True):
            st.number_input("Origination / Lender Fee ($)", min_value=0.0, step=250.0, key="const_origination_fee")
            st.number_input("Appraisal & Feasibility ($)", min_value=0.0, step=100.0, key="const_appraisal_fee")
            st.number_input("Title, Escrow & Insurance ($)", min_value=0.0, step=100.0, key="const_title_fee")
            st.number_input("Survey & Environmental ($)", min_value=0.0, step=100.0, key="const_survey_fee")
            st.number_input("Legal & Doc Prep ($)", min_value=0.0, step=100.0, key="const_legal_fee")
            st.number_input("Recording & Misc ($)", min_value=0.0, step=50.0, key="const_misc_closing_fee")

with st.sidebar.container():
    st.subheader("8. Const. Lender Limits")
    st.number_input("Bank Underwriting Rent ($)", min_value=0, step=50, format="%d", key="const_bank_rent")
    st.slider("Bank Underwriting LTV (%)", min_value=50.0, max_value=100.0, step=5.0, key="const_bank_ltv_pct")
    st.radio("Bank Valuation Method", ["Gross Rent Multiplier (GRM)", "DSCR Stress Test"], key="const_bank_val_mode")
    
    if st.session_state.const_bank_val_mode == "Gross Rent Multiplier (GRM)":
        st.number_input("Bank Underwriting GRM", min_value=4.0, max_value=25.0, step=0.1, key="const_bank_grm")
    else:
        st.slider("Bank Underwriting Vacancy (%)", min_value=0.0, max_value=15.0, step=1.0, key="const_bank_vac_pct")
        st.slider("Bank Underwriting OpEx (%)", min_value=15.0, max_value=50.0, step=1.0, key="const_bank_opex_pct")
        st.number_input("Bank Target DSCR", min_value=1.0, max_value=1.5, step=0.05, key="const_bank_dscr")
        st.slider("Bank Qualifying Rate (%)", min_value=4.0, max_value=14.0, step=0.25, key="const_bank_qual_rate_pct")
        st.selectbox("Bank Amortization (Years)", [15, 20, 25, 30], key="const_bank_amort_yrs")

with st.sidebar.container():
    st.subheader("9. Operating Pro Forma (DSCR)")
    st.number_input("Gross Monthly Rental Income per Unit ($)", min_value=0, step=50, format="%d", key="gross_monthly_rent")
    st.number_input("Target Lender DSCR Rate", min_value=1.0, max_value=1.5, step=0.05, key="target_dscr_rate")
    st.number_input("Min. Acceptable Cash Flow / Door ($)", min_value=0.0, max_value=1000.0, step=25.0, key="target_min_cashflow_per_door")
    st.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, step=1.0, key="vacancy_rate_pct")
    st.slider("Property Management Fee (% of EGI)", min_value=0.0, max_value=15.0, step=0.5, key="mgmt_fee_pct")
    
    st.radio("Other OpEx Entry Mode", ["Percentage of EGI (%)", "Itemized Monthly Costs ($ per door)"], key="opex_entry_mode")
    if st.session_state.opex_entry_mode == "Percentage of EGI (%)":
        st.slider("Other Operating Expenses (OpEx) Rate of EGI (%)", min_value=5.0, max_value=50.0, step=1.0, key="opex_rate_pct")
    else:
        with st.expander("📝 Itemized Other OpEx (Per Door / Month)", expanded=True):
            st.number_input("Property Taxes ($/mo)", min_value=0.0, step=10.0, key="opex_taxes_mo")
            st.number_input("Hazard/Wind Insurance ($/mo)", min_value=0.0, step=10.0, key="opex_ins_mo")
            st.number_input("Flood Insurance ($/mo)", min_value=0.0, step=10.0, key="opex_flood_mo")
            st.number_input("Lawn Maintenance ($/mo)", min_value=0.0, step=10.0, key="opex_lawn_mo")
            st.number_input("Turnover & Maintenance ($/mo)", min_value=0.0, step=10.0, key="opex_maint_mo")
            st.number_input("HOA / Misc ($/mo)", min_value=0.0, step=10.0, key="opex_misc_mo")
            
    st.slider("Marginal Tax Rate (%) for Depreciation Benefit", min_value=10.0, max_value=50.0, step=1.0, key="income_tax_rate_pct")
    st.slider("Annual Asset Appreciation (%)", min_value=0.0, max_value=10.0, step=0.5, key="appreciation_rate_pct")

with st.sidebar.container():
    st.subheader("10. Takeout Appraisal Methodology")
    st.radio("Valuation Mode", [
        "Sales Comp (Price/SF)", 
        "Income Approach (GRM)", 
        "Income Approach (DSCR Loan Sizing)",
        "Conservative (Lesser of GRM or DSCR)"
    ], key="appraisal_mode")
    
    if st.session_state.appraisal_mode in ["Income Approach (GRM)", "Conservative (Lesser of GRM or DSCR)"]:
        st.number_input("Gross Rent Multiplier (GRM)", min_value=4.0, max_value=25.0, step=0.1, key="target_grm")
        
    if st.session_state.appraisal_mode == "Income Approach (DSCR Loan Sizing)":
        st.info("ARV is automatically derived from your Operating (NOI) and Refi Loan terms to exactly meet your Target DSCR and LTV constraints.")
    elif st.session_state.appraisal_mode == "Conservative (Lesser of GRM or DSCR)":
        st.info("ARV evaluates both the GRM and the DSCR max loan limit, automatically defaulting to whichever yields the lower valuation.")

with st.sidebar.container():
    st.subheader("11. Takeout Refinance Terms")
    st.slider("Refinance LTV (%)", min_value=60.0, max_value=85.0, step=5.0, key="refi_ltv_pct")
    st.selectbox("Amortization Term (Years)", [15, 20, 25, 30], key="refi_term_years")
    st.slider("Base Refi Interest Rate (%)", min_value=4.0, max_value=10.0, step=0.25, key="base_refi_rate_pct")
    
    st.markdown("##### Lender Information")
    st.text_input("Refinance Bank Name", key="refi_bank_name")
    st.text_input("Contact Person", key="refi_bank_contact")
    
    st.number_input("Refinance Closing Fee ($ total)", min_value=0, step=250, format="%d", key="refi_closing_fee")
    st.checkbox("Apply Interest Rate Buydown Points?", key="apply_buydown")
    if st.session_state.apply_buydown:
        st.number_input("Discount Points", min_value=0.0, max_value=10.0, step=0.25, format="%.2f", key="buydown_pts")
        net_rate = max(0.01, (st.session_state.base_refi_rate_pct / 100.0) - (st.session_state.buydown_pts * 0.0025))
        st.markdown(f"📉 **Buydown Net Rate:** `{net_rate*100:.3f}%`")

# ==========================================
# --- MASTER ENGINE CALCULATION EXECUTION ---
# ==========================================
calc = run_underwriting_engine(st.session_state, STRESS_SCENARIOS)

# ==========================================
# --- PAGE HEADER ---
# ==========================================
try:
    st.image("Gemini_Generated_Image_.png", width=450)
except Exception:
    pass
st.title("Algorithmic Cost & Yield Optimization Engine")
st.divider()

# --- PROJECT & BORROWER INFO ---
st.markdown("### 📋 Project & Borrower Information")

with st.expander("📍 Project Details", expanded=True):
    top_col1, top_col2, top_col3 = st.columns([2, 2, 1])
    project_name = top_col1.text_input("Project Title", placeholder="e.g. Phase 1 - 24-Lot Build-to-Rent")
    project_address = top_col2.text_input("Project Address", placeholder="e.g. Rogers Moore Parkway, Hammond, LA")
    report_date = datetime.now().strftime("%B %d, %Y")

    sub_col1, sub_col2, sub_col3 = st.columns([1, 1, 2])
    project_beds = sub_col1.number_input("Beds per Unit", min_value=1, value=3, step=1)
    project_baths = sub_col2.number_input("Baths per Unit", min_value=1.0, value=2.0, step=0.5)

with st.expander("👤 Borrower Details", expanded=True):
    b_col1, b_col2 = st.columns(2)
    borrower_name = b_col1.text_input("Borrower Name", value=st.session_state.get("borrower_name", "Stephen Wickboldt Jr."))
    borrower_company = b_col2.text_input("Company/Entity", value=st.session_state.get("borrower_company", "Wickboldt Capital"))
    
    b_col3, b_col4, b_col5 = st.columns(3)
    borrower_address = b_col3.text_input("Mailing Address", value=st.session_state.get("borrower_address", "Prairieville, LA"))
    borrower_phone = b_col4.text_input("Phone Number", value=st.session_state.get("borrower_phone", "(555) 555-5555"))
    borrower_email = b_col5.text_input("Email Address", value=st.session_state.get("borrower_email", "stephen@wickboldtcapital.com"))

# --- DYNAMIC EXECUTIVE SUMMARY ---
address_display = project_address if project_address else "[Project Address]"
capital_recovery_text = "nearly 100% capital recovery" if -5000 <= calc['cash_surplus'] <= 5000 else (f"a complete capital recovery with a ${calc['cash_surplus']:,.0f} surplus" if calc['cash_surplus'] > 5000 else f"a capital recovery requiring ${-calc['cash_surplus']:,.0f} in retained seed capital")

executive_summary_text = (
    f"**Executive Summary:**\n"
    f"This technical brief outlines the pro forma and operational mechanics for a {calc['units']}-unit Build-to-Rent (BTR) "
    f"single-family residential project located at {address_display}. Utilizing a {calc['sqft']:,.0f} SF heated footprint "
    f"with a {calc['struct_sqft']:,.0f} SF integrated {st.session_state.structure_type.lower()}, the model reverse-engineers "
    f"national production builder economics to establish a target appraisal value (ARV) of ${calc['arv_per_unit']:,.0f} per home. "
    f"By deploying {borrower_company} as the managing general contractor, the project successfully captures active "
    f"construction management revenue while executing a commercial takeout refinance.\n\n"
    f"With a {calc['build_months']}-month construction timeline factored into carrying costs, this structure achieves "
    f"{capital_recovery_text}, a compliant {calc['actual_dscr']:.2f}x DSCR generating ${calc['monthly_cash_flow_per_door']:,.0f}/month "
    f"in net passive cash flow per door, and scalable wealth creation totaling ${calc['day1_wealth']:,.0f} across the "
    f"{calc['units']}-unit build program."
)
st.info(executive_summary_text.replace("$", r"\$"))
st.divider()

# ==========================================
# --- 1. POPULATE EXECUTIVE METRICS DASHBOARD ---
# ==========================================
st.markdown("### 1. Project Capital & Valuation Metrics")
col1, col2, col3, col4 = st.columns(4)

refi_vs_basis = calc['loan_total'] - calc['total_project_basis']
col1.metric("Takeout Loan Proceeds", f"${calc['loan_total']:,.0f}", f"{refi_vs_basis:+,.0f} vs Project Basis", delta_color="normal")
col2.metric("Day-1 Seed Capital", f"${calc['seed_capital']:,.0f}" if calc['seed_capital'] > 0 else "$0", "-Requires Cash Reserves" if calc['seed_capital'] > 0 else "Fully Funded", delta_color="normal")
col3.metric("Under-Roof Blended Cost", f"${calc['blended_cost_per_sf']:.2f} / SF", f"{calc['total_under_roof_sqft']:,} Total SF Under Roof")
col4.metric("Tax-Free Cash Surplus" if calc['cash_surplus'] >= 0 else "Trapped Seed Capital", f"${calc['cash_surplus']:,.0f}", "Capital Recovered" if calc['cash_surplus'] >= 0 else "Loss at Closing", delta_color="normal" if calc['cash_surplus'] >= 0 else "inverse")

st.markdown("### 🏢 Operating & DSCR Metrics")
op1, op2, op3, op4 = st.columns(4)
cf_pass = calc['monthly_cash_flow_per_door'] >= calc['target_min_cashflow_per_door']
arv_label = "Derived Unit ARV (Price/SF)" if calc['appraisal_mode'] == "Sales Comp (Price/SF)" else "Derived Unit ARV"
op1.metric(arv_label, f"${calc['arv_per_unit']:,.0f}", f"${calc['total_arv']:,.0f} Total ARV")
op2.metric("Actual DSCR Rate", f"{calc['actual_dscr']:.2f}x", f"Target: {calc['target_dscr_rate']:.2f}x", delta_color="normal" if calc['actual_dscr'] >= calc['target_dscr_rate'] else "inverse")
op3.metric("Monthly Cash Flow", f"${calc['monthly_cash_flow']:,.0f} /mo", f"${calc['monthly_cash_flow']*12:,.0f} Annual", delta_color="normal" if cf_pass else "inverse")
op4.metric("Monthly P&I Payment", f"${calc['total_monthly_pi']:,.0f} /mo", f"{calc['refi_term_years']}Yr @ {calc['net_refi_rate']*100:.3f}%")

st.markdown("### 🚦 Go/No-Go Investment Decision Dashboard")
dscr_pass = calc['actual_dscr'] >= calc['target_dscr_rate']
cash_pass = calc['cash_surplus'] >= 0
dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
dash_col1.metric("DSCR Underwriting Status", "🟢 GREEN LIGHT" if dscr_pass else "🔴 RED LIGHT", f"Actual: {calc['actual_dscr']:.2f}x (Target: {calc['target_dscr_rate']:.2f}x)", delta_color="normal" if dscr_pass else "inverse")
dash_col2.metric("Cash Flow Status", "🟢 GREEN LIGHT" if cf_pass else "🔴 RED LIGHT", f"Actual: ${calc['monthly_cash_flow_per_door']:,.0f}/door (Target: ${calc['target_min_cashflow_per_door']:,.0f})", delta_color="normal" if cf_pass else "inverse")
dash_col3.metric("Capital Recovery Status", "🟢 GREEN LIGHT" if cash_pass else "🔴 RED LIGHT", f"${calc['cash_surplus']:,.0f} at Refi Close", delta_color="normal" if cash_pass else "inverse")
dash_col4.metric("Day-1 Wealth Creation", f"${calc['day1_wealth']:,.0f}", f"${calc['day1_wealth']/calc['units']:,.0f} per door", delta_color="normal")
st.divider()

# ==========================================
# --- 2. COMP AUDIT DASHBOARD ---
# ==========================================
st.markdown("### 2. Market Comp Valuation Audit")
comp_under_roof = calc['comp_heated_sf'] + calc['comp_aux_sqft']
comp_blended_rate = calc['comp_price'] / comp_under_roof if comp_under_roof > 0 else 0
comp_address_display = st.session_state.comp_address if st.session_state.comp_address else "Market Benchmark Comparable"

comp_summary_text = (
    f"**Comparable Valuation Analysis:**\n\n"
    f"The primary comparable (**{comp_address_display}**) sold for **${calc['comp_price']:,.0f}**, spanning **{calc['comp_heated_sf']:,.0f} SF** heated living area "
    f"and **{calc['comp_aux_sqft']:,.0f} SF** of auxiliary space (**{comp_under_roof:,.0f} SF** total under roof at **${comp_blended_rate:.2f}/SF** blended).\n\n"
    f"To prevent non-living areas from inflating shell budgets, the engine algebraically isolates space types. "
    f"This yields a true isolated heated shell rate of **${calc['isolated_heated_rate']:.2f}/SF** and an implied auxiliary rate of "
    f"**${calc['comp_aux_rate_sf']:.2f}/SF** (discounted at **{calc['aux_ratio']*100:.0f}%** of the shell rate), establishing a pristine baseline for project ARV modeling."
)
st.info(comp_summary_text.replace("$", r"\$"))

comp_viz_data = pd.DataFrame({
    "Space Type": ["Heated Living Area", "Auxiliary (Garage/Porches)"],
    "Square Footage": [calc['comp_heated_sf'], calc['comp_aux_sqft']],
    "Derived Rate ($/SF)": [calc['isolated_heated_rate'], calc['comp_aux_rate_sf']],
    "Total Value Allocation": [calc['comp_heated_sf'] * calc['isolated_heated_rate'], calc['comp_aux_value']]
})
fig_comp = px.bar(comp_viz_data, x="Total Value Allocation", y="Space Type", color="Space Type", text="Total Value Allocation", orientation='h', title=f"True Value Allocation: Distributing the ${calc['comp_price']:,.0f} Comp", color_discrete_sequence=["#1f77b4", "#7f7f7f"])
fig_comp.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', insidetextanchor='middle')
fig_comp.update_layout(showlegend=False, xaxis_title="Value ($)", yaxis_title="")
st.plotly_chart(fig_comp, use_container_width=True)

with st.expander("🧮 View Comp Math Audit & Raw API Data", expanded=False):
    st.markdown("**2.1 Raw Heated Rate (Total Price ÷ Heated SF Only)**")
    st.code(f"${calc['comp_price']:,.0f} ÷ {calc['comp_heated_sf']:,.0f} Heated SF = ${calc['raw_comp_price_sf']:.2f} / SF")
    st.markdown("**2.2 Raw Blended Rate (Total Price ÷ Total Under-Roof SF)**")
    st.code(f"${calc['comp_price']:,.0f} ÷ {comp_under_roof:,.0f} Total SF = ${comp_blended_rate:.2f} / SF (Blended)")
    if st.session_state.raw_api_data and st.session_state.get("comp_entry_mode") == "RentCast Live API Fetch":
        st.json(st.session_state.raw_api_data)
st.divider()

# ==========================================
# --- 3. HORIZONTAL LAND DEVELOPMENT ---
# ==========================================
st.markdown("### 3. Horizontal Land Development & Lot Basis")
land_equity_text = f"instantly capturing **${calc['land_equity_captured']:,.0f}** in raw land equity." if calc['land_equity_captured'] >= 0 else f"running **${-calc['land_equity_captured']:,.0f}** over the target benchmark."
horizontal_summary_text = (
    f"The reverse-engineered retail model allocates **{calc['lot_cost_pct']*100:.1f}%** of the ARV to the finished lot, establishing a "
    f"target benchmark value of **${calc['target_lot_value_per_door']:,.0f}** per door (**${calc['target_total_lot_value']:,.0f}** total for {calc['units']} units). "
    f"By self-developing the infrastructure, our actual horizontal out-of-pocket basis is **${calc['land_basis']:,.0f}** per door "
    f"(**${calc['total_land_default']:,.0f}** total), {land_equity_text}"
)
st.info(horizontal_summary_text.replace("$", r"\$"))

if calc['land_equity_captured'] >= 0:
    land_viz_data = pd.DataFrame({"Value Stack": ["Target Lot Value", "Target Lot Value"], "Component": ["Actual Cost Basis", "Captured Equity (Margin)"], "Amount ($)": [calc['total_land_default'], calc['land_equity_captured']]})
    fig_land = px.bar(land_viz_data, x="Amount ($)", y="Value Stack", color="Component", orientation='h', text="Amount ($)", title=f"Land Equity Capture (Total Market Value: ${calc['target_total_lot_value']:,.0f})", color_discrete_map={"Actual Cost Basis": "#1f77b4", "Captured Equity (Margin)": "#2ca02c"})
    fig_land.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', insidetextanchor='middle')
    fig_land.update_layout(yaxis_title="", yaxis_visible=False, height=250, legend_title_text="")
else:
    land_viz_data = pd.DataFrame({"Metric": ["Target Benchmark Value", "Actual Cost Basis (Over Budget)"], "Amount ($)": [calc['target_total_lot_value'], calc['total_land_default']]})
    fig_land = px.bar(land_viz_data, x="Amount ($)", y="Metric", color="Metric", orientation='h', text="Amount ($)", title="Cost Overrun Warning: Basis Exceeds Market Value", color_discrete_map={"Target Benchmark Value": "#7f7f7f", "Actual Cost Basis (Over Budget)": "#d62728"})
    fig_land.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
    fig_land.update_layout(showlegend=False, yaxis_title="", height=250)
st.plotly_chart(fig_land, use_container_width=True)

with st.expander("🚜 View Land Development & Infrastructure Budget", expanded=False):
    if calc['land_entry_mode'] == "Detailed Horizontal Infrastructure (LF Parametrics)":
        horizontal_data = {
            "Cost Category": ["Raw Land Acquisition", "Earthwork & Fill", "Water Main Infrastructure", "Sewer Main Infrastructure", "Electrical/Comm Trenching", "Gas Main Infrastructure", "Roadways, Paving & Flatwork", "Stormwater & Drainage", "Site Amenities, Lights & Signage", "TOTAL ACTUAL HORIZONTAL BASIS", "TARGET FINISHED LOT VALUE (BENCHMARK)", "CAPTURED LAND EQUITY"],
            "Total Project Cost": [f"${calc['land_raw_cost']:,.0f}", f"${calc['land_earthwork']:,.0f}", f"${calc['land_water_main']:,.0f}", f"${calc['land_sewer_main']:,.0f}", f"${calc['land_electric_main']:,.0f}", f"${calc['land_gas_main']:,.0f}", f"${calc['land_paving']:,.0f}", f"${calc['land_drainage'] + calc['detention_pond']:,.0f}", f"${calc['site_amenities']:,.0f}", f"${calc['total_land_default']:,.0f}", f"${calc['target_total_lot_value']:,.0f}", f"${calc['land_equity_captured']:,.0f}"],
            "Cost Per Door": [f"${calc['land_raw_cost']/calc['units']:,.0f}", f"${calc['land_earthwork']/calc['units']:,.0f}", f"${calc['land_water_main']/calc['units']:,.0f}", f"${calc['land_sewer_main']/calc['units']:,.0f}", f"${calc['land_electric_main']/calc['units']:,.0f}", f"${calc['land_gas_main']/calc['units']:,.0f}", f"${calc['land_paving']/calc['units']:,.0f}", f"${(calc['land_drainage'] + calc['detention_pond'])/calc['units']:,.0f}", f"${calc['site_amenities']/calc['units']:,.0f}", f"${calc['land_basis']:,.0f}", f"${calc['target_lot_value_per_door']:,.0f}", f"${calc['land_equity_captured']/calc['units']:,.0f}"]
        }
    else:
        horizontal_data = {
            "Cost Category": ["Total Flat Finished Lot Basis", "Target Finished Lot Value (Benchmark)", "Captured Land Equity"],
            "Total Project Cost": [f"${calc['total_land_default']:,.0f}", f"${calc['target_total_lot_value']:,.0f}", f"${calc['land_equity_captured']:,.0f}"],
            "Cost Per Door": [f"${calc['land_basis']:,.0f}", f"${calc['target_lot_value_per_door']:,.0f}", f"${calc['land_equity_captured']/calc['units']:,.0f}"]
        }
    st.dataframe(pd.DataFrame(horizontal_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 4. GRANULAR DIRECT HARD COST BUILDUP ---
# ==========================================
st.markdown("### 4. Granular Vertical Direct Hard Cost Buildup")
granular_summary_text = (
    f"Below is the itemized cost buildup per trade division required to achieve the baseline "
    f"**${calc['direct_cost_sf']:.2f}/SF (${calc['heated_hard_cost']:,.0f})** heated living area cost and the "
    f"**${calc['struct_cost_sf']:.2f}/SF (${calc['struct_total_cost']:,.0f})** {st.session_state.structure_type.lower()} cost, "
    f"yielding a blended direct hard cost of **${calc['blended_cost_per_sf']:.2f}/SF (${calc['target_direct_hard_cost']:,.0f})** under roof per unit."
)
st.info(granular_summary_text.replace("$", r"\$"))

hc_chart_placeholder = st.empty()

with st.expander("🔨 View Granular Trade Buildup & Master Roll-up", expanded=False):
    granular_mode = st.radio("Buildup Entry Mode", ["Auto-Proportional (Linked to Master Model)", "Manual Custom Entry (Bottom-Up)"], horizontal=True)
    pdf_granular_data = []

    if granular_mode == "Auto-Proportional (Linked to Master Model)":
        st.markdown(f"#### 4.1 Heated Living Area ({calc['sqft']} SF @ ${calc['direct_cost_sf']:.2f} / SF)".replace("$", r"\$"))
        h_data = {"Division / Trade Level": [], "Live Cost / SF": [], "Per Unit Cost": []}
        for name, base_val, is_header in NAHB_HEATED_DIVS:
            live_sf = calc['direct_cost_sf'] * (base_val / 100.0)
            prefix = "" if is_header else "   "
            h_data["Division / Trade Level"].append(f"{prefix}{name}")
            h_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            h_data["Per Unit Cost"].append(f"${live_sf * calc['sqft']:,.0f}")
            pdf_granular_data.append((f"{prefix}{name}", live_sf, live_sf * calc['sqft'], live_sf * calc['sqft'] * calc['units'], is_header))
        st.dataframe(pd.DataFrame(h_data), hide_index=True, use_container_width=True)
        
        st.markdown(f"#### 4.2 {st.session_state.structure_type} Auxiliary ({calc['struct_sqft']} SF @ ${calc['struct_cost_sf']:.2f} / SF)".replace("$", r"\$"))
        s_data = {"Component Level": [], "Live Cost / SF": [], "Per Unit Cost": []}
        for name, base_val, is_header in NAHB_STRUCT_DIVS:
            live_sf = calc['struct_cost_sf'] * (base_val / 35.0)
            s_data["Component Level"].append(name)
            s_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            s_data["Per Unit Cost"].append(f"${live_sf * calc['struct_sqft']:,.0f}")
        st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True)
    else:
        st.markdown(f"#### 4.1 Heated Living Area ({calc['sqft']} SF)")
        hl_heated = []
        current_header = ""
        for name, base, is_h in NAHB_HEATED_DIVS:
            if is_h:
                current_header = name
            else:
                hl_heated.append({"Category": current_header, "Division / Component": name.replace("- ", ""), "Cost / SF": calc['direct_cost_sf'] * (base/100.0)})
        df_manual = pd.DataFrame(hl_heated)
        edited_h = st.data_editor(df_manual.drop(columns=["Category"]), column_config={"Division / Component": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True)
        df_manual["Cost / SF"] = edited_h["Cost / SF"]
        
        for cat in df_manual["Category"].unique():
            cat_df = df_manual[df_manual["Category"] == cat]
            cat_sum = cat_df["Cost / SF"].sum()
            pdf_granular_data.append((cat, cat_sum, cat_sum * calc['sqft'], cat_sum * calc['sqft'] * calc['units'], True))
            for _, row in cat_df.iterrows():
                live_sf = row["Cost / SF"]
                pdf_granular_data.append((f"   - {row['Division / Component']}", live_sf, live_sf * calc['sqft'], live_sf * calc['sqft'] * calc['units'], False))

    st.markdown("#### 4.3 Auxiliary, Foundation & Outdoor Living")
    p_data = {
        "Component": ["Front Porch", "Back Porch", "Storage Room", "Addit. Foundation / Elevation", "TOTAL AUX/OUTDOOR"],
        "Area (SF)": [f"{calc['front_porch_sqft']} SF", f"{calc['back_porch_sqft']} SF", f"{calc['storage_sqft']} SF", "Site Specific", "Total"],
        "Cost / SF": [f"${calc['front_porch_cost_sf']:.2f}", f"${calc['back_porch_cost_sf']:.2f}", f"${calc['storage_cost_sf']:.2f}", "-", "-"],
        "Total Amount": [f"${calc['front_porch_cost']:,.0f}", f"${calc['back_porch_cost']:,.0f}", f"${calc['storage_cost']:,.0f}", f"${calc['additional_foundation_cost']:,.0f}", f"${calc['our_aux_cost_total']:,.0f}"]
    }
    st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)

    st.markdown("#### 4.4 Direct Hard Cost Master Roll-up")
    direct_rollup_df = pd.DataFrame({
        "Category / Major Sub-Assembly": [f"1. Heated Living Area ({calc['sqft']:,} SF)", f"2. {st.session_state.structure_type} Structure ({calc['struct_sqft']:,} SF)", f"3. Outdoor & Storage Spaces ({calc['front_porch_sqft'] + calc['back_porch_sqft'] + calc['storage_sqft']:,} SF)", "4. Site Foundation & Elevation Premium", "TOTAL DIRECT HARD COST BUDGET"],
        "Effective Rate": [f"${calc['direct_cost_sf']:.2f} / Heated SF", f"${calc['struct_cost_sf']:.2f} / SF", f"${calc['struct_cost_sf']:.2f} / SF (Avg)", "Flat Lump Sum", f"${calc['blended_cost_per_sf']:.2f} / SF Under Roof"],
        "Per Unit Cost ($)": [calc['heated_hard_cost'], calc['struct_total_cost'], calc['outdoor_aux_subtotal_unit'], calc['additional_foundation_cost'], calc['target_direct_hard_cost']],
        "Project Total ($)": [calc['heated_hard_cost'] * calc['units'], calc['struct_total_cost'] * calc['units'], calc['outdoor_aux_subtotal_unit'] * calc['units'], calc['additional_foundation_cost'] * calc['units'], calc['total_hard_cost']]
    })
    st.dataframe(direct_rollup_df.style.format({"Per Unit Cost ($)": "${:,.0f}", "Project Total ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)

viz_categories = []
viz_amounts = []
for name, live_sf, unit_cost, proj_cost, is_header in pdf_granular_data:
    if is_header:
        clean_name = name.split(". ", 1)[-1].title() if ". " in name else name.title()
        viz_categories.append(clean_name)
        viz_amounts.append(unit_cost)
viz_categories.append("Auxiliary, Porches & Foundation")
viz_amounts.append(calc['our_aux_cost_total'])

fig_hc = px.bar(pd.DataFrame({"Division": viz_categories, "Cost": viz_amounts}), x="Cost", y="Division", orientation='h', title="Vertical Direct Hard Cost Breakdown per Unit", color="Division", text="Cost")
fig_hc.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', insidetextanchor='middle')
fig_hc.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, xaxis_title="Budget Allocation ($)", yaxis_title="")
hc_chart_placeholder.plotly_chart(fig_hc, use_container_width=True)
st.divider()

# ==========================================
# --- 5. BANK STRESS TEST BREAKDOWN ---
# ==========================================
st.markdown("### 5. Construction Lender Loan Cap & Stress Test")
if calc['const_bank_val_mode'] == "DSCR Stress Test":
    st.info(f"**Construction Loan Underwriting:** The bank determines implied asset value on a **{calc['const_bank_dscr']:.2f}x DSCR stress test** (yielding **${calc['bank_stressed_value']:,.0f}**). Loan cap: **${calc['actual_const_loan']:,.0f}**.".replace("$", r"\$"))
    stress_test_data = {
        "Bank Underwriting Step": ["1. Gross Potential Rent (Bank Model)", "2. Less: Bank Vacancy & OpEx Deductions", "3. Bank Qualified Net Operating Income (NOI)", "4. Target Construction DSCR Constraint", "5. Bank Implied Asset Value", f"6. Const. Lender Loan Value ({calc['const_bank_ltv']*100:.1f}% Bank LTV)", "7. Total Capitalized Construction Basis", "8. Required Seed Capital Reserve"],
        "Value": [f"${calc['cb_gross_annual_rent']:,.0f} / yr", f"-${calc['cb_gross_annual_rent'] - calc['cb_noi']:,.0f} / yr", f"${calc['cb_noi']:,.0f} / yr", f"{calc['const_bank_dscr']:.2f}x", f"${calc['bank_stressed_value']:,.0f}", f"${calc['actual_const_loan']:,.0f}", f"${calc['total_construction_basis']:,.0f}", f"${calc['seed_capital']:,.0f}"]
    }
else:
    st.info(f"**Construction Loan Underwriting:** The bank determines implied asset value on a **{calc['const_bank_grm']:.1f}x Gross Rent Multiplier** (yielding **${calc['bank_stressed_value']:,.0f}**). Loan cap: **${calc['actual_const_loan']:,.0f}**.".replace("$", r"\$"))
    stress_test_data = {
        "Bank Underwriting Step": ["1. Gross Potential Rent (Bank Model)", "2. Bank Underwriting GRM", "3. Bank Implied Asset Value", f"4. Const. Lender Loan Value ({calc['const_bank_ltv']*100:.1f}% Bank LTV)", "5. Total Capitalized Construction Basis", "6. Required Seed Capital Reserve"],
        "Value": [f"${calc['cb_gross_annual_rent']:,.0f} / yr", f"{calc['const_bank_grm']:.1f}x", f"${calc['bank_stressed_value']:,.0f}", f"${calc['actual_const_loan']:,.0f}", f"${calc['total_construction_basis']:,.0f}", f"${calc['seed_capital']:,.0f}"]
    }

cap_viz_data = pd.DataFrame({"Metric": ["1. Total Capital Basis", "2. Max Allowed Loan", "3. Bank Appraised Value"], "Amount ($)": [calc['total_construction_basis'], calc['actual_const_loan'], calc['bank_stressed_value']], "Category": ["Basis", "Loan", "Value"]})
fig_cap = px.bar(cap_viz_data, x="Metric", y="Amount ($)", color="Category", text="Amount ($)", title="Construction Loan Sizing vs. Project Cost", color_discrete_map={"Basis": "#ff7f0e", "Loan": "#1f77b4", "Value": "#2ca02c"})
fig_cap.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
fig_cap.update_layout(showlegend=False, xaxis_title="", yaxis_title="Amount ($)", yaxis=dict(range=[0, max(calc['bank_stressed_value'], calc['total_construction_basis']) * 1.15]))
st.plotly_chart(fig_cap, use_container_width=True)

with st.expander("🏦 View Bank Stress Test Metrics", expanded=False):
    st.dataframe(pd.DataFrame(stress_test_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 6. DEVELOPER CAPITAL & LEDGER ---
# ==========================================
st.markdown("### 6. Developer Capital & Construction Ledger")
basis_breakdown = pd.DataFrame({"Category": ["Land & Horizontal", "Vertical Hard Costs", "Indirects, Cont. & Soft Costs", "Financing & Closing"], "Amount": [calc['total_land_default'], calc['total_hard_cost'], calc['total_indirect_costs'] + calc['total_vertical_soft'], calc['btr_finance_closing']]})
fig_donut = px.pie(basis_breakdown, names="Category", values="Amount", hole=0.45, title="Total Project Capital Basis Breakdown", color_discrete_sequence=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"])
fig_donut.update_traces(textposition='inside', textinfo='percent+label')
st.plotly_chart(fig_donut, use_container_width=True)

with st.expander("💰 View Capital Ledgers & Transaction Scope", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(pd.DataFrame({"Component": [f"Finished Lot Benchmark ({calc['lot_cost_pct']*100:.1f}%)", "Adjusted BTR Hard Costs", "Indirects, Cont. & GC Fee", "On-Lot Utilities & Soft Costs", "Finance, Closing & Buydown", "Built-in Developer Margin", "Total Appraised Value (ARV)"], "Amount": [f"${calc['lot_benchmark']:,.0f}", f"${calc['total_hard_cost']:,.0f}", f"${calc['total_indirect_costs']:,.0f}", f"${calc['total_vertical_soft']:,.0f}", f"${calc['btr_finance_closing']:,.0f}", f"${calc['developer_margin']:,.0f}", f"${calc['total_arv']:,.0f}"]}), hide_index=True, use_container_width=True)
    with col2:
        st.dataframe(pd.DataFrame({"Component": ["Const. Loan Closing Fees", "Carrying Interest", "Perm. Takeout Fees", f"Rate Buydown ({calc['buydown_pts']:.2f} pts)"], "Amount": [f"${calc['const_closing_fee']:,.0f}", f"${calc['carry_int_base']:,.0f}", f"${calc['refi_closing_fee']:,.0f}", f"${calc['default_buydown_cost']:,.0f}"]}), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 7. OPERATING PERFORMANCE & DSCR ---
# ==========================================
st.markdown("### 7. Operating Performance & DSCR Requirements")
operating_summary_text = (
    f"Stabilized portfolio generates **${calc['total_gross_monthly_income']:,.0f}** gross rent. "
    f"Yields **${calc['monthly_noi']:,.0f}** in monthly NOI. "
    f"At a permanent debt service of **${calc['total_monthly_pi']:,.0f}**, the asset operates at a **{calc['actual_dscr']:.2f}x DSCR**, "
    f"producing **${calc['monthly_cash_flow_per_door']:,.0f}** in net cash flow per door every month."
)
st.info(operating_summary_text.replace("$", r"\$"))

op_x = ["Gross Rent", "Vacancy", "Mgmt", "Taxes", "Insurance", "NOI", "Debt Service", "Net Cash Flow"]
op_measure = ["relative", "relative", "relative", "relative", "relative", "total", "relative", "total"]
op_text = [f"+${calc['total_gross_monthly_income']:,.0f}", f"-${calc['monthly_vacancy_loss']:,.0f}", f"-${calc['mgmt_est']:,.0f}", f"-${calc['tax_est']:,.0f}", f"-${calc['ins_est']:,.0f}", f"${calc['monthly_noi']:,.0f}", f"-${calc['total_monthly_pi']:,.0f}", f"${calc['monthly_cash_flow']:,.0f}"]
op_y = [calc['total_gross_monthly_income'], -calc['monthly_vacancy_loss'], -calc['mgmt_est'], -calc['tax_est'], -calc['ins_est'], calc['monthly_noi'], -calc['total_monthly_pi'], calc['monthly_cash_flow']]

fig_op = go.Figure(go.Waterfall(orientation="v", measure=op_measure, x=op_x, textposition="outside", text=op_text, y=op_y, decreasing={"marker": {"color": "#d62728"}}, increasing={"marker": {"color": "#2ca02c"}}, totals={"marker": {"color": "#1f77b4"}}))
fig_op.update_layout(title="Monthly Operating Cash Flow & DSCR Waterfall", showlegend=False, yaxis_title="Amount ($)")
st.plotly_chart(fig_op, use_container_width=True)

dscr_summary_data = {
    "Pro Forma Line Item": ["Gross Potential Rent (GPR)", f"(-) Vacancy Loss @ {calc['vacancy_rate']*100:.1f}%", "= Effective Gross Income (EGI)", f"(-) Property Management @ {calc['mgmt_fee_pct']*100:.1f}% of EGI", "(-) Other Operating Expenses", "= Net Operating Income (NOI)", "(-) Total Debt Service (P&I)", "= Net Cash Flow", "Actual DSCR Rate", "Target Lender DSCR", "DSCR Variance"],
    "Monthly": [f"${calc['total_gross_monthly_income']:,.2f}", f"-${calc['monthly_vacancy_loss']:,.2f}", f"${calc['annual_egi'] / 12:,.2f}", f"-${calc['monthly_mgmt_fee']:,.2f}", f"-${calc['mo_other_opex']:,.2f}", f"${calc['monthly_noi']:,.2f}", f"-${calc['total_monthly_pi']:,.2f}", f"${calc['monthly_cash_flow']:,.2f}", f"{calc['actual_dscr']:.2f}x", f"{calc['target_dscr_rate']:.2f}x", f"{calc['dscr_variance']:+.2f}x"],
    "Annual": [f"${calc['total_gross_monthly_income'] * 12:,.2f}", f"-${calc['annual_vacancy_loss']:,.2f}", f"${calc['annual_egi']:,.2f}", f"-${calc['annual_mgmt_fee']:,.2f}", f"-${calc['annual_other_opex']:,.2f}", f"${calc['annual_noi']:,.2f}", f"${calc['annual_debt_service']:,.2f}", f"${calc['monthly_cash_flow'] * 12:,.2f}", f"{calc['actual_dscr']:.2f}x", f"{calc['target_dscr_rate']:.2f}x", f"{calc['dscr_variance']:+.2f}x"]
}
with st.expander("🏢 View Stabilized Operating Pro Forma (DSCR)", expanded=False):
    st.dataframe(pd.DataFrame(dscr_summary_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 8. REFINANCE WATERFALL & WEALTH ---
# ==========================================
st.markdown("### 8. Refinance Cash Waterfall & Day-1 Wealth")
waterfall_summary_text = (
    f"The **${calc['loan_total']:,.0f}** Permanent Loan pays off the **${calc['actual_const_loan']:,.0f}** Construction phase. "
    f"After recovering **${calc['seed_capital']:,.0f}** in seed capital, the transaction yields **${calc['cash_surplus']:,.0f}** in net cash surplus."
)
st.info(waterfall_summary_text.replace("$", r"\$"))

fig_refi_waterfall = go.Figure(go.Waterfall(orientation="v", measure=["relative", "relative", "relative", "relative", "total", "relative", "total"], x=["Takeout Loan", "Const. Payoff", "Refi Fees", "Buydown Pts", "Net at Close", "Seed Repayment", "Final Surplus"], textposition="outside", text=[f"+${calc['loan_total']:,.0f}", f"-${calc['actual_const_loan']:,.0f}", f"-${calc['refi_closing_fee']:,.0f}", f"-${calc['default_buydown_cost']:,.0f}", f"${calc['net_cash_at_closing']:,.0f}", f"-${calc['seed_capital']:,.0f}", f"${calc['cash_surplus']:,.0f}"], y=[calc['loan_total'], -calc['actual_const_loan'], -calc['refi_closing_fee'], -calc['default_buydown_cost'], calc['net_cash_at_closing'], -calc['seed_capital'], calc['cash_surplus']], decreasing={"marker": {"color": "#d62728"}}, increasing={"marker": {"color": "#2ca02c"}}, totals={"marker": {"color": "#1f77b4"}}))
fig_refi_waterfall.update_layout(title="Refinance Cash Waterfall", showlegend=False, yaxis_title="Amount ($)")
st.plotly_chart(fig_refi_waterfall, use_container_width=True)
st.divider()

# ==========================================
# --- 9. STRATEGY COMPARISON ---
# ==========================================
st.markdown("### 9. Strategy Comparison: Retail Sell vs. Build-to-Rent")
strategy_comparison_text = f"Models National Builder taxable exit (**${calc['retail_net_cash']:,.0f}** after tax) vs. BTR model (**${calc['cash_surplus']:,.0f}** cash surplus + **${calc['retained_equity']:,.0f}** equity retained)."
st.info(strategy_comparison_text.replace("$", r"\$"))

strat_viz_data = pd.DataFrame({"Strategy": ["1. Retail Sell Model", "1. Retail Sell Model", "2. Build-to-Rent Model", "2. Build-to-Rent Model"], "Wealth Component": ["After-Tax Net Cash", "Retained Equity", "After-Tax Net Cash", "Retained Equity"], "Amount ($)": [calc['retail_net_cash'], 0, calc['cash_surplus'], calc['retained_equity']]})
fig_strat = px.bar(strat_viz_data, x="Strategy", y="Amount ($)", color="Wealth Component", text="Amount ($)", barmode="stack", title=f"Wealth Creation Comparison (Total ARV: ${calc['total_arv']:,.0f})", color_discrete_map={"After-Tax Net Cash": "#2ca02c", "Retained Equity": "#1f77b4"})
fig_strat.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', insidetextanchor='middle')
st.plotly_chart(fig_strat, use_container_width=True)

strategy_data = {
    "Financial Metric": ["Land Basis", "Direct Hard Costs", "Total Construction Cost", "On-Lot Utilities & Soft Costs", "Sales & Transaction Closing Costs", "Total Capital Invested", "Gross Revenue / Permanent Loan Proceeds", "Estimated Capital Gains Taxes (30%)", "Net Cash Event at Closing", "Asset Retained on Balance Sheet?", "Ongoing Monthly Cash Flow"],
    "National Builder (Retail Sell)": [f"${calc['total_land_default']:,.0f}", f"${calc['total_hard_cost']:,.0f}", f"${calc['total_const']:,.0f}", f"${calc['total_vertical_soft']:,.0f}", f"${calc['retail_sales_costs']:,.0f}", f"${calc['retail_total_invested']:,.0f}", f"${calc['total_arv']:,.0f}", f"-${calc['retail_taxes']:,.0f}", f"+${calc['retail_net_cash']:,.0f}", "No", "$0"],
    "Build-to-Rent (DSCR Takeout)": [f"${calc['total_land_default']:,.0f}", f"${calc['total_hard_cost']:,.0f}", f"${calc['total_const']:,.0f}", f"${calc['total_vertical_soft']:,.0f}", f"${calc['btr_finance_closing']:,.0f}", f"${calc['total_project_basis']:,.0f}", f"${calc['loan_total']:,.0f}", "$0", f"${calc['cash_surplus']:,.0f}", "Yes", f"+${calc['monthly_cash_flow_per_door']:,.0f} / mo / door"]
}
strategy_footnote_text = f"BTR Model captures ${calc['default_gc_fee']:,.0f} in GC fee revenue with ${calc['day1_wealth']:,.0f} total Day-1 Created Value."
with st.expander("⚖️ View Financial Strategy Comparison Matrix", expanded=False):
    st.dataframe(pd.DataFrame(strategy_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 10. MULTI-UNIT SCALING ---
# ==========================================
st.markdown("### 10. Multi-Unit Phase & Annual Program Analysis")
scaling_intro = f"Scaling production unlocks substantial management savings, optimizing fees down to **$20,000 per 3-house phase** (saving **${calc['savings_per_door']:,.0f}** per home)."
st.info(scaling_intro.replace("$", r"\$"))

scaling_viz_data = pd.DataFrame({"Scale": ["1-House Baseline", "3-House Phase", "6-House Annual"], "Total Capital Invested per Door": [calc['cap_1'], calc['cap_3'] / 3, calc['cap_6'] / 6], "GC Fee per Door": [calc['unit_gc_baseline'], calc['opt_gc_3'] / 3, calc['opt_gc_6'] / 6], "Wealth Created per Door": [calc['wealth_1'], calc['wealth_3'] / 3, calc['wealth_6'] / 6]})
st.plotly_chart(px.bar(scaling_viz_data.melt(id_vars="Scale", var_name="Metric", value_name="Amount ($)"), x="Scale", y="Amount ($)", color="Metric", barmode="group", title="Economies of Scale: Per-Door Financial Impact", text_auto='.2s'), use_container_width=True)

scaling_data = {
    "Portfolio Metric": ["Total Units Built", f"Land Basis (${calc['unit_land']:,.0f} / lot)", f"Adjusted Hard Costs (${calc['unit_hard']:,.0f} / house)", "Optimized Management Fees", "On-Lot Utilities & Soft Costs", "Financing & Closing", "Total Program Capital Invested", "Permanent Commercial Loan Proceeds", "Net Program Cash Surplus at Close", "Total Retained Asset Equity", "Total Day-1 Wealth Created"],
    "Single-House Baseline": ["1 Unit", f"${calc['unit_land']:,.0f}", f"${calc['unit_hard']:,.0f}", f"${calc['unit_gc_baseline']:,.0f}", f"${calc['unit_soft']:,.0f}", f"${calc['unit_fin']:,.0f}", f"${calc['cap_1']:,.0f}", f"${calc['loan_1']:,.0f}", f"${calc['surplus_1']:,.0f}", f"${calc['eq_1']:,.0f}", f"${calc['wealth_1']:,.0f}"],
    "3-House Simultaneous Phase": ["3 Units", f"${calc['unit_land'] * 3:,.0f}", f"${calc['unit_hard'] * 3:,.0f}", f"${calc['opt_gc_3']:,.0f}", f"${calc['unit_soft'] * 3:,.0f}", f"${calc['unit_fin'] * 3:,.0f}", f"${calc['cap_3']:,.0f}", f"${calc['loan_3']:,.0f}", f"${calc['surplus_3']:,.0f}", f"${calc['eq_3']:,.0f}", f"${calc['wealth_3']:,.0f}"],
    "6-House Annual Build (Year 1)": ["6 Units", f"${calc['unit_land'] * 6:,.0f}", f"${calc['unit_hard'] * 6:,.0f}", f"${calc['opt_gc_6']:,.0f}", f"${calc['unit_soft'] * 6:,.0f}", f"${calc['unit_fin'] * 6:,.0f}", f"${calc['cap_6']:,.0f}", f"${calc['loan_6']:,.0f}", f"${calc['surplus_6']:,.0f}", f"${calc['eq_6']:,.0f}", f"${calc['wealth_6']:,.0f}"]
}
scaling_takeaway = f"Executing a 6-house annual program yields ${calc['opt_gc_6']:,.0f} in active GC fees and generates ${calc['monthly_cf_6']:,.0f}/mo in cash flow."
with st.expander("📈 View Multi-Unit Scaling Table", expanded=False):
    st.dataframe(pd.DataFrame(scaling_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 10.5 THE EXIT & TWO-POCKET STRATEGY ---
# ==========================================
st.markdown("### 10.5. The Exit: Refinance & The \"Two-Pocket\" Cash Flow Strategy")

# Extract dynamic 6-unit program variables
prog_units = 6
prog_loan = calc['loan_6']
prog_basis = calc['cap_6']
prog_land = calc['unit_land'] * prog_units
prog_surplus = calc['surplus_6']
prog_gc = calc['opt_gc_6']
prog_eq = calc['eq_6']
prog_wealth = calc['wealth_6']
arv_unit = calc['arv_per_unit']
ltv_pct = calc['refi_ltv'] * 100
unencumbered_pct = 100 - ltv_pct

exit_intro = (
    f"By executing an annual build program of {prog_units} houses across two optimized 3-house phases, you successfully extract active cash during construction while the **{ltv_pct:.0f}% LTV** "
    f"commercial takeout loans fully recover the holding entity's locked capital with substantial surplus."
)
st.info(exit_intro)

col_exit1, col_exit2 = st.columns([1, 1])

with col_exit1:
    st.markdown(f"#### Takeout Capital Distribution Ledger ({prog_units}-House Annual Program)")
    st.markdown(f"- **${prog_basis:,.0f} Basis** clears construction, soft costs, financing, and takeout closing fees across all {prog_units} homes.")
    st.markdown(f"- **${prog_land:,.0f}** is repaid directly to the developer, fully returning 100% of the land seed capital across the portfolio.")
    
    if prog_surplus >= 0:
        st.markdown(f"- **${prog_surplus:,.0f}** is distributed as tax-free cash surplus (${prog_loan:,.0f} total loan proceeds - ${prog_basis:,.0f} total basis).")
    else:
        st.markdown(f"- **${-prog_surplus:,.0f}** remains as trapped seed capital (${prog_loan:,.0f} total loan proceeds - ${prog_basis:,.0f} total basis).")
    
    st.markdown("#### The \"Effectively Infinite\" Return")
    if prog_surplus >= 0:
        st.write(f"In commercial real estate, Cash-on-Cash Return is mathematically defined as: Annual Net Cash Flow divided by Total Developer Capital Trapped in the Asset. Because 100% of the seed capital is returned plus an extra **${prog_surplus:,.0f}** in surplus across the year, the locked capital is $0.00, resulting in an **infinite return**.")
    else:
        st.write(f"In commercial real estate, Cash-on-Cash Return is mathematically defined as: Annual Net Cash Flow divided by Total Developer Capital Trapped in the Asset. With **${-prog_surplus:,.0f}** remaining as trapped capital, the portfolio yields a **{(calc['monthly_cf_6']*12) / (-prog_surplus) * 100 :.1f}%** cash-on-cash return.")

with col_exit2:
    # Dynamic Waterfall Chart for the Pockets of Wealth
    fig_wealth_pockets = go.Figure(go.Waterfall(
        name="Wealth Creation",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Pocket 1: GC Fees", "Pocket 2: Cash Surplus", "Pocket 3: Retained Equity", "Total Day-1 Wealth"],
        textposition="outside",
        text=[f"${prog_gc:,.0f}", f"${prog_surplus:,.0f}", f"${prog_eq:,.0f}", f"${prog_wealth:,.0f}"],
        y=[prog_gc, prog_surplus, prog_eq, prog_wealth],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#d62728"}},
        increasing={"marker": {"color": "#2ca02c"}},
        totals={"marker": {"color": "#1f77b4"}}
    ))
    fig_wealth_pockets.update_layout(
        title=f"Total Day-1 Wealth Creation ({prog_units}-House Program)", 
        showlegend=False, 
        yaxis_title="Amount ($)",
        margin=dict(t=40, b=20, l=20, r=20)
    )
    st.plotly_chart(fig_wealth_pockets, use_container_width=True)

# Detailed Data Table
wealth_pocket_data = {
    "Wealth Component": [
        "Pocket 1: GC Management Fees Earned During Build",
        "Pocket 2: Tax-Free Cash-Out Surplus at Refinance Close",
        f"Pocket 3: Retained Asset Equity ({unencumbered_pct:.0f}% unencumbered equity of ${arv_unit:,.0f} ARV)",
        "Total Day-1 Created Value"
    ],
    "Per House": [
        f"${prog_gc/prog_units:,.0f}",
        f"${prog_surplus/prog_units:,.0f}",
        f"${prog_eq/prog_units:,.0f}",
        f"${prog_wealth/prog_units:,.0f}"
    ],
    f"Program Total ({prog_units} Doors)": [
        f"${prog_gc:,.0f}",
        f"${prog_surplus:,.0f}",
        f"${prog_eq:,.0f}",
        f"${prog_wealth:,.0f}"
    ]
}

with st.expander("📊 View Detailed Wealth Creation Matrix", expanded=True):
    st.dataframe(pd.DataFrame(wealth_pocket_data), hide_index=True, use_container_width=True)

st.divider()

# ==========================================
# --- 11. S-CURVE DRAW SCHEDULE ---
# ==========================================
st.markdown("### 11. Enterprise S-Curve Draw Schedule & Actual Carry Interest")
scurve_summary = f"Deploying development budget across a trigonometric S-Curve locks carry interest at **${calc['carry_int_base']:,.0f}** over {calc['build_months']} months."
st.info(scurve_summary.replace("$", r"\$"))

fig_scurve = px.bar(calc['df_schedule'], x="Month", y="Monthly Draw ($)", title="Monthly Construction Drawdown (S-Curve)", text_auto='.2s', color_discrete_sequence=["#1f77b4"])
fig_scurve.update_traces(textposition='outside')
st.plotly_chart(fig_scurve, use_container_width=True)

with st.expander("📉 View S-Curve Schedule Table", expanded=False):
    st.dataframe(calc['df_schedule'].style.format({"Monthly Draw ($)": "${:,.0f}", "Capitalized Interest ($)": "${:,.0f}", "Total Drawn Balance ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 12. SENSITIVITY ANALYSIS (STRESS TEST) ---
# ==========================================
st.markdown("### 12. Sensitivity Analysis (Stress Testing)")
stress_test_summary = f"Stress-tests active pro forma against market volatility, proving DSCR safety (**> {calc['target_dscr_rate']:.2f}x**)."
st.info(stress_test_summary.replace("$", r"\$"))

df_stress_plot = calc['df_stress'].copy()
df_stress_plot['DSCR Color'] = df_stress_plot['Raw DSCR'].apply(lambda x: '#2ca02c' if x >= calc['target_dscr_rate'] else '#d62728')
df_stress_plot['Short Name'] = df_stress_plot['Stress Scenario'].apply(lambda x: x.split(". ")[1] if ". " in x else x)

fig_stress_dscr = go.Figure(go.Bar(x=df_stress_plot['Short Name'], y=df_stress_plot['Raw DSCR'], marker_color=df_stress_plot['DSCR Color'], text=df_stress_plot['Raw DSCR'].apply(lambda x: f"{x:.2f}x"), textposition='auto'))
fig_stress_dscr.add_hline(y=calc['target_dscr_rate'], line_dash="dash", line_color="black", annotation_text=f"Min {calc['target_dscr_rate']:.2f}x")
fig_stress_dscr.update_layout(title="DSCR Safety Under Duress", yaxis_title="DSCR Rate", showlegend=False)
st.plotly_chart(fig_stress_dscr, use_container_width=True)

with st.expander("🌩️ View Lender Risk Mitigation Matrix", expanded=False):
    st.dataframe(calc['df_stress'].drop(columns=["Raw DSCR", "Raw Surplus"]), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 13. OPEX SENSITIVITY ---
# ==========================================
st.markdown("### 13. Operating Expense (OpEx) Sensitivity")
opex_sens_summary = f"Evaluates fluctuations in OpEx against baseline **${calc['total_gross_monthly_income']:,.0f}** gross rent and fixed **${calc['total_monthly_pi']:,.0f}** monthly P&I."
st.info(opex_sens_summary.replace("$", r"\$"))

fig_opex = go.Figure(go.Bar(x=calc['opex_labels'], y=calc['raw_opex_nois'], marker_color=calc['opex_colors'], text=[f"NOI: ${n:,.0f}<br>{d:.2f}x DSCR" for n, d in zip(calc['raw_opex_nois'], calc['raw_opex_dscrs'])], textposition='auto'))
fig_opex.add_hline(y=calc['total_monthly_pi'], line_dash="dash", line_color="black", annotation_text=f"Breakeven (P&I): ${calc['total_monthly_pi']:,.0f}", annotation_position="bottom right")
target_noi = calc['total_monthly_pi'] * calc['target_dscr_rate']
fig_opex.add_hline(y=target_noi, line_dash="dot", line_color="#1f77b4", annotation_text=f"Bank Target NOI: ${target_noi:,.0f}", annotation_position="top right")
fig_opex.update_layout(title="Net Operating Income vs. Debt Service Requirements", yaxis_title="Monthly Amount ($)", showlegend=False, yaxis=dict(range=[0, max(max(calc['raw_opex_nois']), target_noi) * 1.15]))
st.plotly_chart(fig_opex, use_container_width=True)

with st.expander("📊 View Detailed OpEx Stress Matrix", expanded=False):
    st.dataframe(calc['df_opex_sens'], hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 14. GROSS RENT SENSITIVITY MATRIX ---
# ==========================================
st.markdown("### 14. Gross Rent Sensitivity Matrix")
rent_sens_summary = f"Models project cash flows and loan coverage across market rents from **${calc['gross_monthly_rent'] - 100:,.0f}** to **${calc['gross_monthly_rent'] + 200:,.0f}**."
st.info(rent_sens_summary.replace("$", r"\$"))

fig_rent = go.Figure(go.Bar(x=calc['raw_rents'], y=calc['raw_rent_cfs'], marker_color=calc['rent_colors'], text=[f"CF: ${cf:,.0f}<br>{d:.2f}x DSCR" for cf, d in zip(calc['raw_rent_cfs'], calc['raw_rent_dscrs'])], textposition='auto'))
fig_rent.add_hline(y=calc['target_min_cashflow_per_door'], line_dash="dash", line_color="black", annotation_text=f"Target Min CF: ${calc['target_min_cashflow_per_door']:,.0f}", annotation_position="bottom right")
fig_rent.update_layout(title="Net Monthly Cash Flow & DSCR Across Rent Scenarios", yaxis_title="Net Cash Flow per Door ($)", showlegend=False)
st.plotly_chart(fig_rent, use_container_width=True)

with st.expander("📊 View Detailed Rent Sensitivity Matrix", expanded=False):
    st.dataframe(calc['df_rent_sens'], hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 15. REVERSE-ENGINEERING BREAKDOWN ---
# ==========================================
if calc['cost_calc_mode'] in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"]:
    st.markdown("### 15. Retail Comp & Appraisal Reverse-Engineering Breakdown")
    rev_eng_summary = f"Estimated project ARV of **${calc['reference_price']:,.0f}** reverse-engineers direct hard costs from margins and soft costs."
    st.info(rev_eng_summary.replace("$", r"\$"))
    
    fig_rev = go.Figure(go.Waterfall(orientation="v", measure=["relative", "relative", "relative", "relative", "relative", "relative", "total", "relative", "total", "relative", "total"], x=["Target ARV", "Lot Cost", "Profit", "Overhead", "Sales", "Finance", "Const. Budget", "Indirects & Cont.", "Hard Costs", "Aux/Elev", "Shell Budget"], textposition="outside", text=[f"+${calc['reference_price']:,.0f}", f"-${calc['lot_val']:,.0f}", f"-${calc['profit_val']:,.0f}", f"-${calc['overhead_val']:,.0f}", f"-${calc['sales_val']:,.0f}", f"-${calc['finance_val']:,.0f}", f"${calc['total_construction_budget']:,.0f}", f"-${calc['total_indirect_costs']:,.0f}", f"${calc['target_direct_hard_cost']:,.0f}", f"-${calc['our_aux_cost_total']:,.0f}", f"${calc['target_heated_hard_cost']:,.0f}"], y=[calc['reference_price'], -calc['lot_val'], -calc['profit_val'], -calc['overhead_val'], -calc['sales_val'], -calc['finance_val'], 0, -calc['total_indirect_costs'], 0, -calc['our_aux_cost_total'], 0], decreasing={"marker": {"color": "#d62728"}}, increasing={"marker": {"color": "#1f77b4"}}, totals={"marker": {"color": "#2ca02c"}}))
    fig_rev.update_layout(title="Reverse-Engineered Target Budget Waterfall", showlegend=False, yaxis_title="Amount ($)")
    st.plotly_chart(fig_rev, use_container_width=True)
    st.divider()

# ==========================================
# --- 16. LONG-TERM PORTFOLIO WEALTH ---
# ==========================================
st.markdown("### 16. Long-Term Portfolio Wealth & Tax Shelter")
long_term_intro = f"Models 30-year horizon tracking **{calc['appreciation_rate']*100:.1f}% annual appreciation** and **${calc['annual_tax_savings']:,.0f} annual depreciation tax shelter**."
st.info(long_term_intro.replace("$", r"\$"))

tot_ret_viz_data = pd.DataFrame({"Wealth Pillar": ["1. Net Cash Flow", "2. Principal Paydown", "3. Asset Appreciation", "4. Tax Savings"], "Amount ($)": [calc['yr1_cf'], calc['yr1_prin'], calc['yr1_appr'], calc['yr1_tax']], "Category": ["Year 1 Total Return"] * 4})
fig_tot_ret = px.bar(tot_ret_viz_data, x="Category", y="Amount ($)", color="Wealth Pillar", barmode="stack", text="Amount ($)", title=f"Year 1 Return: ${calc['total_yr1_return']:,.0f}", color_discrete_sequence=["#2ca02c", "#1f77b4", "#ff7f0e", "#9467bd"])
fig_tot_ret.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', insidetextanchor='middle')

fig_wealth = go.Figure()
fig_wealth.add_trace(go.Scatter(x=calc['proj_years'], y=calc['loan_vals'], name="Remaining Loan", fill='tozeroy', fillcolor='rgba(214, 39, 40, 0.1)', mode='lines', line_color='#d62728'))
fig_wealth.add_trace(go.Scatter(x=calc['proj_years'], y=calc['asset_vals'], name="Asset Value", fill='tonexty', fillcolor='rgba(44, 160, 44, 0.2)', mode='lines', line_color='#2ca02c'))
fig_wealth.update_layout(title="30-Year Equity Accumulation", xaxis_title="Years", yaxis_title="Value ($)", hovermode="x unified")

ret_col1, ret_col2 = st.columns([1, 2])
ret_col1.plotly_chart(fig_tot_ret, use_container_width=True)
ret_col2.plotly_chart(fig_wealth, use_container_width=True)

projection_data = {
    "Metric": ["Portfolio Value", "Loan Balance", "Equity", "Net Cash Flow", "Principal Paid", "Tax Shield", "Total Return", "IRR"],
    "Year 1": [f"${calc['asset_vals'][1]:,.0f}", f"${calc['loan_vals'][1]:,.0f}", f"${calc['equity_vals'][1]:,.0f}", f"${calc['cumulative_cf'][1]:,.0f}", f"${calc['principal_paid'][1]:,.0f}", f"${calc['annual_tax_savings']:,.0f}", f"${calc['cumulative_cf'][1] + calc['principal_paid'][1] + (calc['asset_vals'][1] - calc['total_arv']) + calc['annual_tax_savings']:,.0f}", "-"],
    "Year 5": [f"${calc['asset_vals'][5]:,.0f}", f"${calc['loan_vals'][5]:,.0f}", f"${calc['equity_vals'][5]:,.0f}", f"${calc['cumulative_cf'][5]:,.0f}", f"${calc['principal_paid'][5]:,.0f}", f"${calc['annual_tax_savings'] * 5:,.0f}", f"${calc['cumulative_cf'][5] + calc['principal_paid'][5] + (calc['asset_vals'][5] - calc['total_arv']) + (calc['annual_tax_savings'] * 5):,.0f}", calc['irr_5_str']],
    "Year 10": [f"${calc['asset_vals'][10]:,.0f}", f"${calc['loan_vals'][10]:,.0f}", f"${calc['equity_vals'][10]:,.0f}", f"${calc['cumulative_cf'][10]:,.0f}", f"${calc['principal_paid'][10]:,.0f}", f"${calc['annual_tax_savings'] * 10:,.0f}", f"${calc['cumulative_cf'][10] + calc['principal_paid'][10] + (calc['asset_vals'][10] - calc['total_arv']) + (calc['annual_tax_savings'] * 10):,.0f}", calc['irr_10_str']]
}
with st.expander("📊 View Projected Returns", expanded=False):
    st.dataframe(pd.DataFrame(projection_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 16.5 FIVE-YEAR PORTFOLIO PROJECTIONS & REFI ---
# ==========================================
st.markdown("### 16.5 Five-Year Portfolio Projections & 80% LTV Refinance Analysis")

# --- Dynamic Year 5 Engine Variables ---
y5_units = 6
y5_rent_growth = 0.03  # Standard 3% escalation
y5_refi_ltv = 0.80
y5_closing_pct = 0.03  # 3% refi closing costs

arv_u = calc['arv_per_unit']
rent_u = calc['gross_monthly_rent']
appr_r = calc['appreciation_rate']
vac_r = calc['vacancy_rate']
opex_r = calc['opex_rate']
mo_pi_u = calc['monthly_pi_per_unit']
r_mo = calc['net_refi_rate'] / 12.0

initial_loan_u = calc['loan_total'] / calc['units']
bal = initial_loan_u * y5_units
total_ds_annual = mo_pi_u * 12 * y5_units

y_arv, y_port, y_rent, y_gross, y_egi, y_opex, y_noi, y_ds, y_ncf, y_prin, y_bal = [], [], [], [], [], [], [], [], [], [], []
cum_prin = 0

# --- Calculate 5-Year Progression ---
for y in range(1, 6):
    # Appreciation & Value
    curr_arv = arv_u * ((1 + appr_r) ** (y - 1))
    port_val = curr_arv * y5_units
    
    # Income & Operations
    curr_rent = rent_u * ((1 + y5_rent_growth) ** (y - 1))
    ann_gross = curr_rent * 12 * y5_units
    egi = ann_gross * (1 - vac_r)
    opex = egi * opex_r
    noi = egi - opex
    ncf = noi - total_ds_annual
    
    # Exact Amortization Paydown Loop (12 months)
    yr_prin = 0
    for _ in range(12):
        if r_mo > 0:
            interest = bal * r_mo
            prin = (mo_pi_u * y5_units) - interest
        else:
            prin = (mo_pi_u * y5_units)
        yr_prin += prin
        bal -= prin
        
    cum_prin += yr_prin
    
    y_arv.append(curr_arv)
    y_port.append(port_val)
    y_rent.append(curr_rent)
    y_gross.append(ann_gross)
    y_egi.append(egi)
    y_opex.append(-opex)
    y_noi.append(noi)
    y_ds.append(-total_ds_annual)
    y_ncf.append(ncf)
    y_prin.append(cum_prin)
    y_bal.append(bal)

# --- Year 5 Refinance Execution ---
y5_new_loan = y_port[4] * y5_refi_ltv
y5_closing_costs = y5_new_loan * y5_closing_pct
y5_payoff = y_bal[4]
y5_net_cash_out = y5_new_loan - y5_payoff - y5_closing_costs

# Calculate new DSCR on the newly minted debt to verify solvency
if r_mo > 0:
    y5_new_mo_pi = (y5_new_loan) * (r_mo * (1 + r_mo)**360) / ((1 + r_mo)**360 - 1)
else:
    y5_new_mo_pi = y5_new_loan / 360
y5_new_dscr = y_noi[4] / (y5_new_mo_pi * 12) if y5_new_mo_pi > 0 else 0

# --- UI Rendering ---
y5_intro = (
    f"This section projects the 5-year financial performance of the **{y5_units}-house** annual portfolio. It incorporates compounding "
    f"**{y5_rent_growth*100:.1f}%** annual rent growth, **{appr_r*100:.1f}%** annual appreciation (starting from ${arv_u:,.0f} ARV), "
    f"standard debt amortization, a Year-5 cash-out refinance at an **{y5_refi_ltv*100:.0f}% LTV**, and deducts estimated refinance "
    f"closing costs of {y5_closing_pct*100:.1f}% of the new loan amount."
)
st.info(y5_intro.replace("$", r"\$"))

# --- Dynamic Waterfall Chart ---
fig_y5_refi = go.Figure(go.Waterfall(
    name="Year 5 Refinance",
    orientation="v",
    measure=["relative", "relative", "relative", "total"],
    x=[f"{y5_refi_ltv*100:.0f}% LTV New Loan", "Payoff Existing Debt", "Closing Costs (3%)", "Net Tax-Free Liquidity"],
    textposition="outside",
    text=[f"+${y5_new_loan:,.0f}", f"-${y5_payoff:,.0f}", f"-${y5_closing_costs:,.0f}", f"${y5_net_cash_out:,.0f}"],
    y=[y5_new_loan, -y5_payoff, -y5_closing_costs, y5_net_cash_out],
    connector={"line": {"color": "rgb(63, 63, 63)"}},
    decreasing={"marker": {"color": "#d62728"}},
    increasing={"marker": {"color": "#1f77b4"}},
    totals={"marker": {"color": "#2ca02c"}}
))
fig_y5_refi.update_layout(
    title=f"Year-5 Portfolio Refinance Event Execution ({y5_units} Doors)", 
    showlegend=False, 
    yaxis_title="Amount ($)",
    margin=dict(t=40, b=20, l=20, r=20)
)
st.plotly_chart(fig_y5_refi, use_container_width=True)

# --- Data Table ---
y5_data = {
    "Portfolio Projection Metric": [
        f"Average Property Value (ARV @ {appr_r*100:.1f}% Appr.)",
        f"Total Portfolio Value ({y5_units} Doors)",
        f"Average Monthly Gross Rent ({y5_rent_growth*100:.1f}% Esc.)",
        f"Total Annual Gross Revenue ({y5_units} Doors)",
        f"Effective Gross Income (Less {vac_r*100:.1f}% Vacancy)",
        f"Operating Expenses ({opex_r*100:.1f}% OpEx)",
        "Portfolio Net Operating Income (NOI)",
        f"Total Annual Debt Service",
        "Total Annual Net Cash Flow (Portfolio)",
        f"Cumulative Principal Paydown",
        "Ending Total Loan Balance (Remaining Prin.)",
        f"Year-5 {y5_refi_ltv*100:.0f}% LTV Refi Gross Proceeds",
        f"(-) Estimated Refi Closing Costs ({y5_closing_pct*100:.1f}%)",
        f"Year-5 Net Tax-Free Cash-Out Proceeds"
    ],
    "Year 1": [f"${y_arv[0]:,.0f}", f"${y_port[0]:,.0f}", f"${y_rent[0]:,.0f}", f"${y_gross[0]:,.0f}", f"${y_egi[0]:,.0f}", f"${y_opex[0]:,.0f}", f"${y_noi[0]:,.0f}", f"${y_ds[0]:,.0f}", f"${y_ncf[0]:,.0f}", f"${y_prin[0]:,.0f}", f"${y_bal[0]:,.0f}", "-", "-", "-"],
    "Year 2": [f"${y_arv[1]:,.0f}", f"${y_port[1]:,.0f}", f"${y_rent[1]:,.0f}", f"${y_gross[1]:,.0f}", f"${y_egi[1]:,.0f}", f"${y_opex[1]:,.0f}", f"${y_noi[1]:,.0f}", f"${y_ds[1]:,.0f}", f"${y_ncf[1]:,.0f}", f"${y_prin[1]:,.0f}", f"${y_bal[1]:,.0f}", "-", "-", "-"],
    "Year 3": [f"${y_arv[2]:,.0f}", f"${y_port[2]:,.0f}", f"${y_rent[2]:,.0f}", f"${y_gross[2]:,.0f}", f"${y_egi[2]:,.0f}", f"${y_opex[2]:,.0f}", f"${y_noi[2]:,.0f}", f"${y_ds[2]:,.0f}", f"${y_ncf[2]:,.0f}", f"${y_prin[2]:,.0f}", f"${y_bal[2]:,.0f}", "-", "-", "-"],
    "Year 4": [f"${y_arv[3]:,.0f}", f"${y_port[3]:,.0f}", f"${y_rent[3]:,.0f}", f"${y_gross[3]:,.0f}", f"${y_egi[3]:,.0f}", f"${y_opex[3]:,.0f}", f"${y_noi[3]:,.0f}", f"${y_ds[3]:,.0f}", f"${y_ncf[3]:,.0f}", f"${y_prin[3]:,.0f}", f"${y_bal[3]:,.0f}", "-", "-", "-"],
    "Year 5": [f"${y_arv[4]:,.0f}", f"${y_port[4]:,.0f}", f"${y_rent[4]:,.0f}", f"${y_gross[4]:,.0f}", f"${y_egi[4]:,.0f}", f"${y_opex[4]:,.0f}", f"${y_noi[4]:,.0f}", f"${y_ds[4]:,.0f}", f"${y_ncf[4]:,.0f}", f"${y_prin[4]:,.0f}", f"${y_bal[4]:,.0f}", f"${y5_new_loan:,.0f}", f"-${y5_closing_costs:,.0f}", f"+${y5_net_cash_out:,.0f}"]
}

with st.expander(f"📈 View {y5_units}-House 5-Year Portfolio Progression Matrix", expanded=True):
    st.dataframe(pd.DataFrame(y5_data), hide_index=True, use_container_width=True)

y5_takeaway = (
    f"**5-Year Projections & Net {y5_refi_ltv*100:.0f}% LTV Refinance Takeaway**\n\n"
    f"Over a 5-year hold, compounding {y5_rent_growth*100:.0f}% annual rent growth expands annual portfolio net cash flow from **${y_ncf[0]:,.0f}** to **${y_ncf[4]:,.0f}/year** "
    f"while standard amortization pays down **${y_prin[4]:,.0f} in principal**. By Year 5, portfolio value reaches **${y_port[4]:,.0f}**. "
    f"Executing an {y5_refi_ltv*100:.0f}% LTV cash-out refinance (${y5_new_loan:,.0f} gross proceeds minus ${y5_payoff:,.0f} payoff balance and ${y5_closing_costs:,.0f} in estimated closing costs) "
    f"unlocks a net **${y5_net_cash_out:,.0f} in tax-free liquidity** for the developer while maintaining a highly secure **{y5_new_dscr:.2f}x DSCR** on the newly minted commercial debt."
)
st.success(y5_takeaway.replace("$", r"\$"))
st.divider()

# ==========================================
# --- 17. EXPORT ENGINES ---
# ==========================================
st.markdown("### 🖨️ 17. Export Reports & Lender Proposals")

pdf_detail_mode = st.radio("PDF Construction Detail Level:", ["Full 36-Component Breakdown", "8 Major NAHB Categories Only", "High-Level Roll-up Only"], horizontal=True)

ui_inputs = {
    "project_name": project_name,
    "project_address": project_address,
    "project_beds": project_beds,
    "project_baths": project_baths,
    "report_date": report_date,
    "borrower_name": borrower_name,
    "borrower_company": borrower_company,
    "borrower_address": borrower_address,
    "borrower_phone": borrower_phone,
    "borrower_email": borrower_email,
    "const_bank_name": st.session_state.get("const_bank_name", "Local Regional Bank"),
    "const_bank_contact": st.session_state.get("const_bank_contact", "Commercial Loan Officer"),
    "refi_bank_name": st.session_state.get("refi_bank_name", "National DSCR Lender"),
    "refi_bank_contact": st.session_state.get("refi_bank_contact", "Takeout Underwriter")
}

texts_dict = {
    "executive_summary_text": executive_summary_text,
    "horizontal_summary_text": horizontal_summary_text,
    "granular_summary_text": granular_summary_text,
    "operating_summary_text": operating_summary_text,
    "waterfall_summary_text": waterfall_summary_text,
    "strategy_comparison_text": strategy_comparison_text,
    "strategy_footnote_text": strategy_footnote_text,
    "scaling_intro": scaling_intro,
    "scaling_takeaway": scaling_takeaway,
    "scurve_summary": scurve_summary,
    "stress_test_summary": stress_test_summary,
    "opex_sens_summary": opex_sens_summary,
    "rent_sens_summary": rent_sens_summary,
    "long_term_intro": long_term_intro
}

tables_dict = {
    "horizontal_data": horizontal_data,
    "direct_rollup_df": direct_rollup_df,
    "pdf_granular_data": pdf_granular_data,
    "df_schedule": calc['df_schedule'],
    "df_stress": calc['df_stress'],
    "df_opex_sens": calc['df_opex_sens'],
    "df_rent_sens": calc['df_rent_sens'],
    "projection_data": projection_data,
    "strategy_data": strategy_data,
    "scaling_data": scaling_data,
    "dscr_summary_data": dscr_summary_data
}

col_p1, col_p2 = st.columns(2)
with col_p1:
    st.download_button("📄 Download Full Enterprise Pro Forma PDF", data=create_pdf(pdf_detail_mode, ui_inputs, calc, texts_dict, tables_dict), file_name=f"{borrower_company}_BTR_ProForma_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", use_container_width=True)
with col_p2:
    st.download_button("📄 Download Construction Proposal Letter", data=create_lender_letter_pdf("Construction", ui_inputs, calc), file_name=f"{borrower_company}_Const_Proposal_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", use_container_width=True)

col_p3, col_p4 = st.columns(2)
with col_p3:
    st.download_button("📄 Download Refinance Takeout Letter", data=create_lender_letter_pdf("Refinance", ui_inputs, calc), file_name=f"{borrower_company}_Refi_Proposal_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", use_container_width=True)
with col_p4:
    st.download_button("📊 Download Presentation Deck (PPTX)", data=create_pptx(ui_inputs, calc), file_name=f"{borrower_company}_Deck_{report_date.replace(' ', '_').replace(',', '')}.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)

st.download_button("📄 Download Slide Deck (PDF Slides)", data=create_slide_pdf(ui_inputs, calc), file_name=f"{borrower_company}_Slide_Deck_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", use_container_width=True)
st.download_button("💼 Download Master Business Plan", data=create_business_plan_pdf(ui_inputs, calc), file_name=f"{borrower_company}_Business_Plan_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", use_container_width=True)

# ==========================================
# --- 18. TECHNICAL BRIEFS & CAPEX ---
# ==========================================
st.markdown("### 📎 18. Technical Briefs & CapEx Analysis")
st.info("Download supplemental technical and financial briefs that substantiate long-term material efficiencies and operational cost protections.")

col_tb1, col_tb2 = st.columns(2)
with col_tb1:
    st.download_button(
        label="📄 Download Technical Brief 1 (LVP Break-Even)", 
        data=create_tb1_lvp_pdf(ui_inputs), 
        file_name=f"{borrower_company}_TechBrief1_LVP_{report_date.replace(' ', '_').replace(',', '')}.pdf", 
        mime="application/pdf", 
        use_container_width=True
    )
with col_tb2:
    st.download_button(
        label="📄 Download Technical Brief 2 (Showers vs. Custom Tile)", 
        data=create_tb2_shower_pdf(ui_inputs), 
        file_name=f"{borrower_company}_TechBrief2_Showers_{report_date.replace(' ', '_').replace(',', '')}.pdf", 
        mime="application/pdf", 
        use_container_width=True
    )

st.divider()
