import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import requests
import os
import re
from datetime import datetime

# ==========================================
# --- GLOBAL HARDCODED MASTER DRIVERS ---
# ==========================================
# Edit these values to change the permanent global underwriting rules for your firm.
GLOBAL_DRIVERS = {
    "units": 1,
    "sqft": 1150,
    "structure_type": "Carport", # Or "Garage"
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
    
    "refi_ltv_pct": 80.0,
    "refi_term_years": 30,
    "base_refi_rate_pct": 6.5,
    "refi_closing_fee": 3650,
    "apply_buydown": False,
    "buydown_pts": 2.0,
    
    "gc_fee_mode": "Percentage of Hard Costs (%)", # Or "Consolidated Flat Fee ($ Total)"
    "gc_fee_pct": 10.0,
    "custom_gc_fee": 20000,
    "land_basis": 15000,
    
    "appraisal_mode": "Income Approach (GRM)", # Or "Sales Comp (Price/SF)"
    "target_grm": 10.5,
    
    "cost_calc_mode": "Reverse-Engineer from Appraisal", # Or "Reverse-Engineer from Primary Comp", "Manual Set (Heated SF)"
    "base_direct_cost_sf": 74.0,
    "lot_cost_pct": 18.0,
    "margin_pct": 20.0,
    "sales_pct": 8.0,
    "finance_pct": 4.0,
    
    "pdf_include_sublevels": True
}

# Initialize session state with Global Drivers
for key, value in GLOBAL_DRIVERS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Page Configuration
st.set_page_config(page_title="Wickboldt Capital | BTR Pro Forma Engine", layout="wide")

st.title("🏗️ BTR Pro Forma Engine")
st.markdown("### Wickboldt Capital — *Today's Foundation. Tomorrow's Legacy.*")
st.divider()

# Set up the Tabs (Hides the backend drivers from standard viewers)
tab_main, tab_admin = st.tabs(["📊 Main Underwriting Dashboard", "⚙️ Admin Access"])

# ==========================================
# --- ADMIN TAB (Global Overrides) ---
# ==========================================
with tab_admin:
    st.markdown("### 🔒 Master Underwriting Drivers")
    st.info("Edit the `GLOBAL_DRIVERS` dictionary at the top of `app.py` to change the permanent rules for all users. Enter the Admin PIN below to make temporary live overrides.")
    
    # Simple Admin Lock (Change "admin" to whatever you want your password to be)
    admin_pwd = st.text_input("Enter Admin PIN", type="password")
    
    if admin_pwd == "admin":
        st.success("Access Granted. Adjusting these values will instantly update the model.")
        
        col_adm1, col_adm2, col_adm3 = st.columns(3)
        with col_adm1:
            st.subheader("1. Scale & Footprint")
            st.number_input("Number of Units (Doors)", key="units")
            st.number_input("Heated SqFt per Unit", key="sqft", step=50)
            st.selectbox("Aux Structure Type", ["Carport", "Garage"], key="structure_type")
            st.number_input("Aux SqFt per Unit", key="struct_sqft", step=25)
            st.slider("Aux Cost / SF ($)", min_value=15.0, max_value=90.0, key="base_struct_cost_sf")
            st.number_input("Front Porch SqFt", key="front_porch_sqft", step=10)
            st.slider("Front Porch Cost / SF ($)", min_value=15.0, max_value=70.0, key="front_porch_cost_sf")
            st.number_input("Back Porch SqFt", key="back_porch_sqft", step=10)
            st.slider("Back Porch Cost / SF ($)", min_value=15.0, max_value=70.0, key="back_porch_cost_sf")
            st.number_input("Storage Room SqFt", key="storage_sqft", step=5)
            st.slider("Storage Room Cost / SF ($)", min_value=15.0, max_value=90.0, key="storage_cost_sf")
            st.number_input("Additional Foundation / Elevation Cost ($)", key="additional_foundation_cost", step=500)
            
            st.subheader("2. GC & Land")
            st.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"], key="gc_fee_mode")
            st.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, step=0.5, key="gc_fee_pct")
            st.number_input("Total Consolidated GC Fee ($)", step=1000, key="custom_gc_fee")
            st.number_input("Land Basis per Lot ($)", step=1000, key="land_basis")

        with col_adm2:
            st.subheader("3. Operations & Takeout")
            st.number_input("Gross Monthly Rent per Unit ($)", step=50, key="gross_monthly_rent")
            st.number_input("Target Lender DSCR Rate", step=0.05, key="target_dscr_rate")
            st.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, step=1.0, key="vacancy_rate_pct")
            st.slider("OpEx Rate of EGI (%)", min_value=15.0, max_value=50.0, step=1.0, key="opex_rate_pct")
            
            st.slider("Refinance LTV (%)", min_value=60.0, max_value=85.0, step=5.0, key="refi_ltv_pct")
            st.selectbox("Amortization Term (Years)", [15, 20, 25, 30], key="refi_term_years")
            st.slider("Base Refi Interest Rate (%)", min_value=4.0, max_value=10.0, step=0.25, key="base_refi_rate_pct")
            st.number_input("Refinance Closing Fee ($)", step=250, key="refi_closing_fee")
            st.checkbox("Apply Interest Rate Buydown Points?", key="apply_buydown")
            st.number_input("Discount Points", min_value=0.0, max_value=5.0, step=0.5, key="buydown_pts")
            
            st.subheader("4. Construction Loan")
            st.slider("Construction Loan LTV (%)", min_value=60.0, max_value=100.0, step=5.0, key="const_ltv_pct")
            st.slider("Construction Duration (Months)", min_value=3, max_value=18, step=1, key="build_months")
            st.slider("Construction Loan Rate (%)", min_value=4.0, max_value=14.0, step=0.5, key="const_rate_pct")
            st.slider("Avg Draw Utilization (%)", min_value=20.0, max_value=100.0, step=5.0, key="avg_draw_pct")
            st.number_input("Const Loan Closing Fee ($)", step=500, key="const_closing_fee")

        with col_adm3:
            st.subheader("5. Valuation & Target Costs")
            st.radio("Valuation Mode", ["Sales Comp (Price/SF)", "Income Approach (GRM)"], key="appraisal_mode")
            st.number_input("Gross Rent Multiplier (GRM)", min_value=4.0, max_value=25.0, step=0.1, key="target_grm")
            
            st.radio("Cost Target Logic", ["Manual Set (Heated SF)", "Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"], key="cost_calc_mode")
            st.slider("Direct Build Cost / SF ($) [Manual Mode Only]", min_value=40.0, max_value=150.0, step=1.0, key="base_direct_cost_sf")
            
            st.markdown("**Reverse Engineering Deductions:**")
            st.slider("Finished Lot Cost (%)", min_value=0.0, max_value=30.0, step=0.5, key="lot_cost_pct")
            st.slider("Gross Margin (O&P) (%)", min_value=0.0, max_value=30.0, step=0.5, key="margin_pct")
            st.slider("Sales & Marketing (%)", min_value=0.0, max_value=15.0, step=0.5, key="sales_pct")
            st.slider("Soft Costs & Finance (%)", min_value=0.0, max_value=15.0, step=0.5, key="finance_pct")
            
            st.subheader("Report Export")
            st.checkbox("Include Sub-Levels in PDF", key="pdf_include_sublevels")


# ==========================================
# --- EXTRACT ACTIVE VARIABLES FOR MATH ---
# ==========================================
units = st.session_state.units
sqft = st.session_state.sqft
structure_type = st.session_state.structure_type
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

refi_ltv = st.session_state.refi_ltv_pct / 100.0
refi_term_years = st.session_state.refi_term_years
base_refi_rate = st.session_state.base_refi_rate_pct / 100.0
refi_closing_fee = st.session_state.refi_closing_fee
apply_buydown = st.session_state.apply_buydown
buydown_pts = st.session_state.buydown_pts

net_refi_rate = base_refi_rate
if apply_buydown:
    net_refi_rate = max(0.01, base_refi_rate - (buydown_pts * 0.0025))

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
pdf_include_sublevels = st.session_state.pdf_include_sublevels


# ==========================================
# --- MAIN UI TAB & CALCULATIONS ---
# ==========================================
with tab_main:
    
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

    # --- TOP METRICS PLACEHOLDERS (Anchored at the top!) ---
    ui_top_metrics = st.container()
    ui_op_metrics = st.container()
    ui_decision_dashboard = st.container()
    st.divider()

    # --- COMPARABLE MARKET ANALYSIS (COMP BENCHMARK TOOL) ---
    st.markdown("### 🔍 Market Comp Valuation & Blended Rate Benchmark")
    st.markdown("Input market comparable data below. This dynamically sets the Appraised Value (ARV) and drives the Retail Reverse-Engineering cost basis.")

    if "comp_address" not in st.session_state: st.session_state.comp_address = ""
    if "comp_price" not in st.session_state: st.session_state.comp_price = 182600
    if "comp_heated_sf" not in st.session_state: st.session_state.comp_heated_sf = 1150
    if "raw_api_data" not in st.session_state: st.session_state.raw_api_data = None

    comp_entry_mode = st.radio("Comparable Data Entry Mode", ["Manual Entry", "RentCast Live API Fetch"], horizontal=True)

    if comp_entry_mode == "RentCast Live API Fetch":
        rc_col1, rc_col2 = st.columns([4, 1])
        search_address = rc_col1.text_input("Property Address", placeholder="e.g. 1103 S Spruce St, Hammond, LA 70403")
        
        with st.expander("⚙️ API Configuration (Optional)"):
            st.caption("If Railway hasn't loaded your key yet, paste it here to test immediately.")
            manual_key = st.text_input("RentCast API Key Override", type="password")

        if rc_col2.button("Fetch Live Data", use_container_width=True):
            if not search_address or search_address.strip() == "":
                st.warning("Please enter a valid property address before fetching.")
            else:
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
                                if isinstance(data, list) and len(data) > 0:
                                    prop = data[0]
                                    fetched_sf = prop.get("squareFootage")
                                    fetched_price = prop.get("price") or prop.get("lastSalePrice")
                                    fetched_addr = prop.get("formattedAddress")
                                    if not fetched_price:
                                        try:
                                            avm_url = "https://api.rentcast.io/v1/avm/value"
                                            avm_res = requests.get(avm_url, headers=headers, params={"address": fetched_addr or search_address})
                                            if avm_res.status_code == 200:
                                                fetched_price = avm_res.json().get("price")
                                        except: pass
                                    if fetched_price: st.session_state.comp_price = int(fetched_price)
                                    if fetched_sf: st.session_state.comp_heated_sf = int(fetched_sf)
                                    if fetched_addr: st.session_state.comp_address = str(fetched_addr)
                                    st.success(f"Property successfully imported: {st.session_state.comp_address}")
                                    st.rerun()
                                else:
                                    st.error("No exact match found. Make sure the address includes city, state, and zip.")
                            elif response.status_code == 400:
                                st.error("Error 400 (Bad Request): RentCast could not parse this address format.")
                            elif response.status_code == 404:
                                st.error("Error 404: RentCast found no property records for this address in public tax rolls.")
                            elif response.status_code in [401, 403]:
                                st.error(f"Error {response.status_code}: Unauthorized. Your API Key is invalid or missing.")
                            else:
                                st.error(f"RentCast API Error {response.status_code}.")
                    except Exception as e:
                        st.error(f"Error fetching data: {e}")
                else:
                    st.error("Missing API Key. Paste it in the Configuration box or add RENTCAST_API_KEY to Railway Variables.")

    st.markdown("##### 1. Primary Comp Metrics")
    col_addr, col_price, col_hsf = st.columns([2, 1, 1])

    if comp_entry_mode == "RentCast Live API Fetch":
        comp_address = col_addr.text_input("Comparable Property Address", value=st.session_state.comp_address, disabled=True)
        comp_price = col_price.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, disabled=True)
        comp_heated_sf = col_hsf.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, disabled=True)
    else:
        comp_address = col_addr.text_input("Comparable Property Address", value=st.session_state.comp_address, placeholder="e.g. 16144 South Bud Broussard Road, Prairieville, LA")
        comp_price = col_price.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, step=1000, format="%d")
        comp_heated_sf = col_hsf.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, step=50, format="%d")
        st.session_state.comp_price = comp_price
        st.session_state.comp_heated_sf = comp_heated_sf
        st.session_state.comp_address = comp_address

    st.markdown("##### 2. Comp Auxiliary Spaces (Always Editable)")
    c_aux1, c_aux2, c_aux3, c_aux4 = st.columns(4)
    comp_struct_sf = c_aux1.number_input("Comp Aux. SF (Garage/Carport)", value=200, step=25, format="%d")
    comp_front_sf = c_aux2.number_input("Comp Front Porch SF", value=60, step=10, format="%d")
    comp_back_sf = c_aux3.number_input("Comp Back Porch SF", value=120, step=10, format="%d")
    comp_storage_sf = c_aux4.number_input("Comp Storage Room SF", value=40, step=5, format="%d")


    # ==========================================
    # --- PRE-LEDGER MATH TRANSACTIONS ---
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

    if comp_address:
        st.caption(f"📍 **Active Comp:** {comp_address} | Isolated Heated Rate: **${isolated_heated_rate:.2f} / SF** *(Raw Price/SF: ${raw_comp_price_sf:.2f})*")
    else:
        st.caption(f"📊 Isolated Heated Rate: **${isolated_heated_rate:.2f} / SF** *(Raw Price/SF: ${raw_comp_price_sf:.2f})*")

    # Appraisal & Cost Target Processing
    if appraisal_mode == "Income Approach (GRM)":
        arv_per_unit = (gross_monthly_rent * 12) * target_grm
    else:
        appraised_heated_value = isolated_heated_rate * sqft
        arv_per_unit = appraised_heated_value + our_aux_cost_total

    if cost_calc_mode == "Manual Set (Heated SF)":
        target_heated_hard_cost = base_direct_cost_sf * sqft
        target_total_hard_cost = target_heated_hard_cost + our_aux_cost_total
    elif cost_calc_mode == "Reverse-Engineer from Appraisal":
        target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)
        target_total_hard_cost = arv_per_unit * target_hard_cost_pct
        target_heated_hard_cost = max(0, target_total_hard_cost - our_aux_cost_total)
        base_direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0
    else: # Primary Comp Reverse Engineering
        target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)
        comp_total_hard_budget = comp_price * target_hard_cost_pct
        comp_target_heated_budget = max(0, comp_total_hard_budget - comp_aux_value)
        base_direct_cost_sf = comp_target_heated_budget / comp_heated_sf if comp_heated_sf > 0 else 0
        target_heated_hard_cost = base_direct_cost_sf * sqft
        target_total_hard_cost = target_heated_hard_cost + our_aux_cost_total

    # FIX: Ensure both structure and direct costs are assigned properly for the granular loop
    direct_cost_sf = base_direct_cost_sf
    struct_cost_sf = base_struct_cost_sf

    with st.expander("🧮 View Comp Math Audit & Raw API Data", expanded=False):
        st.markdown("#### The Math Breakdown")
        st.markdown("**1. Raw Retail Heated Rate (Unadjusted)**")
        st.code(f"${comp_price:,.0f} (Sale Price) ÷ {comp_heated_sf:,.0f} (Heated SF) = ${raw_comp_price_sf:.2f} / SF")
        
        st.markdown("**2. True Isolated Heated Shell Rate (Value-Add Extraction)**")
        st.code(f"(${comp_price:,.0f} - ${comp_aux_value:,.0f} Aux Value) ÷ {comp_heated_sf:,.0f} SF = ${isolated_heated_rate:.2f} / SF")
        
        if st.session_state.raw_api_data and comp_entry_mode == "RentCast Live API Fetch":
            st.divider()
            st.markdown("#### 🔍 Raw RentCast API Feed")
            st.json(st.session_state.raw_api_data)

    st.divider()

    # --- RAW GRANULAR DATA ---
    raw_heated_divs = [
        ("DIVISION 1: FOUNDATION & CONCRETE", 9.50, True, ""),
        ("  - Dirtwork, Pad Prep & Formwork", 1.50, False, "Laser leveling, select fill compaction, 2x12 perimeter form boards."),
        ("  - Termiticide & Vapor Barrier", 0.50, False, "Soil pre-treatment chemical barrier and 10-mil poly vapor barrier."),
        ("  - Rebar & Post-Tension Steel", 2.50, False, "Grade 60 rebar footings, welded wire mesh / post-tension cables."),
        ("  - Ready-Mix Concrete & Pumping", 3.50, False, "3,000 PSI ready-mix concrete batching and boom pump truck service."),
        ("  - Slab Placement & Finishing", 1.50, False, "Turnkey concrete crew placement, screeding, power trowel finish."),
        
        ("DIVISION 2: FRAMING & STRUCTURAL SHELL", 18.50, True, ""),
        ("  - Wall Framing Lumber Package", 5.50, False, "2x4 studs @ 16\" OC, treated sole plates, double top plates, LVL headers."),
        ("  - Pre-Engineered Roof Trusses", 4.50, False, "Manufactured gang-nail roof truss package, gable ends, bracing."),
        ("  - Sheathing (Walls & Roof)", 2.50, False, "7/16\" OSB wall sheathing and 7/16\" radiant barrier roof decking."),
        ("  - Structural Hardware & Fasteners", 1.00, False, "Simpson Strong-Tie clips, anchor bolts, framing nails."),
        ("  - Turnkey Framing Labor", 5.00, False, "Piece-rate crew framing walls, setting trusses, sheathing, drying-in."),
        
        ("DIVISION 3: EXTERIOR ENVELOPE & ROOFING", 10.00, True, ""),
        ("  - Architectural Shingle Roofing", 3.25, False, "Lifetime architectural shingles, synthetic underlayment, drip edge."),
        ("  - Vinyl Lap Siding, Soffit & Fascia", 3.00, False, "0.042\" vinyl lap siding, vented vinyl soffits, aluminum fascia wrap."),
        ("  - Windows & Exterior Doors", 2.50, False, "Low-E vinyl single-hung windows; fiberglass insulated exterior doors."),
        ("  - Weatherization & Exterior Labor", 1.25, False, "Housewrap, flashing tape, window/door install, exterior caulk."),

        ("DIVISION 4: MECHANICAL, ELECTRICAL, PLUMBING", 15.50, True, ""),
        ("  - Plumbing Complete (Rough & Trim)", 5.00, False, "Underground PVC, PEX supply, 50-gal water heater, tub/shower, faucets."),
        ("  - HVAC Heat Pump System", 6.00, False, "14.3+ SEER2 heat pump & air handler, R-6 flex ducting, thermostat."),
        ("  - Electrical Rough & Trim", 4.50, False, "200A main service panel, Romex wiring, LED recessed lighting, smoke/CO."),

        ("DIVISION 5: INSULATION & DRYWALL", 6.50, True, ""),
        ("  - Thermal Insulation Package", 2.25, False, "R-13/R-15 kraft-faced wall batts, R-38 blown attic cellulose/fiberglass."),
        ("  - Drywall Materials", 1.75, False, "1/2\" drywall boards (moisture-resistant in wet areas), mud, beads."),
        ("  - Drywall Hanging & Finishing", 2.50, False, "Hang, tape, 3-coat float, sand, spray light texture."),

        ("DIVISION 6: INTERIOR FINISHES & CABINETS", 10.50, True, ""),
        ("  - Interior Doors & Trim Package", 2.50, False, "Hollow-core 6-panel doors, MDF baseboards, casing, hardware."),
        ("  - Cabinetry & Countertops", 4.00, False, "Pre-fab flat panel shaker cabinets, Level 1 laminate/granite."),
        ("  - Flooring (LVP & Carpet)", 2.75, False, "Waterproof click LVP in living/kitchen/baths; carpet in bedrooms."),
        ("  - Interior Paint Labor & Paint", 1.25, False, "Production spray: 1-coat PVA primer, 2-coat wall/ceiling latex."),

        ("DIVISION 7: APPLIANCES & SPECIALTIES", 1.50, True, ""),
        ("  - Kitchen Appliance Suite", 1.10, False, "Stainless/black electric range, microwave, built-in dishwasher."),
        ("  - Bath Hardware & Shelving", 0.40, False, "Wire closet shelving, vanity mirrors, towel bars, paper holders."),

        ("DIVISION 8: EXTERIOR FLATWORK & SITE", 2.00, True, ""),
        ("  - Driveway & Entry Flatwork", 1.25, False, "Broom-finished concrete lead walk and 2-car parking apron."),
        ("  - Final Grading & Starter Sod", 0.75, False, "Tractor rough/finish grade, silt fence, front pallet sod.")
    ]

    raw_struct_divs = [
        ("AUXILIARY: CARPORT / GARAGE", 31.00, True),
        ("  - Slab & Turned-Down Footings", 7.00, False),
        ("  - Framing & Columns", 12.00, False),
        ("  - Roofing & Exterior Trim", 8.00, False),
        ("  - Electrical & Lighting", 2.50, False),
        ("  - Paint & Column Wrap", 1.50, False)
    ]

    # --- GRANULAR HARD COST BUILDUP ---
    st.markdown("### 🧱 Granular Direct Hard Cost Buildup (Trade Divisions)")

    granular_mode = st.radio("Buildup Entry Mode", ["Auto-Proportional (Linked to Master Model)", "Manual Custom Entry (Bottom-Up)"], horizontal=True)

    pdf_granular_data = []

    if granular_mode == "Auto-Proportional (Linked to Master Model)":
        show_sub_items = st.toggle("Show Detailed Sub-Level Trade Itemization", value=False)
        st.markdown(f"#### 1. Heated Living Area ({sqft} SF @ ${direct_cost_sf:.2f} / SF)")
        h_data = {"Division / Trade Level": [], "Live Cost / SF": [], f"Per Unit Cost": [], "Scope Specifications": []}
        for name, base_val, is_header, scope in raw_heated_divs:
            if not show_sub_items and not is_header: continue
            live_sf = direct_cost_sf * (base_val / 74.0)
            h_data["Division / Trade Level"].append(name)
            h_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            h_data[f"Per Unit Cost"].append(f"${live_sf * sqft:,.0f}")
            h_data["Scope Specifications"].append(scope)
            pdf_granular_data.append((name, live_sf, live_sf * sqft, live_sf * sqft * units, is_header))
        st.dataframe(pd.DataFrame(h_data), hide_index=True, use_container_width=True)
        
        st.markdown(f"#### 2. {structure_type} Auxiliary ({struct_sqft} SF @ ${struct_cost_sf:.2f} / SF)")
        s_data = {"Component Level": [], "Live Cost / SF": [], f"Per Unit Cost": []}
        for name, base_val, is_header in raw_struct_divs:
            if not show_sub_items and not is_header: continue
            live_sf = struct_cost_sf * (base_val / 31.0)
            s_data["Component Level"].append(name)
            s_data["Live Cost / SF"].append(f"${live_sf:.2f}")
            s_data["Per Unit Cost"].append(f"${live_sf * struct_sqft:,.0f}")
        st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True)

    else:
        st.markdown(f"#### 1. Heated Living Area ({sqft} SF)")
        hl_heated = [{"Division / Trade Level": name, "Cost / SF": base_direct_cost_sf * (base/74.0), "Scope": scope} for name, base, is_h, scope in raw_heated_divs if is_h]
        edited_h = st.data_editor(pd.DataFrame(hl_heated), column_config={"Division / Trade Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5), "Scope": st.column_config.TextColumn(disabled=True)}, hide_index=True, use_container_width=True, key="manual_heated_editor")
        direct_cost_sf = edited_h["Cost / SF"].sum()
        for index, row in edited_h.iterrows():
            live_sf = row["Cost / SF"]
            pdf_granular_data.append((row["Division / Trade Level"], live_sf, live_sf * sqft, live_sf * sqft * units, True))
        
        st.markdown(f"#### 2. {structure_type} Auxiliary ({struct_sqft} SF)")
        hl_struct = [{"Component Level": name, "Cost / SF": base_struct_cost_sf * (base/31.0)} for name, base, is_h in raw_struct_divs if is_h]
        edited_s = st.data_editor(pd.DataFrame(hl_struct), column_config={"Component Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True, key="manual_struct_editor")
        struct_cost_sf = edited_s["Cost / SF"].sum()

    st.markdown(f"#### 3. Auxiliary, Foundation & Outdoor Living")
    p_data = {
        "Component": ["Front Porch", "Back Porch", "Storage Room", "Addit. Foundation / Elevation", "TOTAL AUX/OUTDOOR"],
        "Area (SF) / Metric": [f"{front_porch_sqft} SF", f"{back_porch_sqft} SF", f"{storage_sqft} SF", "Site Specific", f"{front_porch_sqft + back_porch_sqft + storage_sqft} SF + Site"],
        "Live Cost / SF": [f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", f"${storage_cost_sf:.2f}", "-", "-"],
        "Per Unit Cost": [f"${front_porch_cost:,.0f}", f"${back_porch_cost:,.0f}", f"${storage_cost:,.0f}", f"${additional_foundation_cost:,.0f}", f"${our_aux_cost_total:,.0f}"]
    }
    st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)
    st.divider()


    # --- FINAL MATH & LEDGER UI ---
    total_under_roof_sqft = sqft + struct_sqft + front_porch_sqft + back_porch_sqft + storage_sqft
    heated_hard_cost = sqft * direct_cost_sf

    blended_cost_per_sf = (heated_hard_cost + our_aux_cost_total) / total_under_roof_sqft if total_under_roof_sqft > 0 else 0
    total_hard_cost = target_total_hard_cost * units if cost_calc_mode in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"] else (heated_hard_cost + our_aux_cost_total) * units
    total_arv = arv_per_unit * units
    loan_total = total_arv * refi_ltv

    st.markdown("### 📊 Detailed Construction Cost & Capital Ledger")
    ledger_mode = st.radio("Ledger Input Mode", ["Sync with Global Parameters", "Manual Ledger Override"], horizontal=True)

    st.markdown("#### 1. Direct Hard Costs (Driven by Granular Builder)")
    direct_data = {
        "Cost Category": ["Heated Living Area", f"{structure_type} Auxiliary", "Front Porch", "Back Porch", "Storage Room", "Addit. Foundation / Elevation", "TOTAL DIRECT HARD COSTS"],
        "Area / Metric": [f"{sqft:,.0f} SF", f"{struct_sqft:,.0f} SF", f"{front_porch_sqft:,.0f} SF", f"{back_porch_sqft:,.0f} SF", f"{storage_sqft:,.0f} SF", "Site Specific", f"{total_under_roof_sqft:,.0f} SF Under Roof"],
        "Cost / SF": [f"${direct_cost_sf:.2f}", f"${struct_cost_sf:.2f}", f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", f"${storage_cost_sf:.2f}", "-", f"${blended_cost_per_sf:.2f} (Blended)"],
        "Total Amount ($)": [heated_hard_cost * units, struct_total_cost * units, front_porch_cost * units, back_porch_cost * units, storage_cost * units, additional_foundation_cost * units, total_hard_cost]
    }
    st.dataframe(pd.DataFrame(direct_data).style.format({"Total Amount ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)

    st.markdown("#### 2. Indirect, Land & Capital Costs")
    default_gcond = total_hard_cost * 0.05
    fee_basis = total_hard_cost + default_gcond
    default_gc_fee = custom_gc_fee if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else fee_basis * gc_fee_pct
    default_premium = total_hard_cost * 0.05
    total_land_default = land_basis * units
    default_soft_cost_per_unit = 5500
    total_soft_default = default_soft_cost_per_unit * units

    total_const_default = fee_basis + default_gc_fee + default_premium
    total_project_costs_ex_interest_default = total_land_default + total_const_default + total_soft_default + const_closing_fee
    construction_loan_limit_default = total_project_costs_ex_interest_default * const_ltv
    default_carry_int = construction_loan_limit_default * avg_draw_pct * const_rate * (build_months / 12.0)
    default_buydown_cost = loan_total * (buydown_pts / 100.0) if apply_buydown else 0

    indirects_data = [
        {"Cost Category": "General Conditions", "Metric / Basis": "5.0% of Direct", "Amount ($)": default_gcond},
        {"Cost Category": "GC Management Fee", "Metric / Basis": "Flat Fee" if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else f"{gc_fee_pct*100:.1f}% Basis", "Amount ($)": default_gc_fee},
        {"Cost Category": "BTR Buying Power Premium", "Metric / Basis": "5.0% of Direct", "Amount ($)": default_premium},
        {"Cost Category": "Land Acquisition Basis", "Metric / Basis": f"${land_basis:,.0f} / Lot", "Amount ($)": total_land_default},
        {"Cost Category": "Soft Costs & Permitting", "Metric / Basis": f"${default_soft_cost_per_unit:,.0f} / Unit", "Amount ($)": total_soft_default},
        {"Cost Category": "Construction Loan Closing Fee", "Metric / Basis": "Flat Fee", "Amount ($)": const_closing_fee},
        {"Cost Category": f"Accrued Const. Interest ({build_months} Mos)", "Metric / Basis": f"{avg_draw_pct*100:.0f}% Avg Draw", "Amount ($)": default_carry_int},
        {"Cost Category": "Takeout Refinance Closing Fee", "Metric / Basis": "Flat Fee", "Amount ($)": refi_closing_fee},
        {"Cost Category": "Rate Buydown Points Cost", "Metric / Basis": f"{buydown_pts} Points", "Amount ($)": default_buydown_cost}
    ]
    df_indirects = pd.DataFrame(indirects_data)

    if ledger_mode == "Manual Ledger Override":
        st.caption("✏️ **Manual Mode Active:** Edit the amounts in the table below to override the Master Model.")
        edited_df = st.data_editor(df_indirects, column_config={"Amount ($)": st.column_config.NumberColumn(format="$%.2f", min_value=0.0)}, disabled=["Cost Category", "Metric / Basis"], hide_index=True, use_container_width=True)
        gcond, gc_fee, premium, total_land = edited_df.loc[0, "Amount ($)"], edited_df.loc[1, "Amount ($)"], edited_df.loc[2, "Amount ($)"], edited_df.loc[3, "Amount ($)"]
        total_soft_costs, final_const_closing, carry_int = edited_df.loc[4, "Amount ($)"], edited_df.loc[5, "Amount ($)"], edited_df.loc[6, "Amount ($)"]
        final_refi_closing, total_buydown_cost = edited_df.loc[7, "Amount ($)"], edited_df.loc[8, "Amount ($)"]
    else:
        st.dataframe(df_indirects.style.format({"Amount ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)
        gcond, gc_fee, premium, total_land = default_gcond, default_gc_fee, default_premium, total_land_default
        total_soft_costs, final_const_closing, carry_int = total_soft_default, const_closing_fee, default_carry_int
        final_refi_closing, total_buydown_cost = refi_closing_fee, default_buydown_cost

    total_const = total_hard_cost + gcond + gc_fee + premium
    total_project_costs_ex_interest = total_land + total_const + total_soft_costs + final_const_closing
    total_project_basis = total_project_costs_ex_interest + carry_int + final_refi_closing + total_buydown_cost

    st.markdown(f"### 🎯 TOTAL PROJECT BASIS: **${total_project_basis:,.0f}** *(${total_project_basis/units:,.0f} / Door)*")
    st.divider()

    # --- DSCR CALCULATIONS ---
    total_payments = refi_term_years * 12
    if monthly_interest_rate > 0:
        monthly_pi_per_unit = loan_total / units * (monthly_interest_rate * (1 + monthly_interest_rate)**total_payments) / ((1 + monthly_interest_rate)**total_payments - 1)
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

    cash_surplus = loan_total - total_project_basis
    retained_equity = total_arv - loan_total
    day1_wealth = gc_fee + max(0, cash_surplus) + retained_equity


    # ==========================================
    # --- POPULATE TOP CONTAINERS ---
    # ==========================================

    with ui_top_metrics:
        st.markdown("### 🏗️ Project Capital & Valuation Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Takeout Loan Proceeds", f"${loan_total:,.0f}", f"{refi_ltv*100:.0f}% LTV")
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


    # --- REVERSE ENGINEERING BREAKDOWN & BOTTOM SECTIONS ---
    if cost_calc_mode in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"]:
        st.markdown("### 🔄 Retail Comp & Appraisal Reverse-Engineering Breakdown")
        st.caption(f"Extracting true Heated Construction budget by applying custom standard deductions, isolating fixed auxiliary costs and elevation extras.")
        breakdown_data = {
            "Cost Category": [
                f"Baseline Reference Price (Comp / ARV)", "(-) Finished Lot Cost", "(-) Gross Margin (O&P)", 
                "(-) Sales & Marketing", "(-) Soft Costs & Finance", "= Total Hard Cost Budget", 
                "(-) Fixed Auxiliary & Elevation Costs", "= Available Budget for Heated Shell"
            ],
            "Value ($)": [
                f"${comp_price if cost_calc_mode == 'Reverse-Engineer from Primary Comp' else arv_per_unit:,.0f}", 
                f"-${(comp_price if cost_calc_mode == 'Reverse-Engineer from Primary Comp' else arv_per_unit) * lot_cost_pct:,.0f}", 
                f"-${(comp_price if cost_calc_mode == 'Reverse-Engineer from Primary Comp' else arv_per_unit) * margin_pct:,.0f}", 
                f"-${(comp_price if cost_calc_mode == 'Reverse-Engineer from Primary Comp' else arv_per_unit) * sales_pct:,.0f}", 
                f"-${(comp_price if cost_calc_mode == 'Reverse-Engineer from Primary Comp' else arv_per_unit) * finance_pct:,.0f}", 
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
                "Locked budget required for your specific outdoor/auxiliary footprint and foundation elevation.",
                f"Yields exactly ${base_direct_cost_sf:.2f} / SF across {sqft} Heated SF."
            ]
        }
        st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)
        st.divider()

    st.markdown("### 💰 Day-1 Wealth Creation")
    wealth_data = {
        "Pocket Component": ["Pocket 1: Active GC Fee Revenue", "Pocket 2: Tax-Free Cash Surplus at Close", "Pocket 3: Retained Asset Equity", "TOTAL DAY-1 CREATED VALUE"],
        "Value ($)": [gc_fee, cash_surplus, retained_equity, day1_wealth]
    }
    df_wealth = pd.DataFrame(wealth_data)
    df_wealth['Value ($)'] = df_wealth['Value ($)'].apply(lambda x: f"${x:,.0f}")
    st.dataframe(df_wealth, hide_index=True, use_container_width=True)

    if cash_surplus >= 0:
        st.success(f"**Infinite Cash-on-Cash Return Achieved:** You have recovered 100% of your seed capital plus an additional ${cash_surplus:,.0f} in liquid cash.")
    else:
        st.error(f"**Capital Trapped:** You are leaving ${abs(cash_surplus):,.0f} of your seed capital in the deal to close the takeout loan.")
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
        pdf.cell(0, 8, " 2. Operating Performance & DSCR (Annualized)", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(100, 7, "Gross Potential Rent (GPR):", 0, 0)
        pdf.cell(90, 7, f"${total_gross_monthly_income * 12:,.2f}", 0, 1, 'R')
        pdf.cell(100, 7, f"(-) Vacancy Loss ({vacancy_rate*100:.1f}%):", 0, 0)
        pdf.cell(90, 7, f"-${annual_vacancy_loss:,.2f}", 0, 1, 'R')
        pdf.cell(100, 7, "= Effective Gross Income (EGI):", 0, 0)
        pdf.cell(90, 7, f"${annual_egi:,.2f}", 0, 1, 'R')
        pdf.cell(100, 7, f"(-) Operating Expenses ({opex_rate*100:.1f}% EGI):", 0, 0)
        pdf.cell(90, 7, f"-${annual_opex:,.2f}", 0, 1, 'R')
        pdf.cell(100, 7, "= Net Operating Income (NOI):", 0, 0)
        pdf.cell(90, 7, f"${annual_noi:,.2f}", 0, 1, 'R')
        pdf.cell(100, 7, "(-) Total Debt Service (P&I):", 0, 0)
        pdf.cell(90, 7, f"-${annual_debt_service:,.2f}", 0, 1, 'R')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(100, 7, "= Net Cash Flow:", 0, 0)
        pdf.cell(90, 7, f"${monthly_cash_flow * 12:,.2f}", 0, 1, 'R')
        pdf.cell(100, 7, "Actual DSCR Rate:", 0, 0)
        pdf.cell(90, 7, f"{actual_dscr:.2f}x (Variance: {dscr_variance:+.2f}x)", 0, 1, 'R')
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, " 3. Detailed Construction Cost Breakdown", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        
        pdf.cell(100, 7, "Total Direct Hard Costs:", 0, 0)
        pdf.cell(90, 7, f"${total_hard_cost:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, "Indirect General Conditions & Premiums:", 0, 0)
        pdf.cell(90, 7, f"${gcond + premium:,.0f}", 0, 1, 'R')
        
        gc_label = "Consolidated GC Flat Fee:" if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else f"GC Management Fee:"
        pdf.cell(100, 7, gc_label, 0, 0)
        pdf.cell(90, 7, f"${gc_fee:,.0f}", 0, 1, 'R')
        
        pdf.cell(100, 7, "Land Acquisition Basis:", 0, 0)
        pdf.cell(90, 7, f"${total_land:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, "Accrued Construction Loan Interest:", 0, 0)
        pdf.cell(90, 7, f"${carry_int:,.0f}", 0, 1, 'R')
        pdf.cell(100, 7, "Total Soft Costs & Closing Fees:", 0, 0)
        pdf.cell(90, 7, f"${total_soft_costs + final_const_closing + final_refi_closing + total_buydown_cost:,.0f}", 0, 1, 'R')
        
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
                if not include_sublevels and not is_header:
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
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            with open(tmp.name, "rb") as f:
                return f.read()

    with download_placeholder:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📄 Download Enterprise Report (PDF)",
            data=create_pdf(pdf_include_sublevels),
            file_name=f"Wickboldt_Capital_ProForma_{report_date.replace(' ', '_').replace(',', '')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
