import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os
from datetime import datetime

# Import Modular Project Engines
from config import HARDCODED_DRIVERS, NAHB_HEATED_DIVS, NAHB_STRUCT_DIVS, STRESS_SCENARIOS
from calculations import run_underwriting_engine
from pdf_engine import create_pdf, create_lender_letter_pdf
from presentation_engine import create_pptx, create_slide_pdf
from business_plan_engine import create_business_plan_pdf
from technical_briefs_engine import create_tb1_lvp_pdf, create_tb2_shower_pdf

# Page Configuration
st.set_page_config(page_title="Wickboldt Capital | Algorithmic Cost & Yield Optimization Engine", layout="wide")

# Initialize Session State Defaults
for key, value in HARDCODED_DRIVERS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Enforce specific UI defaults on initial load (takes precedence over config.py)
if "first_load_complete" not in st.session_state:
    st.session_state["amortization_type"] = "Fully Amortizing (30-Yr)"
    st.session_state["arv_constraint_mode"] = "Reverse-Engineer Max ARV from Min. Cash Flow"
    st.session_state["target_grm"] = 10.0
    st.session_state["base_prime_rate"] = 6.75
    st.session_state["borrower_fico"] = 750
    st.session_state["comp_address"] = "435 Pine St, Independence, LA 70443"
    st.session_state["refi_points_pct"] = 3.0
    st.session_state["refi_margin_pct"] = 0.50
    st.session_state["first_load_complete"] = True

if "raw_api_data" not in st.session_state:
    st.session_state.raw_api_data = None

def format_surplus(val):
    return f"+${val:,.0f}" if val >= 0 else f"-${-val:,.0f}"

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
        with st.expander("API Configuration (Optional)"):
            manual_key = st.text_input("RentCast API Key Override", type="password")

        if st.button("Fetch Live Data", width='stretch'):
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
    st.text_input("Comparable Property Address", value="435 Pine St, Independence, LA 70443", key="comp_address", disabled=is_rentcast)
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
    
    st.markdown("##### Commercial Base Rate (WSJ Prime)")
    st.radio("Prime Rate Source", ["Manual Entry", "Fetch Live FRED API (DPRIME)"], key="prime_rate_mode")
    if st.button("Fetch Live Fed Prime Rate", width='stretch'):
        fred_api_key = os.environ.get("FRED_API_KEY", "")
        if not fred_api_key:
            try:
                fred_api_key = st.secrets.get("FRED_API_KEY", "")
            except Exception:
                fred_api_key = ""

        if not fred_api_key:
            st.error("FRED_API_KEY not found in environment variables or secrets.toml.")
        else:
            try:
                with st.spinner("Fetching DPRIME from St. Louis Fed..."):
                    url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DPRIME&api_key={fred_api_key.strip()}&file_type=json&sort_order=desc&limit=1"
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        wsj_prime = float(data['observations'][0]['value'])
                        st.session_state.base_prime_rate = wsj_prime
                        st.success(f"Successfully fetched: {wsj_prime}%")
                    else:
                        st.error(f"FRED API Error: {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: {e}")
                    
    current_prime = st.session_state.get("base_prime_rate", 6.75)
    
    if st.session_state.prime_rate_mode == "Manual Entry":
        current_prime = st.number_input("Manual Prime Rate (%)", min_value=1.0, max_value=15.0, step=0.25, value=st.session_state.get("base_prime_rate", 6.75), key="base_prime_rate")

    st.markdown("##### Bank Lending Margin & Discounts")
    bank_margin = st.number_input("Bank Lending Margin (Prime + %)", min_value=0.0, max_value=10.0, step=0.25, value=1.00, key="bank_margin_pct", help="The spread your bank charges above the Prime Rate.")
    
    st.selectbox("Construction / Bank LTC (%)", [80.0, 75.0, 70.0], key="const_ltv_pct", help="Select bank loan-to-cost tier. Lower LTC tiers unlock commercial rate discounts.")
    
    base_c_rate = current_prime + bank_margin
    st.session_state["const_rate_pct"] = base_c_rate 
    
    current_ltv = st.session_state.get("const_ltv_pct", 80.0)
    rate_discount = max(0.0, (80.0 - current_ltv) / 5.0) * 0.5
    effective_c_rate = max(1.0, base_c_rate - rate_discount)
    
    if rate_discount > 0:
        st.markdown(f"📈 **Base Rate (Prime + Margin):** `{base_c_rate:.2f}%`\n📉 **Tiered Equity Discount:** `-{rate_discount:.2f}%`\n🎯 **Effective Rate:** `{effective_c_rate:.2f}%`")
    else:
        st.markdown(f"🎯 **Effective Construction Rate:** `{effective_c_rate:.2f}%`")
    
    st.slider("Construction Duration (Months)", min_value=3, max_value=18, step=1, key="build_months")
    
    st.markdown("##### Lender Information")
    st.text_input("Construction Bank Name", key="const_bank_name")
    st.text_input("Contact Person", key="const_bank_contact")
    
    st.markdown("##### Closing Costs")
    st.radio("Closing Fee Entry Mode", ["Flat Lump Sum", "Detailed Enterprise Breakout"], key="const_closing_mode")
    if st.session_state.const_closing_mode == "Flat Lump Sum":
        st.number_input("Const Loan Closing Fee ($ total)", min_value=0, step=500, format="%d", key="const_closing_fee")
    else:
        with st.expander("Detailed Closing Costs", expanded=True):
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
    st.subheader("9. True Operating Pro Forma")
    
    st.number_input("Min. Acceptable Cash Flow / Door ($)", min_value=0.0, max_value=1000.0, step=25.0, key="target_min_cashflow_per_door")
    st.number_input("Gross Monthly Rental Income per Unit ($)", min_value=0, step=25, format="%d", key="gross_monthly_rent")
    
    st.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, step=1.0, key="vacancy_rate_pct")
    st.slider("Property Management Fee (% of EGI)", min_value=0.0, max_value=15.0, step=0.5, key="mgmt_fee_pct")
    
    current_mgmt_pct = st.session_state.get("mgmt_fee_pct", 8.0)
    project_units = st.session_state.get("units", 1)
    
    st.radio("Other OpEx Entry Mode", ["Percentage of EGI (%)", "Itemized Global Costs ($ Total Project)"], key="opex_entry_mode")
    if st.session_state.opex_entry_mode == "Percentage of EGI (%)":
        st.slider("Other Operating Expenses (OpEx) Rate of EGI (%)", min_value=5.0, max_value=50.0, step=1.0, key="opex_rate_pct")
        current_other_pct = st.session_state.get("opex_rate_pct", 15.0)
        st.markdown(f"**🎯 True Total OpEx:** `{current_mgmt_pct + current_other_pct:.1f}% of EGI`")
    else:
        current_tax_g = st.session_state.get("opex_taxes_global", 0.0)
        current_ins_g = st.session_state.get("opex_ins_global", 0.0)
        current_flood_g = st.session_state.get("opex_flood_global", 0.0)
        current_lawn_g = st.session_state.get("opex_lawn_global", 0.0)
        current_maint_g = st.session_state.get("opex_maint_global", 0.0)
        current_misc_g = st.session_state.get("opex_misc_global", 0.0)
        
        global_rent = st.session_state.get("gross_monthly_rent", 1) * project_units
        current_vac = st.session_state.get("vacancy_rate_pct", 5.0) / 100.0
        global_egi = global_rent * (1 - current_vac)
        
        total_itemized_g = current_tax_g + current_ins_g + current_flood_g + current_lawn_g + current_maint_g + current_misc_g
        dyn_opex_pct = (total_itemized_g / global_egi) * 100 if global_egi > 0 else 0.0
        true_total_opex = current_mgmt_pct + dyn_opex_pct
        
        st.markdown(f"**🎯 True Total OpEx:** `{true_total_opex:.1f}% of EGI`")

        tax_pct = (current_tax_g / global_egi) * 100 if global_egi > 0 else 0.0
        ins_pct = (current_ins_g / global_egi) * 100 if global_egi > 0 else 0.0
        flood_pct = (current_flood_g / global_egi) * 100 if global_egi > 0 else 0.0
        lawn_pct = (current_lawn_g / global_egi) * 100 if global_egi > 0 else 0.0
        maint_pct = (current_maint_g / global_egi) * 100 if global_egi > 0 else 0.0
        misc_pct = (current_misc_g / global_egi) * 100 if global_egi > 0 else 0.0

        with st.expander(f"Itemized Global OpEx ({dyn_opex_pct:.1f}% of EGI)", expanded=True):
            st.number_input(f"Global Taxes ($/mo) — {tax_pct:.1f}%", min_value=0.0, step=50.0, key="opex_taxes_global")
            st.number_input(f"Global Hazard Ins ($/mo) — {ins_pct:.1f}%", min_value=0.0, step=50.0, key="opex_ins_global")
            st.number_input(f"Global Flood Ins ($/mo) — {flood_pct:.1f}%", min_value=0.0, step=50.0, key="opex_flood_global")
            st.number_input(f"Global Lawn Maint ($/mo) — {lawn_pct:.1f}%", min_value=0.0, step=50.0, key="opex_lawn_global")
            st.number_input(f"Global Turnover/Maint ($/mo) — {maint_pct:.1f}%", min_value=0.0, step=50.0, key="opex_maint_global")
            st.number_input(f"Global HOA / Misc ($/mo) — {misc_pct:.1f}%", min_value=0.0, step=50.0, key="opex_misc_global")
        
        st.session_state['opex_taxes_mo'] = current_tax_g / project_units
        st.session_state['opex_ins_mo'] = current_ins_g / project_units
        st.session_state['opex_flood_mo'] = current_flood_g / project_units
        st.session_state['opex_lawn_mo'] = current_lawn_g / project_units
        st.session_state['opex_maint_mo'] = current_maint_g / project_units
        st.session_state['opex_misc_mo'] = current_misc_g / project_units
            
    st.slider("Marginal Tax Rate (%) for Depreciation Benefit", min_value=10.0, max_value=50.0, step=1.0, key="income_tax_rate_pct")
    st.slider("Annual Asset Appreciation (%)", min_value=0.0, max_value=10.0, step=0.5, key="appreciation_rate_pct")

with st.sidebar.container():
    st.subheader("10. Takeout Appraisal Methodology")
    st.radio("Primary Valuation Mode", [
        "Sales Comp (Price/SF)", 
        "Income Approach (GRM)", 
        "Income Approach (DSCR Loan Sizing)",
        "Conservative (Lesser of GRM or DSCR)"
    ], key="appraisal_mode")
    
    if st.session_state.appraisal_mode in ["Income Approach (GRM)", "Conservative (Lesser of GRM or DSCR)"]:
        st.number_input("Gross Rent Multiplier (GRM)", min_value=4.0, max_value=25.0, step=0.1, value=10.0, key="target_grm")
        
    if st.session_state.appraisal_mode == "Income Approach (DSCR Loan Sizing)":
        st.info("ARV is automatically derived from your Operating (NOI) and Refi Loan terms to exactly meet your Target DSCR and LTV constraints.")
    elif st.session_state.appraisal_mode == "Conservative (Lesser of GRM or DSCR)":
        st.info("ARV evaluates both the GRM and the DSCR max loan limit, automatically defaulting to whichever yields the lower valuation.")
        
    st.divider()
    st.markdown("##### Secondary ARV Constraints")
    
    arv_constraint = st.radio("Override Target ARV?", [
        "Reverse-Engineer Max ARV from Min. Cash Flow",
        "No Override (Use Valuation Mode Above)",
        "Manual Target ARV Override"
    ], key="arv_constraint_mode", help="Allows you to bypass the primary valuation and force the reverse-engineering engine to use a specific ARV limit.")
    
    if arv_constraint == "Manual Target ARV Override":
        st.number_input("Custom Target ARV per Unit ($)", min_value=10000.0, step=5000.0, value=250000.0, key="manual_arv_override")

with st.sidebar.container():
    st.subheader("11. Takeout Refinance & Optimization Terms")
    
    st.selectbox("Refinance LTV Tier (%)", [80.0, 75.0, 70.0], key="refi_ltv_pct")
    st.selectbox("Amortization Structure", ["Fully Amortizing (30-Yr)", "Interest-Only (10-Yr IO Rider)"], key="amortization_type")
    st.number_input("Bank Target DSCR Rate", min_value=1.0, max_value=1.5, step=0.05, key="target_dscr_rate")
    st.selectbox("Amortization Term (Years)", [15, 20, 25, 30], key="refi_term_years")
    
    st.markdown("##### Commercial Base Rate & Pricing")
    st.radio("Refi Rate Source", ["Manual Entry", "Fetch Live FRED API (DPRIME)"], key="refi_rate_mode")
    
    if st.session_state.refi_rate_mode == "Fetch Live FRED API (DPRIME)":
        if st.button("Fetch Live Fed Index Rate", width='stretch'):
            fred_api_key = os.environ.get("FRED_API_KEY", "")
            if not fred_api_key:
                try:
                    fred_api_key = st.secrets.get("FRED_API_KEY", "")
                except Exception:
                    fred_api_key = ""

            if not fred_api_key:
                st.error("FRED_API_KEY not found in environment variables or secrets.toml.")
            else:
                try:
                    with st.spinner("Fetching DPRIME from St. Louis Fed..."):
                        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DPRIME&api_key={fred_api_key.strip()}&file_type=json&sort_order=desc&limit=1"
                        response = requests.get(url, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            wsj_prime = float(data['observations'][0]['value'])
                            st.session_state.refi_index_rate = wsj_prime
                            st.success(f"Successfully fetched: {wsj_prime}%")
                        else:
                            st.error(f"FRED API Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
                    
        current_refi_index = st.session_state.get("refi_index_rate", 7.50)
        st.info(f"**Active Index Rate:** `{current_refi_index:.2f}%`")
    else:
        current_refi_index = st.number_input("Manual Index Rate (%)", min_value=1.0, max_value=15.0, step=0.25, value=st.session_state.get("refi_index_rate", 7.50), key="refi_index_rate")

    # --- BANK LENDING MARGIN & RISK PROFILE ---
    st.markdown("##### Bank Lending Margin & Risk Profile")
    st.number_input("Borrower FICO Score", min_value=300, max_value=850, step=10, value=750, key="borrower_fico")
    
    margin_mode = st.radio("Refi Lending Spread Mode", ["Estimated Risk-Based Margin", "Manual Entry"], key="refi_margin_mode")
    
    # Calculate target tier logic
    fico = st.session_state.get("borrower_fico", 750)
    ltv = st.session_state.get("refi_ltv_pct", 80.0)
    dscr_check = st.session_state.get("target_dscr_rate", 1.25)
    
    # Recalibrated Wholesale Risk-Based Pricing Matrix
    if fico < 680 or ltv > 80.0 or dscr_check < 1.00:
        derived_tier = 3
        derived_margin = 1.375 # Prime + 1.375% (Midpoint of Tier 3)
    elif fico >= 740 and ltv <= 75.0 and dscr_check >= 1.25:
        derived_tier = 1
        derived_margin = -0.375 # Prime - 0.375% (Midpoint of Tier 1 Discount)
    else:
        derived_tier = 2
        derived_margin = 0.625 # Prime + 0.625% (Midpoint of Tier 2)
        
    if margin_mode == "Estimated Risk-Based Margin":
        margin_tag = f"+{derived_margin:.3f}%" if derived_margin >= 0 else f"{derived_margin:.3f}%"
        st.info(f"**Tier {derived_tier} Pricing Activated:** `{margin_tag}` Margin")
        refi_margin = derived_margin
    else:
        refi_margin = st.number_input("Manual Refi Lending Spread (+/- %)", min_value=-5.0, max_value=10.0, step=0.1, value=0.50, key="refi_margin_pct", help="The margin your bank charges above or below the Index Rate.")
    # ------------------------------------------

    raw_refi_rate = current_refi_index + refi_margin
    current_refi_ltv = st.session_state.get("refi_ltv_pct", 80.0)
    
    refi_rate_discount = max(0.0, (80.0 - current_refi_ltv) / 5.0) * 0.5
    adjusted_base_r_rate = max(1.0, raw_refi_rate - refi_rate_discount)
    
    st.session_state["base_refi_rate_pct"] = adjusted_base_r_rate
    
    # Clear breakdown of where the Effective Base Rate comes from
    margin_display_str = f"+{refi_margin:.3f}%" if refi_margin >= 0 else f"{refi_margin:.3f}%"
    if refi_rate_discount > 0:
        st.markdown(f"🏛️ **Index Rate:** `{current_refi_index:.2f}%`\n📊 **Risk Margin (Tier {derived_tier}):** `{margin_display_str}`\n📈 **Raw Rate (Index + Spread):** `{raw_refi_rate:.3f}%`\n📉 **Tiered Equity Discount (LTV Reward):** `-{refi_rate_discount:.3f}%`\n🎯 **Effective Base Rate:** `{adjusted_base_r_rate:.3f}%`")
    else:
        st.markdown(f"🏛️ **Index Rate:** `{current_refi_index:.2f}%`\n📊 **Risk Margin (Tier {derived_tier}):** `{margin_display_str}`\n📈 **Raw Rate (Index + Spread):** `{raw_refi_rate:.3f}%`\n🎯 **Effective Base Rate:** `{adjusted_base_r_rate:.3f}%`")
    
    st.markdown("##### Lender Points & Closing Bundle")
    
    st.number_input(
        "Lender Discount Points (%)", 
        min_value=0.0, 
        max_value=5.0, 
        step=0.25,
        value=3.0,
        format="%.2f", 
        key="refi_points_pct", 
        help="Points paid to lender to buy down rate (e.g. 3.0 pts for 6.99%)."
    )
    
    # --- LIVE NET RATE DISPLAY ---
    current_pts = st.session_state.get("refi_points_pct", 3.0)
    # 1 point = 0.25% reduction in rate
    final_net_rate_pct = max(0.25, adjusted_base_r_rate - (current_pts * 0.25))
    st.markdown(f"🎯 **Effective Net Refi Rate (w/ {current_pts:.2f} Pts):** `{final_net_rate_pct:.2f}%`")
    # -----------------------------
    
    # --- CLOSING BUNDLE TOGGLE ---
    st.markdown("##### Takeout Closing & Title Bundle")
    closing_bundle_mode = st.radio("Closing Bundle Mode", ["Standard Fixed ($6,500)", "Manual Custom Input"], key="refi_bundle_mode", horizontal=True)

    if closing_bundle_mode == "Standard Fixed ($6,500)":
        refi_closing_bundle = 6500.0
        st.info("📌 **Active Closing Bundle:** `$6,500` (Standard Title, Escrow & Legal)")
    else:
        refi_closing_bundle = st.number_input("Custom Closing Bundle ($)", min_value=0.0, step=250.0, value=6500.0, key="manual_refi_bundle")
    st.session_state["active_refi_bundle"] = refi_closing_bundle
    
    st.markdown("##### Lender Information")
    st.text_input("Refinance Bank Name", key="refi_bank_name")
    st.text_input("Contact Person", key="refi_bank_contact")

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

with st.expander("Project Details", expanded=True):
    top_col1, top_col2, top_col3 = st.columns([2, 2, 1])
    project_name = top_col1.text_input("Project Title", placeholder="e.g. Phase 1 - 24-Lot Build-to-Rent")
    project_address = top_col2.text_input("Project Address", placeholder="e.g. Rogers Moore Parkway, Hammond, LA")
    report_date = datetime.now().strftime("%B %d, %Y")

    sub_col1, sub_col2, sub_col3 = st.columns([1, 1, 2])
    project_beds = sub_col1.number_input("Beds per Unit", min_value=1, value=3, step=1)
    project_baths = sub_col2.number_input("Baths per Unit", min_value=1.0, value=2.0, step=0.5)

with st.expander("Borrower Details", expanded=True):
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
arv_label = "Derived Unit ARV (Price/SF)" if calc['appraisal_mode'] == "Sales Comp (Price/SF)" else "Derived Unit ARV"
op1.metric(arv_label, f"${calc['arv_per_unit']:,.0f}", f"${calc['total_arv']:,.0f} Total ARV")
op2.metric("Actual DSCR Rate", f"{calc['actual_dscr']:.2f}x", f"Target: {calc['target_dscr_rate']:.2f}x", delta_color="normal" if calc['actual_dscr'] >= calc['target_dscr_rate'] else "inverse")
op3.metric("Monthly Cash Flow", f"${calc['monthly_cash_flow']:,.0f} /mo", f"${calc['monthly_cash_flow']*12:,.0f} Annual", delta_color="normal" if calc['monthly_cash_flow_per_door'] >= calc['target_min_cashflow_per_door'] else "inverse")
op4.metric("Monthly P&I Payment", f"${calc['total_monthly_pi']:,.0f} /mo", f"{calc['refi_term_years']}Yr @ {calc['net_refi_rate']*100:.3f}%")

st.markdown("### 🚦 Go/No-Go Investment Decision Dashboard")
dscr_pass = calc['actual_dscr'] >= calc['target_dscr_rate']
cash_pass = calc['cash_surplus'] >= 0
cf_pass = calc['monthly_cash_flow_per_door'] >= calc['target_min_cashflow_per_door']

dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
dash_col1.metric("DSCR Underwriting Status", "🟢 GREEN LIGHT" if dscr_pass else "🔴 RED LIGHT", f"Actual: {calc['actual_dscr']:.2f}x (Target: {calc['target_dscr_rate']:.2f}x)", delta_color="normal" if dscr_pass else "inverse")
dash_col2.metric("Cash Flow Status", "🟢 GREEN LIGHT" if cf_pass else "🔴 RED LIGHT", f"Actual: ${calc['monthly_cash_flow_per_door']:,.0f}/door (Target: ${calc['target_min_cashflow_per_door']:,.0f})", delta_color="normal" if cf_pass else "inverse")
dash_col3.metric("Capital Recovery Status", "🟢 GREEN LIGHT" if cash_pass else "🔴 RED LIGHT", f"${calc['cash_surplus']:,.0f} at Refi Close", delta_color="normal" if cash_pass else "inverse")
dash_col4.metric("Day-1 Wealth Creation", f"${calc['day1_wealth']:,.0f}", f"${calc['day1_wealth']/calc['units']:,.0f} per door", delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# --- DYNAMIC EXECUTIVE CONCLUSION BUBBLE ---
# ==========================================
safe_dscr = round(calc['actual_dscr'], 2)
dscr_pass_safe = safe_dscr >= calc['target_dscr_rate']

if dscr_pass_safe and cf_pass and cash_pass:
    conclusion_text = (
        f"**✅ PROJECT CLEARED FOR EXECUTION:**\n\n"
        f"This build configuration is structurally sound and achieves an infinite return profile. "
        f"The **{safe_dscr:.2f}x DSCR** successfully clears the bank's {calc['target_dscr_rate']:.2f}x minimum, unlocking the full **${calc['loan_total']:,.0f}** permanent takeout loan. "
        f"Operations generate a healthy **${calc['monthly_cash_flow_per_door']:,.0f} per month** net cash flow per door. "
        f"Most importantly, the loan proceeds completely pay off the **${calc['total_project_basis']:,.0f}** capital basis, returning 100% of your seed capital and handing you a **${calc['cash_surplus']:,.0f} tax-free cash surplus** at closing."
    )
    st.success(conclusion_text.replace("$", r"\$"))
else:
    failures = []
    
    if not dscr_pass_safe:
        failures.append(f"- **DSCR Failure (Lender Rejection Risk):** The modeled {safe_dscr:.2f}x DSCR falls below the bank's {calc['target_dscr_rate']:.2f}x limit. This suppresses your permanent loan amount and forces you to leave cash in the deal.")
        
    if not cf_pass:
        failures.append(f"- **Cash Flow Squeeze:** The unit yields only ${calc['monthly_cash_flow_per_door']:,.0f} per month, which is below your baseline target of ${calc['target_min_cashflow_per_door']:,.0f} per month.")
        
    if not cash_pass:
        failures.append(f"- **Trapped Capital (Loss at Close):** The takeout loan (${calc['loan_total']:,.0f}) is too small to cover the total project basis (${calc['total_project_basis']:,.0f}). This traps **${-calc['cash_surplus']:,.0f}** of seed capital inside the asset as dead equity.")
        
    conclusion_text = (
        f"**🛑 UNDERWRITING WARNING - OPTIMIZATION REQUIRED:**\n\n"
        f"This configuration fails one or more core investment constraints. To execute an infinite-return BTR strategy, you must adjust your levers (lower direct costs, buy down the interest rate, or increase target rents):\n\n" + 
        "\n\n".join(failures)
    )
    st.error(conclusion_text.replace("$", r"\$"))

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

with st.expander("View Comp Math Audit & Raw API Data", expanded=False):
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

with st.expander("View Land Development & Infrastructure Budget", expanded=False):
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

with st.expander("View Granular Trade Buildup & Master Roll-up", expanded=False):
    granular_mode = st.radio("Buildup Entry Mode", ["Auto-Proportional (Linked to Master Model)", "Manual Custom Entry (Bottom-Up)"], horizontal=True)
    pdf_granular_data = []

    if granular_mode == "Auto-Proportional (Linked to Master Model)":
        st.markdown(f"#### 4.1 Heated Living Area ({calc['sqft']} SF @ ${calc['direct_cost_sf']:.2f} / SF)".replace("$", r"\$"))
        h_data = {"Division / Trade Level": [], "Live Cost / SF": [], "Per Unit Cost": []}
        for name, base_val, is_header in NAHB_HEATED_DIVS:
            live_sf = calc['direct_cost_sf'] * (base_val / 100.0)
            prefix = "" if is_header else "    "
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
                pdf_granular_data.append((f"    - {row['Division / Component']}", live_sf, live_sf * calc['sqft'], live_sf * calc['sqft'] * calc['units'], False))

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
        "Bank Under underwriting Step": ["1. Gross Potential Rent (Bank Model)", "2. Less: Bank Vacancy & OpEx Deductions", "3. Bank Qualified Net Operating Income (NOI)", "4. Target Construction DSCR Constraint", "5. Bank Implied Asset Value", f"6. Const. Lender Loan Value ({calc['const_ltv']*100:.1f}% Bank LTC)", "7. Total Capitalized Construction Basis", "8. Required Seed Capital Reserve"],
        "Value": [f"${calc['cb_gross_annual_rent']:,.0f} / yr", f"-${calc['cb_gross_annual_rent'] - calc['cb_noi']:,.0f} / yr", f"${calc['cb_noi']:,.0f} / yr", f"{calc['const_bank_dscr']:.2f}x", f"${calc['bank_stressed_value']:,.0f}", f"${calc['actual_const_loan']:,.0f}", f"${calc['total_construction_basis']:,.0f}", f"${calc['seed_capital']:,.0f}"]
    }
else:
    st.info(f"**Construction Loan Under underwriting:** The bank determines implied asset value on a **{calc['const_bank_grm']:.1f}x Gross Rent Multiplier** (yielding **${calc['bank_stressed_value']:,.0f}**). Loan cap: **${calc['actual_const_loan']:,.0f}**.".replace("$", r"\$"))
    stress_test_data = {
        "Bank Underwriting Step": ["1. Gross Potential Rent (Bank Model)", "2. Bank Underwriting GRM", "3. Bank Implied Asset Value", f"4. Const. Lender Loan Value ({calc['const_ltv']*100:.1f}% Bank LTC)", "5. Total Capitalized Construction Basis", "6. Required Seed Capital Reserve"],
        "Value": [f"${calc['cb_gross_annual_rent']:,.0f} / yr", f"{calc['const_bank_grm']:.1f}x", f"${calc['bank_stressed_value']:,.0f}", f"${calc['actual_const_loan']:,.0f}", f"${calc['total_construction_basis']:,.0f}", f"${calc['seed_capital']:,.0f}"]
    }

cap_viz_data = pd.DataFrame({"Metric": ["1. Total Capital Basis", "2. Max Allowed Loan", "3. Bank Appraised Value"], "Amount ($)": [calc['total_construction_basis'], calc['actual_const_loan'], calc['bank_stressed_value']], "Category": ["Basis", "Loan", "Value"]})
fig_cap = px.bar(cap_viz_data, x="Metric", y="Amount ($)", color="Category", text="Amount ($)", title="Construction Loan Sizing vs. Project Cost", color_discrete_map={"Basis": "#ff7f0e", "Loan": "#1f77b4", "Value": "#2ca02c"})
fig_cap.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
fig_cap.update_layout(showlegend=False, xaxis_title="", yaxis_title="Amount ($)", yaxis=dict(range=[0, max(calc['bank_stressed_value'], calc['total_construction_basis']) * 1.15]))
st.plotly_chart(fig_cap, use_container_width=True)

with st.expander("View Bank Stress Test Metrics", expanded=False):
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

with st.expander("View Capital Ledgers & Transaction Scope", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(pd.DataFrame({"Component": [f"Finished Lot Benchmark ({calc['lot_cost_pct']*100:.1f}%)", "Adjusted BTR Hard Costs", "Indirects, Cont. & GC Fee", "On-Lot Utilities & Soft Costs", "Finance, Closing & Buydown", "Built-in Developer Margin", "Total Appraised Value (ARV)"], "Amount": [f"${calc['lot_benchmark']:,.0f}", f"${calc['total_hard_cost']:,.0f}", f"${calc['total_indirect_costs']:,.0f}", f"${calc['total_vertical_soft']:,.0f}", f"${calc['btr_finance_closing']:,.0f}", f"${calc['developer_margin']:,.0f}", f"${calc['total_arv']:,.0f}"]}), hide_index=True, use_container_width=True)
    with col2:
        st.dataframe(pd.DataFrame({"Component": ["Const. Loan Closing Fees", "Carrying Interest", "Perm. Takeout Fees", f"Rate Buydown ({calc['buydown_pts']:.2f} pts)"], "Amount": [f"${calc['const_closing_fee']:,.0f}", f"${calc['carry_int_base']:,.0f}", f"${calc['refi_closing_fee']:,.0f}", f"${calc['default_buydown_cost']:,.0f}"]}), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 7. BANK DSCR UNDERWRITING & TRUE CASH FLOW ---
# ==========================================
st.markdown("### 7. Bank DSCR Underwriting & True Operating Cash Flow")

u_rent = st.session_state.get('gross_monthly_rent', 0) * calc['units']
u_tax = st.session_state.get('opex_taxes_mo', 0) * calc['units']
u_ins = st.session_state.get('opex_ins_mo', 0) * calc['units']
u_flood = st.session_state.get('opex_flood_mo', 0) * calc['units']
u_hoa = st.session_state.get('opex_misc_mo', 0) * calc['units']

bank_tia_mo = u_tax + u_ins + u_flood + u_hoa
total_pitia_mo = calc['total_monthly_pi'] + bank_tia_mo

operating_summary_text = (
    f"**1. Bank Underwriting (PITIA Method):** The lender sizes the commercial loan by dividing the Gross Rent (**${u_rent:,.0f}**) by the PITIA payment "
    f"(P&I + Taxes + Ins + HOA = **${total_pitia_mo:,.0f}**), yielding a **{calc['actual_dscr']:.2f}x DSCR**.\n\n"
    f"**2. True Pro Forma Cash Flow:** After satisfying the bank's PITIA, we account for actual market Vacancy (**${calc['monthly_vacancy_loss']:,.0f}**), "
    f"Management Fees (**${calc['monthly_mgmt_fee']:,.0f}**), and Maintenance/Lawn Care. The asset produces a true net operating cash flow of "
    f"**${calc['monthly_cash_flow_per_door']:,.0f} / door / month**."
)
st.info(operating_summary_text.replace("$", r"\$"))

dscr_summary_data = {
    "Bank Underwriting (DSCR Sizing)": [
        "Gross Scheduled Rent", 
        "(-) Monthly P&I Debt Service", 
        "(-) Taxes, Ins, Flood & HOA (TIA)", 
        "= Total Bank PITIA Payment", 
        "Actual Bank DSCR (Rent ÷ PITIA)"
    ],
    "Monthly": [
        f"${u_rent:,.0f}", 
        f"-${calc['total_monthly_pi']:,.0f}", 
        f"-${bank_tia_mo:,.0f}", 
        f"${total_pitia_mo:,.0f}", 
        f"{calc['actual_dscr']:.2f}x"
    ]
}

proforma_summary_data = {
    "True Operating Pro Forma": [
        "Gross Scheduled Rent", 
        f"(-) Vacancy Loss @ {st.session_state.get('vacancy_rate_pct', 5.0):.1f}%", 
        "= Effective Gross Income (EGI)", 
        f"(-) Property Management @ {st.session_state.get('mgmt_fee_pct', 8.0):.1f}%", 
        "(-) Taxes, Insurance & HOA", 
        "(-) Maintenance, Lawn & Turnover", 
        "= True Net Operating Income (NOI)", 
        "(-) Monthly P&I Debt Service", 
        "= True Net Cash Flow"
    ],
    "Monthly": [
        f"${u_rent:,.0f}", 
        f"-${calc['monthly_vacancy_loss']:,.0f}", 
        f"${(u_rent - calc['monthly_vacancy_loss']):,.0f}", 
        f"-${calc['monthly_mgmt_fee']:,.0f}", 
        f"-${bank_tia_mo:,.0f}", 
        f"-${(calc['mo_other_opex'] * calc['units']) - bank_tia_mo:,.0f}", 
        f"${calc['monthly_noi']:,.0f}", 
        f"-${calc['total_monthly_pi']:,.0f}", 
        f"${calc['monthly_cash_flow']:,.0f}"
    ]
}

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.dataframe(pd.DataFrame(dscr_summary_data), hide_index=True, use_container_width=True)
with col_t2:
    st.dataframe(pd.DataFrame(proforma_summary_data), hide_index=True, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### ⚖️ Maximum Loan Sizing Constraints & Reverse-Calculation")

cf_loan = calc['cf_max_loan_total']
bank_loan = calc['bank_dscr_max_loan_total']
actual_loan = calc['loan_total']

loan_comp_df = pd.DataFrame({
    "Loan Limit Type": [
        f"1. Bank Limit ({calc['target_dscr_rate']:.2f}x DSCR)", 
        f"2. Cash Flow Limit (Min ${calc['target_min_cashflow_per_door']:,.0f}/door)", 
        f"3. Active Modeled Loan ({calc['refi_ltv']*100:.0f}% LTV)"
    ],
    "Maximum Loan Amount": [bank_loan, cf_loan, actual_loan]
})

fig_loan_limits = px.bar(
    loan_comp_df, 
    x="Maximum Loan Amount", 
    y="Loan Limit Type", 
    orientation="h", 
    color="Loan Limit Type",
    text="Maximum Loan Amount",
    color_discrete_sequence=["#1f77b4", "#ff7f0e", "#2ca02c"]
)
fig_loan_limits.update_traces(texttemplate='$%{text:,.0f}', textposition='inside', insidetextanchor='middle')
fig_loan_limits.update_layout(showlegend=False, xaxis_title="Maximum Loan Amount ($)", yaxis_title="")

limit_text = (
    f"**The Leverage Squeeze:**\n\n"
    f"While the bank's strict PITIA DSCR allows you to borrow up to **${bank_loan:,.0f}**, maximizing that leverage would compress your "
    f"true operating cash flow below your baseline target of **${calc['target_min_cashflow_per_door']:,.0f}** per door.\n\n"
    f"To successfully hit your personal cash flow minimums after accounting for all true operating expenses (vacancy, mgmt, maintenance), "
    f"your maximum borrowable amount is strictly capped at **${cf_loan:,.0f}**.\n\n"
    f"Currently, your active modeled takeout loan is **${actual_loan:,.0f}**."
)

col_l1, col_l2 = st.columns([1.5, 1])
with col_l1:
    st.plotly_chart(fig_loan_limits, use_container_width=True)
with col_l2:
    st.info(limit_text.replace("$", r"\$"))

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
with st.expander("View Financial Strategy Comparison Matrix", expanded=False):
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
with st.expander("View Multi-Unit Scaling Table", expanded=False):
    st.dataframe(pd.DataFrame(scaling_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 10.5 THE EXIT & TWO-POCKET STRATEGY ---
# ==========================================
st.markdown("### 10.5. The Exit: Refinance & The \"Two-Pocket\" Cash Flow Strategy")

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

with st.expander("View Detailed Wealth Creation Matrix", expanded=True):
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

with st.expander("View S-Curve Schedule Table", expanded=False):
    st.dataframe(calc['df_schedule'].style.format({"Monthly Draw ($)": "${:,.0f}", "Capitalized Interest ($)": "${:,.0f}", "Total Drawn Balance ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 11.2 COMMERCIAL TAKEOUT RISK PROFILE ---
# ==========================================
st.markdown("### 11.2 Commercial Takeout Risk Profile & Pricing Margin")

risk_intro = (
    "Commercial DSCR loan pricing is directly linked to the borrower's risk profile. "
    "Lenders determine the base margin over WSJ Prime using a matrix driven by "
    "**FICO Score**, **Loan-to-Value (LTV)**, and the underwritten **Debt Service Coverage Ratio (DSCR)**."
)
st.info(risk_intro)

risk_df = pd.DataFrame({
    "Risk Profile Characteristics": [
        "Tier 1 (Prime Pricing)", 
        "Tier 2 (Standard Pricing)", 
        "Tier 3 (High-Risk Pricing)"
    ],
    "DSCR Requirement": ["≥ 1.25x", "1.00x – 1.24x", "< 1.00x"],
    "FICO Requirement": ["≥ 740", "680 – 739", "< 680"],
    "Max LTV Limit": ["≤ 75%", "80%", "> 80%"],
    "Estimated Margin Spread": [
        "Prime - 0.625% to -0.125%", 
        "Prime + 0.250% to +1.000%", 
        "Prime + 1.000% to +1.750%"
    ]
})

st.dataframe(risk_df, hide_index=True, use_container_width=True)

col_r1, col_r2 = st.columns(2)

with col_r1:
    st.markdown("#### 🎯 Active Risk Assessment")
    st.markdown(f"- **Borrower FICO:** `{st.session_state.get('borrower_fico', 750)}`")
    st.markdown(f"- **Refinance LTV:** `{st.session_state.get('refi_ltv_pct', 80.0):.0f}%`")
    st.markdown(f"- **Underwritten DSCR:** `{calc['actual_dscr']:.2f}x`")

with col_r2:
    st.markdown("#### 🏦 Applied Pricing Tier")
    st.markdown(f"Based on the most constraining metric, the engine has categorized this transaction as **Tier {derived_tier}**.")
    margin_disp = f"+{derived_margin:.3f}%" if derived_margin >= 0 else f"{derived_margin:.3f}%"
    st.markdown(f"- **Applied Target Margin:** `{margin_disp}`")
    st.markdown(f"- **Index Rate:** `{current_refi_index:.2f}%`")
    st.markdown(f"- **Gross Base Rate:** `{current_refi_index + derived_margin:.3f}%`")

st.divider()

# ==========================================
# --- 11.5 REFINANCE OPTIMIZATION MATRIX & TARGET CALLOUT ---
# ==========================================
st.markdown("### 11.5 Refinance Optimization Matrix & Target Benchmarking")

opt_intro = (
    f"This matrix sweeps across LTV tiers (**80%, 75%, 70%**) and debt structures to identify the optimal configuration "
    f"meeting your target **$\ge \${calc['target_min_cashflow_per_door']:.0f}/mo$ net cash flow** and **net-zero out-of-pocket** closing constraints "
    f"for the Hammond asset (**${calc['total_arv']/calc['units']:,.0f} ARV**, **${calc['total_project_basis']:,.0f} Basis**, **${calc['gross_monthly_rent']:,.0f}/mo Rent**)."
)
st.info(opt_intro.replace("$", r"\$"))

matrix_rows = []
test_ltvs = [80.0, 75.0, 70.0]
test_structures = ["Interest-Only (10-Yr IO Rider)", "Fully Amortizing (30-Yr)"]

for ltv_val in test_ltvs:
    ltv_decimal = ltv_val / 100.0
    gross_loan_sim = calc['total_arv'] * ltv_decimal
    buydown_pts_sim = st.session_state.get("refi_points_pct", 3.0)
    points_cost_sim = gross_loan_sim * (buydown_pts_sim / 100.0)
    net_rate_sim = calc['net_refi_rate']
    refi_closing_bundle_sim = st.session_state.get("active_refi_bundle", 6500.0)
    
    for struct in test_structures:
        if struct == "Interest-Only (10-Yr IO Rider)":
            pi_mo = (gross_loan_sim / calc['units']) * (net_rate_sim / 12.0)
        else:
            m_rate = net_rate_sim / 12.0
            n_pmts = calc['refi_term_years'] * 12
            if m_rate > 0:
                pi_mo = (gross_loan_sim / calc['units']) * (m_rate * (1 + m_rate)**n_pmts) / ((1 + m_rate)**n_pmts - 1)
            else:
                pi_mo = (gross_loan_sim / calc['units']) / n_pmts
                
        tot_pi_mo = pi_mo * calc['units']
        tot_outflow_mo = tot_pi_mo + calc['mo_opex']
        net_cf_door = (calc['monthly_noi'] - tot_pi_mo) / calc['units']
        
        pitia_unit = pi_mo + calc['bank_tia_per_unit']
        dscr_sim = calc['gross_monthly_rent'] / pitia_unit if pitia_unit > 0 else 0
        
        basis_payoff_sim = calc['total_construction_basis']
        cash_at_table_sim = gross_loan_sim - basis_payoff_sim - points_cost_sim - refi_closing_bundle_sim
        
        if net_cf_door >= calc['target_min_cashflow_per_door'] and cash_at_table_sim >= -500 and dscr_sim >= calc['target_dscr_rate']:
            fit_status = "🟢 Optimal Target"
        elif net_cf_door >= calc['target_min_cashflow_per_door'] and dscr_sim >= calc['target_dscr_rate']:
            fit_status = "🟡 Hits Flow / Capital Req."
        elif dscr_sim >= calc['target_dscr_rate']:
            fit_status = "🟠 Misses Cash Flow Target"
        else:
            fit_status = "🔴 Fails DSCR / High Risk"
            
        matrix_rows.append({
            "LTV Tier": f"{ltv_val:.0f}%",
            "Structure": "10-Yr IO" if "IO" in struct else f"{calc['refi_term_years']}-Yr Amort",
            "Rate": f"{net_rate_sim*100:.2f}%",
            "Gross Loan": f"${gross_loan_sim:,.0f}",
            "Monthly P&I": f"${tot_pi_mo:,.0f}",
            "Total Outflow": f"${tot_outflow_mo:,.0f}",
            "Net Cash Flow": f"${net_cf_door:,.0f} /mo",
            "DSCR": f"{dscr_sim:.2f}x",
            "Cash-at-Table": f"+${cash_at_table_sim:,.0f}" if cash_at_table_sim >= 0 else f"-${-cash_at_table_sim:,.0f}",
            "Fit Status": fit_status
        })

df_opt_matrix = pd.DataFrame(matrix_rows)
st.dataframe(df_opt_matrix, hide_index=True, use_container_width=True)

col_b1, col_b2 = st.columns(2)

with col_b1:
    st.markdown("#### 🎯 Hammond Target Benchmark Card")
    st.markdown(f"- **ARV Valuation:** `${calc['arv_per_unit']:,.0f}`")
    st.markdown(f"- **Construction Basis Payoff:** `${calc['total_construction_basis']:,.0f}`")
    st.markdown(f"- **Active Gross Loan ({calc['refi_ltv']*100:.0f}% LTV):** `${calc['loan_total']:,.0f}`")
    st.markdown(f"- **Net Effective Rate (w/ {calc['buydown_pts']:.1f} Pts):** `{calc['net_refi_rate']*100:.2f}%`")

with col_b2:
    st.markdown("#### 📊 Execution Summary")
    st.markdown(f"- **Total Monthly Outflow (PITIA + OpEx):** `${calc['total_monthly_pi'] + calc['mo_opex']:,.0f}/mo`")
    st.markdown(f"- **Net Monthly Cash Flow:** `+${calc['monthly_cash_flow_per_door']:,.0f}/mo per door` (Target: $\ge\${calc['target_min_cashflow_per_door']:.0f}$) ")
    st.markdown(f"- **Underwritten DSCR:** `{calc['actual_dscr']:.2f}x` (Target: $\ge{calc['target_dscr_rate']:.2f}x$)")
    st.markdown(f"- **Net Cash-at-Table:** `{format_surplus(calc['net_cash_at_closing'])}` (Target: $\ge \$0$)")

st.divider()

# ==========================================
# --- 12. SENSITIVITY ANALYSIS (STRESS TEST) ---
# ==========================================
st.markdown("### 12. Sensitivity Analysis (Stress Testing)")
stress_test_summary = f"Stress-tests active pro forma against market volatility, proving DSCR safety (**> {calc['target_dscr_rate']:.2f}x**)."
st.info(stress_test_summary.replace("$", r"\$"))

df_stress_plot = calc['df_stress'].copy()
df_stress_plot['DSCR Color'] = df_stress_plot['Raw DSCR'].apply(lambda x: '#2ca02c' if x >= calc['target_dscr_rate'] else '#d62728')
df_stress_plot['Surplus Color'] = df_stress_plot['Raw Surplus'].apply(lambda x: '#2ca02c' if x >= 0 else '#d62728')
df_stress_plot['Short Name'] = df_stress_plot['Stress Scenario'].apply(lambda x: x.split(". ")[1] if ". " in x else x)

stress_col1, stress_col2 = st.columns(2)

with stress_col1:
    fig_stress_dscr = go.Figure(go.Bar(
        x=df_stress_plot['Short Name'], 
        y=df_stress_plot['Raw DSCR'], 
        marker_color=df_stress_plot['DSCR Color'], 
        text=df_stress_plot['Raw DSCR'].apply(lambda x: f"{x:.2f}x"), 
        textposition='auto'
    ))
    fig_stress_dscr.add_hline(y=calc['target_dscr_rate'], line_dash="dash", line_color="black", annotation_text=f"Min {calc['target_dscr_rate']:.2f}x", annotation_position="top right")
    fig_stress_dscr.update_layout(title="DSCR Safety Under Duress", yaxis_title="DSCR Rate", showlegend=False)
    st.plotly_chart(fig_stress_dscr, use_container_width=True)

with stress_col2:
    fig_stress_surplus = go.Figure(go.Bar(
        x=df_stress_plot['Short Name'], 
        y=df_stress_plot['Raw Surplus'], 
        marker_color=df_stress_plot['Surplus Color'], 
        text=df_stress_plot['Raw Surplus'].apply(lambda x: f"${x:,.0f}"), 
        textposition='auto'
    ))
    fig_stress_surplus.add_hline(y=0, line_color="black")
    fig_stress_surplus.update_layout(title="Capital Recovery Under Duress", yaxis_title="Surplus / (Trapped) $", showlegend=False)
    st.plotly_chart(fig_stress_surplus, use_container_width=True)

with st.expander("View Lender Risk Mitigation Matrix", expanded=False):
    st.dataframe(calc['df_stress'].drop(columns=["Raw DSCR", "Raw Surplus"]), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 13. OPEX SENSITIVITY ---
# ==========================================
st.markdown("### 13. Operating Expense (OpEx) Sensitivity")
opex_sens_summary = f"Evaluates fluctuations in OpEx against baseline **${calc['total_gross_monthly_income']:,.0f}** gross rent and fixed **${calc['total_monthly_pi']:,.0f}** monthly P&I."
st.info(opex_sens_summary.replace("$", r"\$"))

opex_ncfs = [noi - calc['total_monthly_pi'] for noi in calc['raw_opex_nois']]

col_opex1, col_opex2 = st.columns(2)

with col_opex1:
    fig_opex_dscr = go.Figure(go.Bar(
        x=calc['opex_labels'], 
        y=calc['raw_opex_dscrs'], 
        marker_color=calc['opex_colors'], 
        text=[f"{d:.2f}x" for d in calc['raw_opex_dscrs']], 
        textposition='auto'
    ))
    fig_opex_dscr.add_hline(y=calc['target_dscr_rate'], line_dash="dash", line_color="black", annotation_text=f"Target: {calc['target_dscr_rate']:.2f}x", annotation_position="top right")
    fig_opex_dscr.add_hline(y=1.0, line_dash="solid", line_color="#d62728", annotation_text="Breakeven (1.0x)", annotation_position="bottom right")
    fig_opex_dscr.update_layout(title="DSCR Safety Margin Drop-off", yaxis_title="DSCR Rate", showlegend=False)
    st.plotly_chart(fig_opex_dscr, use_container_width=True)

with col_opex2:
    fig_opex_ncf = go.Figure(go.Bar(
        x=calc['opex_labels'], 
        y=opex_ncfs, 
        marker_color=calc['opex_colors'], 
        text=[f"${cf:,.0f}" for cf in opex_ncfs], 
        textposition='auto'
    ))
    fig_opex_ncf.add_hline(y=0, line_dash="solid", line_color="#d62728", annotation_text="Breakeven ($0)", annotation_position="bottom right")
    fig_opex_ncf.update_layout(title="Net Monthly Cash Flow Impact", yaxis_title="Net Cash Flow ($)", showlegend=False)
    st.plotly_chart(fig_opex_ncf, use_container_width=True)

with st.expander("View Detailed OpEx Stress Matrix", expanded=False):
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

with st.expander("View Detailed Rent Sensitivity Matrix", expanded=False):
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
# --- 15.5 REVERSE-ENGINEERED COST COMPRESSION ---
# ==========================================
st.markdown(f"### 15.5 Reverse-Engineered Cost Compression Analysis (Baseline {calc['sqft']:,.0f} SF + {st.session_state.structure_type})")

comp_intro = (
    f"This section analyzes the direct relationship between construction costs and the developer’s Day-1 wealth creation using our core {calc['sqft']:,.0f} SF + {calc['struct_sqft']:,.0f} SF {st.session_state.structure_type.lower()} model. "
    f"Here, the target Appraised Value (ARV) remains fixed (${calc['arv_per_unit']:,.0f}). Because the commercial takeout loan is capped at **${calc['loan_total']/calc['units']:,.0f}** "
    f"({calc['refi_ltv']*100:.0f}% LTV), any reduction in the Total Cost / SF translates dollar-for-dollar into a reduction of the direct build cost, immediately boosting closing cash surplus. "
    f"This factors in the {calc['build_months']}-month construction timeline carrying interest."
)
st.info(comp_intro.replace("$", r"\$"))

compression_data = []
comp_labels = []
comp_cfs_plot = []
comp_colors = []

base_d_cost = calc['direct_cost_sf']
step_val = max(3.0, base_d_cost * 0.05)
test_d_costs = [
    base_d_cost + (step_val * 2),
    base_d_cost + (step_val * 1),
    base_d_cost,
    base_d_cost - (step_val * 1),
    base_d_cost - (step_val * 2),
    base_d_cost - (step_val * 3),
    base_d_cost - (step_val * 4)
]

for idx, d_cost in enumerate(test_d_costs):
    if d_cost <= 0: continue
    
    h_hc = d_cost * calc['sqft']
    if calc['aux_cost_mode'] == "Percentage of Heated Rate (%)":
        aux_c = (d_cost * calc['aux_ratio'] * calc['aux_sqft_total']) + calc['additional_foundation_cost']
    else:
        aux_c = (calc['aux_fixed_cost_sf'] * calc['aux_sqft_total']) + calc['additional_foundation_cost']
    t_hc = h_hc + aux_c
    
    c_pct = calc['contingency_pct']
    p_pct = calc['indirect_permits_pct']
    t_pct = calc['indirect_temp_facilities_pct']
    
    cont = t_hc * c_pct
    perm = t_hc * p_pct
    temp = t_hc * t_pct
    fee_b = t_hc + cont + perm + temp
    
    gc = calc['custom_gc_fee']/calc['units'] if calc['gc_fee_mode'] == "Consolidated Flat Fee ($ Total)" else fee_b * calc['gc_fee_pct']
    t_ind = cont + perm + temp + gc
    t_const = t_hc + t_ind
    
    unit_const_loan = calc['actual_const_loan'] / calc['units']
    carry = unit_const_loan * 0.5 * calc['const_rate'] * (calc['build_months'] / 12.0)
    
    unit_land = calc['total_land_default'] / calc['units']
    unit_soft = calc['total_vertical_soft'] / calc['units']
    unit_const_close = calc['const_closing_fee'] / calc['units']
    unit_refi_close = calc['refi_closing_fee'] / calc['units']
    unit_buy = calc['default_buydown_cost'] / calc['units']
    
    basis_ex_refi = unit_land + t_const + unit_soft + unit_const_close + carry
    total_basis = basis_ex_refi + unit_refi_close + unit_buy
    
    unit_refi_loan = calc['loan_total'] / calc['units']
    unit_seed = max(0, basis_ex_refi - unit_const_loan)
    net_cash_close = unit_refi_loan - unit_const_loan - unit_refi_close - unit_buy
    surplus = net_cash_close - unit_seed
    
    retained_eq = calc['arv_per_unit'] - unit_refi_loan
    wealth = gc + max(0, surplus) + retained_eq
    
    tot_cost_sf = total_basis / calc['sqft']
    
    if idx == 0:
        lbl_prefix = "(Over Budget Risk)"
    elif idx == 2:
        lbl_prefix = "(Active Model)"
    elif idx == 6:
        lbl_prefix = "(Maximum Compression)"
    else:
        lbl_prefix = ""
        
    compression_data.append({
        "Target Total Cost / SF Scenario": f"${tot_cost_sf:,.2f} / SF {lbl_prefix}",
        "Required Direct Build Cost / SF": f"${d_cost:,.2f}",
        "Total Hard Cost (w/ Aux)": f"${t_hc:,.0f}",
        "Total Const. Budget (w/ GC)": f"${t_const:,.0f}",
        "Total Project Capital Basis": f"${total_basis:,.0f}",
        f"Fixed Refi Takeout ({calc['refi_ltv']*100:.0f}% LTV)": f"${unit_refi_loan:,.0f}",
        "Day-1 Cash Surplus at Close": f"+${surplus:,.0f}" if surplus >=0 else f"-${-surplus:,.0f}",
        "Total Day-1 Created Value": f"${wealth:,.0f}"
    })
    
    comp_labels.append(f"${d_cost:.0f}/SF Direct")
    comp_cfs_plot.append(surplus)
    comp_colors.append('#2ca02c' if surplus >= 0 else '#d62728')

fig_comp_chart = go.Figure(go.Bar(
    x=comp_labels, 
    y=comp_cfs_plot,
    marker_color=comp_colors,
    text=[f"+${cf:,.0f}" if cf >= 0 else f"-${-cf:,.0f}" for cf in comp_cfs_plot],
    textposition='auto',
))
fig_comp_chart.add_hline(y=0, line_dash="solid", line_color="black")
fig_comp_chart.update_layout(
    title="Day-1 Cash Surplus vs. Direct Build Cost / SF Target",
    yaxis_title="Net Cash Surplus at Close ($)",
    xaxis_title="Required Direct Build Cost / SF Scenario",
    showlegend=False
)
st.plotly_chart(fig_comp_chart, use_container_width=True)

with st.expander("View Detailed Cost Compression Matrix", expanded=True):
    st.dataframe(pd.DataFrame(compression_data), hide_index=True, use_container_width=True)

comp_takeaway = (
    f"**Direct Cost Compression Takeaway**\n\n"
    f"Because the commercial takeout loan is strictly capped at **${calc['loan_total']/calc['units']:,.0f}** by the fixed retail ARV, any dollar compressed out of construction flows directly to the developer as "
    f"liquid, tax-free cash surplus at closing. Factoring in the {calc['build_months']}-month build carry interest, higher cost-per-square-foot tiers severely compress cash surplus, potentially trapping seed capital. "
    f"However, by aggressively engineering the direct build cost down to the lower benchmark tiers, the project yields an immediate surge in tax-free cash-out surplus while returning 100% of seed capital and "
    f"securing maximum Total Day-1 wealth creation per door."
)
st.success(comp_takeaway.replace("$", r"\$"))
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
with st.expander("View Projected Returns", expanded=False):
    st.dataframe(pd.DataFrame(projection_data), hide_index=True, use_container_width=True)
st.divider()

# ==========================================
# --- 16.5 FIVE-YEAR PORTFOLIO PROJECTIONS & REFI ---
# ==========================================
st.markdown("### 16.5 Five-Year Portfolio Projections & 80% LTV Refinance Analysis")

y5_units = 6
y5_rent_growth = 0.03 
y5_refi_ltv = 0.80
y5_closing_pct = 0.03 

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

for y in range(1, 6):
    curr_arv = arv_u * ((1 + appr_r) ** (y - 1))
    port_val = curr_arv * y5_units
    
    curr_rent = rent_u * ((1 + y5_rent_growth) ** (y - 1))
    ann_gross = curr_rent * 12 * y5_units
    egi = ann_gross * (1 - vac_r)
    opex = egi * opex_r
    noi = egi - opex
    ncf = noi - total_ds_annual
    
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

y5_new_loan = y_port[4] * y5_refi_ltv
y5_closing_costs = y5_new_loan * y5_closing_pct
y5_payoff = y_bal[4]
y5_net_cash_out = y5_new_loan - y5_payoff - y5_closing_costs

if r_mo > 0:
    y5_new_mo_pi = (y5_new_loan) * (r_mo * (1 + r_mo)**360) / ((1 + r_mo)**360 - 1)
else:
    y5_new_mo_pi = y5_new_loan / 360
y5_new_dscr = y_noi[4] / (y5_new_mo_pi * 12) if y5_new_mo_pi > 0 else 0

y5_intro = (
    f"This section projects the 5-year financial performance of the **{y5_units}-house** annual portfolio. It incorporates compounding "
    f"**{y5_rent_growth*100:.1f}%** annual rent growth, **{appr_r*100:.1f}%** annual appreciation (starting from ${arv_u:,.0f} ARV), "
    f"standard debt amortization, a Year-5 cash-out refinance at an **{y5_refi_ltv*100:.0f}% LTV**, and deducts estimated refinance "
    f"closing costs of {y5_closing_pct*100:.1f}% of the new loan amount."
)
st.info(y5_intro.replace("$", r"\$"))

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
    increasing={"marker": {"color": "#2ca02c"}},
    totals={"marker": {"color": "#2ca02c"}}
))
fig_y5_refi.update_layout(
    title=f"Year-5 Portfolio Refinance Event Execution ({y5_units} Doors)", 
    showlegend=False, 
    yaxis_title="Amount ($)",
    margin=dict(t=40, b=20, l=20, r=20)
)
st.plotly_chart(fig_y5_refi, use_container_width=True)

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

with st.expander(f"View {y5_units}-House 5-Year Portfolio Progression Matrix", expanded=True):
    st.dataframe(pd.DataFrame(y5_data), hide_index=True, use_container_width=True)

y5_takeaway = (
    f"**5-Year Projections & Net {y5_refi_ltv*100:.0f}% LTV Refinance Takeaway**\n\n"
    f"Over a 5-year hold, compounding {y5_rent_growth*100:.1f}% annual rent growth expands annual portfolio net cash flow from **${y_ncf[0]:,.0f}** to **${y_ncf[4]:,.0f}/year** "
    f"while standard amortization pays down **${y_prin[4]:,.0f} in principal**. By Year 5, portfolio value reaches **${y_port[4]:,.0f}**. "
    f"Executing an {y5_refi_ltv*100:.0f}% LTV cash-out refinance (${y5_new_loan:,.0f} gross proceeds minus ${y5_payoff:,.0f} payoff balance and ${y5_closing_costs:,.0f} in estimated closing costs) "
    f"unlocks a net **${y5_net_cash_out:,.0f} in tax-free liquidity** for the developer while maintaining a highly secure **{y5_new_dscr:.2f}x DSCR** on the newly minted commercial debt."
)
st.success(y5_takeaway.replace("$", r"\$"))
st.divider()

# ==========================================
# --- 16.6 POST-REFINANCE CASH FLOW SENSITIVITY ---
# ==========================================
st.markdown("### 16.6 Post-Refinance Cash Flow Sensitivity Analysis (Post-Year 5 Refi)")

y5_loan_per_door = y5_new_loan / y5_units
y5_noi_total = y_noi[4]
y5_noi_per_door_annual = y5_noi_total / y5_units
y5_noi_per_door_monthly = y5_noi_per_door_annual / 12.0
y5_gross_rent_door = y_rent[4]

y5_sens_intro = (
    f"Following the Year-5 cash-out refinance at {y5_refi_ltv*100:.0f}% LTV, the new total portfolio loan balance across the {y5_units} homes is "
    f"**${y5_new_loan:,.0f}** (${y5_loan_per_door:,.0f} per door). This section evaluates the resulting annual and monthly cash flow per door "
    f"across different permanent commercial interest rates, assuming Year-5 operating performance (Year-5 Gross Rent of **${y5_gross_rent_door:,.0f}/mo**, "
    f"{vac_r*100:.0f}% vacancy, and {opex_r*100:.0f}% OpEx yielding a Year-5 NOI of **${y5_noi_total:,.0f}** total / **${y5_noi_per_door_annual:,.0f}** per door)."
)
st.info(y5_sens_intro.replace("$", r"\$"))

y5_sens_data = []
y5_rates_labels = []
y5_cfs_plot = []
y5_dscrs_plot = []
y5_colors_plot = []

rate_offsets = [-0.01, -0.005, 0.0, 0.005, 0.01]

for r_offset in rate_offsets:
    test_rate = calc['net_refi_rate'] + r_offset
    if test_rate <= 0: continue
    
    test_rate_mo = test_rate / 12.0
    
    pi_mo_door = y5_loan_per_door * (test_rate_mo * (1 + test_rate_mo)**360) / ((1 + test_rate_mo)**360 - 1)
    pi_ann_door = pi_mo_door * 12.0
    
    ncf_mo_door = y5_noi_per_door_monthly - pi_mo_door
    dscr_val = y5_noi_per_door_annual / pi_ann_door
    
    lbl = f"{test_rate*100:.2f}% Interest Rate" + (" (Baseline)" if r_offset == 0.0 else "")
    
    dscr_str = f"{dscr_val:.2f}x"
    if dscr_val < calc['target_dscr_rate']:
        dscr_str += " (Requires Buydown)"
        bar_color = '#d62728'
    elif ncf_mo_door < 0:
        bar_color = '#d62728'
    elif dscr_val < calc['target_dscr_rate'] + 0.05:
        bar_color = '#ff7f0e'
    else:
        bar_color = '#2ca02c'
        
    y5_rates_labels.append(f"{test_rate*100:.2f}%")
    y5_cfs_plot.append(ncf_mo_door)
    y5_dscrs_plot.append(dscr_val)
    y5_colors_plot.append(bar_color)

    y5_sens_data.append({
        "Interest Rate Scenario": lbl,
        "New Loan Balance (Per Door)": f"${y5_loan_per_door:,.0f}",
        "Annual P&I (Per Door)": f"-${pi_ann_door:,.0f}",
        "Monthly P&I (Per Door)": f"-${pi_mo_door:,.0f}",
        "Year-5 NOI (Per Door)": f"${y5_noi_per_door_annual:,.0f}",
        "Net Monthly Cash Flow (Per Door)": f"+${ncf_mo_door:,.0f} / mo" if ncf_mo_door >= 0 else f"-${-ncf_mo_door:,.0f} / mo",
        "Post-Refi DSCR": dscr_str
    })

fig_y5_sens = go.Figure(go.Bar(
    x=y5_rates_labels, 
    y=y5_cfs_plot,
    marker_color=y5_colors_plot,
    text=[f"CF: ${cf:,.0f}<br>{d:.2f}x DSCR" for cf, d in zip(y5_cfs_plot, y5_dscrs_plot)],
    textposition='auto',
))

fig_y5_sens.add_hline(
    y=0, 
    line_dash="solid", 
    line_color="black", 
    annotation_text="Breakeven", 
    annotation_position="bottom right"
)

fig_y5_sens.update_layout(
    title="Year-5 Post-Refinance Net Monthly Cash Flow (Per Door) vs. Interest Rates",
    yaxis_title="Net Cash Flow per Door ($)",
    xaxis_title="Future Takeout Interest Rate",
    showlegend=False
)
st.plotly_chart(fig_y5_sens, use_container_width=True)

with st.expander("View Post-Refinance Cash Flow Sensitivity Matrix", expanded=False):
    st.dataframe(pd.DataFrame(y5_sens_data), hide_index=True, use_container_width=True)

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
    "refi_bank_contact": st.session_state.get("refi_bank_contact", "Takeout Underwriter"),
    "amortization_type": st.session_state.get("amortization_type", "Interest-Only (10-Yr IO Rider)"),
    "buydown_pts": calc.get('buydown_pts', 3.0),
    "net_refi_rate": calc.get('net_refi_rate', 0.0699),
    "refi_closing_bundle": st.session_state.get("active_refi_bundle", 6500.0)
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
    st.download_button("📄 Download Full Enterprise Pro Forma PDF", data=create_pdf(pdf_detail_mode, ui_inputs, calc, texts_dict, tables_dict), file_name=f"{borrower_company}_BTR_ProForma_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", width='stretch')
with col_p2:
    st.download_button("📄 Download Construction Proposal Letter", data=create_lender_letter_pdf("Construction", ui_inputs, calc), file_name=f"{borrower_company}_Const_Proposal_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", width='stretch')

col_p3, col_p4 = st.columns(2)
with col_p3:
    st.download_button("📄 Download Refinance Takeout Letter", data=create_lender_letter_pdf("Refinance", ui_inputs, calc), file_name=f"{borrower_company}_Refi_Proposal_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", width='stretch')
with col_p4:
    st.download_button("📊 Download Presentation Deck (PPTX)", data=create_pptx(ui_inputs, calc), file_name=f"{borrower_company}_Deck_{report_date.replace(' ', '_').replace(',', '')}.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", width='stretch')

col_p5, col_p6 = st.columns(2)
with col_p5:
    st.download_button("📄 Download Slide Deck (PDF Slides)", data=create_slide_pdf(ui_inputs, calc), file_name=f"{borrower_company}_Slide_Deck_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", width='stretch')
with col_p6:
    st.download_button("💼 Download Master Business Plan", data=create_business_plan_pdf(ui_inputs, calc), file_name=f"{borrower_company}_Business_Plan_{report_date.replace(' ', '_').replace(',', '')}.pdf", mime="application/pdf", width='stretch')

st.divider()

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
        width='stretch'
    )
with col_tb2:
    st.download_button(
        label="📄 Download Technical Brief 2 (Showers vs. Custom Tile)", 
        data=create_tb2_shower_pdf(ui_inputs), 
        file_name=f"{borrower_company}_TechBrief2_Showers_{report_date.replace(' ', '_').replace(',', '')}.pdf", 
        mime="application/pdf", 
        width='stretch'
    )

st.divider()

# ==========================================
# --- 19. MASTER MODEL DRIVERS & EXECUTIVE CONCLUSION ---
# ==========================================
st.markdown("### 🔑 19. Master Model Drivers & Executive Conclusion")

intro_text = (
    "The financial success of the Wickboldt Capital BTR strategy relies on the precise orchestration of interrelated project variables. "
    "Rather than a static pro forma, this model is a dynamic engine where specific operational levers directly expand or compress "
    "profitability, capital recovery, and long-term wealth."
)
st.info(intro_text)

st.markdown("#### Primary Profit Drivers & Capital Impacts")

col_d1, col_d2 = st.columns(2)

with col_d1:
    st.markdown("""
    - **Direct Build Cost / SF (The Equity Engine):** Because the permanent takeout loan is capped by a fixed market appraisal, every dollar saved in construction costs flows 1:1 into the developer's pocket at closing. Controlling direct hard costs is the primary defense against trapped capital and the sole mechanism for generating Day-1 tax-free cash surplus.
    - **Market Rental Rate (The Leverage Ceiling):** Gross scheduled rent dictates the Net Operating Income (NOI). A higher rent raises the NOI ceiling, which directly increases the maximum allowable loan amount under commercial DSCR rules, enabling greater capital extraction.
    - **OpEx & Vacancy Factors (The NOI Defenders):** Commercial lenders strictly underwrite NOI. Allowing OpEx to drift from the modeled 25% to 35% destroys the DSCR ratio. A failed DSCR forces the developer to leave cash in the deal to lower the loan balance, severely damaging the 100% capital recovery strategy.
    - **Permanent Interest Rate & Buydown Points (The Cash Flow Governor):** This dictates the ongoing monthly P&I burden. Paying upfront points to buy down the rate (e.g., to 6.50%) is mathematically required to clear the 1.20x DSCR hurdle and ensure positive passive income over the 30-year term.
    """)

with col_d2:
    st.markdown("""
    - **Construction Loan Rate & Duration (The Capital Bleed):** Time is money. Extended construction schedules (e.g., 9 months) or elevated short-term interest rates inflate carrying costs. This accrued interest bloats the total project basis, directly consuming the cash surplus available at the permanent refinance.
    - **Land Investment Cost (The Seed Capital):** Securing finished lots at an out-of-pocket discount ($15,000 actual vs. 18% ARV benchmark) embeds immediate "phantom" equity into the deal, ensuring the takeout loan can easily cover 100% of the initial investment.
    - **Multi-Unit Phase Scaling (The Overhead Multiplier):** Building in concurrent phases (e.g., 3 to 6 doors) compresses project management and General Conditions overhead. Consolidating field operations directly shrinks the per-unit basis, scaling cash-out surpluses exponentially.
    - **Annual Appreciation & Rent Escalation (The Long-Term Multiplier):** While Year 1 focuses on capital recovery, compounding a conservative 3% annual growth in both property value and rental rates unlocks massive delayed liquidity. This mechanism enables a Year-5 80% LTV cash-out refinance, pulling hundreds of thousands in secondary tax-free cash from the portfolio.
    """)

st.markdown("<br>", unsafe_allow_html=True)

conclusion_text = (
    "**Final Strategic Conclusion**\n\n"
    "By treating these drivers not as fixed expenses but as engineered levers, the Wickboldt Capital BTR model mitigates traditional real estate risks. "
    "The dual-pronged approach—generating active GC management revenue during the build phase and retaining stabilized, cash-flowing assets with zero "
    "remaining equity exposure at stabilization—achieves an effectively infinite cash-on-cash return. Controlling build costs creates the initial equity; "
    "scaling production compresses the basis; and disciplined DSCR underwriting secures long-term, tax-advantaged portfolio growth."
)
st.success(conclusion_text)
st.divider()
