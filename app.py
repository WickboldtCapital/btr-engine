import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import requests
import os
import re
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Wickboldt Capital | BTR Pro Forma Engine", layout="wide")

st.title("🏗️ BTR Pro Forma Engine")
st.markdown("### Wickboldt Capital — *Today's Foundation. Tomorrow's Legacy.*")
st.divider()

# --- PROJECT IDENTIFICATION & EXPORT ---
st.markdown("### 📋 Project Information")

top_col1, top_col2, top_col3 = st.columns([2, 2, 1])

project_name = top_col1.text_input("Project Title", placeholder="e.g. Phase 1 - 24-Lot Build-to-Rent")
project_address = top_col2.text_input("Project Address", placeholder="e.g. Rogers Moore Parkway, Hammond, LA")
report_date = datetime.now().strftime("%B %d, %Y")

download_placeholder = top_col3.empty()

st.divider()

# --- COMPARABLE MARKET ANALYSIS (COMP BENCHMARK TOOL) ---
st.markdown("### 🔍 Market Comp Valuation & Blended Rate Benchmark")
st.markdown("Input market comparable data below. This dynamically sets the Appraised Value (ARV) and drives the Retail Reverse-Engineering cost basis.")

# 1. Initialize session state variables
if "comp_address" not in st.session_state:
    st.session_state.comp_address = ""
if "comp_price" not in st.session_state:
    st.session_state.comp_price = 182600
if "comp_heated_sf" not in st.session_state:
    st.session_state.comp_heated_sf = 1150
if "raw_api_data" not in st.session_state:
    st.session_state.raw_api_data = None

# 2. Toggle Mode
comp_entry_mode = st.radio(
    "Comparable Data Entry Mode", 
    [
        "Manual Entry", 
        "RentCast Live API Fetch"
    ], 
    horizontal=True
)

if comp_entry_mode == "RentCast Live API Fetch":
    
    rc_col1, rc_col2 = st.columns([4, 1])
    search_address = rc_col1.text_input("Property Address", placeholder="e.g. 1103 S Spruce St, Hammond, LA")
    
    with st.expander("⚙️ API Configuration (Optional)"):
        st.caption("If Railway hasn't loaded your key yet, paste it here to test immediately.")
        manual_key = st.text_input("RentCast API Key Override", type="password")

    if rc_col2.button("Fetch Live Data", use_container_width=True):
        if search_address:
            rentcast_key = manual_key or os.environ.get("RENTCAST_API_KEY") or st.secrets.get("RENTCAST_API_KEY", "")
            
            if rentcast_key:
                try:
                    with st.spinner("Fetching live data from RentCast MLS..."):
                        api_url = "https://api.rentcast.io/v1/properties"
                        querystring = {"address": search_address}
                        headers = {
                            "X-Api-Key": rentcast_key,
                            "accept": "application/json"
                        }
                        
                        response = requests.get(api_url, headers=headers, params=querystring)
                        
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
                                            avm_data = avm_res.json()
                                            fetched_price = avm_data.get("price")
                                    except:
                                        pass
                                
                                if fetched_price: st.session_state.comp_price = int(fetched_price)
                                if fetched_sf: st.session_state.comp_heated_sf = int(fetched_sf)
                                if fetched_addr: st.session_state.comp_address = str(fetched_addr)
                                
                                st.success(f"Property successfully imported: {st.session_state.comp_address}")
                                st.rerun()
                            else:
                                st.error("No exact match found. Make sure the address is formatted perfectly (e.g., '1103 S Spruce St, Hammond, LA').")
                        else:
                            st.error(f"RentCast API Error {response.status_code}. Your API Key may be invalid.")
                except Exception as e:
                    st.error(f"Error fetching data: {e}")
            else:
                st.error("Missing API Key. Paste it in the Configuration box or add RENTCAST_API_KEY to Railway Variables.")
            
    st.info("💡 RentCast Mode is active. Address, Price, and Heated SF are locked to the fetched data. Switch to 'Manual Entry' to edit them.")
    comp_address = st.text_input("Comparable Property Address", value=st.session_state.comp_address, disabled=True)
    cc_col1, cc_col2, cc_col3, cc_col4, cc_col5 = st.columns(5)
    comp_price = cc_col1.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, disabled=True)
    comp_heated_sf = cc_col2.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, disabled=True)

else:
    comp_address = st.text_input("Comparable Property Address", value=st.session_state.comp_address, placeholder="e.g. 16144 South Bud Broussard Road, Prairieville, LA")
    cc_col1, cc_col2, cc_col3, cc_col4, cc_col5 = st.columns(5)
    comp_price = cc_col1.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, step=1000, format="%d")
    comp_heated_sf = cc_col2.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, step=50, format="%d")
    
    st.session_state.comp_price = comp_price
    st.session_state.comp_heated_sf = comp_heated_sf
    st.session_state.comp_address = comp_address


# --- SIDEBAR: MASTER MODEL DRIVERS ---
st.sidebar.header("Master Model Drivers")

st.sidebar.subheader("1. Project Scale & Rents")
units = st.sidebar.number_input("Number of Units (Doors)", min_value=1, value=1, step=1, format="%d")
gross_monthly_rent = st.sidebar.number_input("Gross Monthly Rental Income per Unit ($)", value=1650, step=50, format="%d")

st.sidebar.subheader("2. Physical Footprint & Aux Costs")
sqft = st.sidebar.number_input("Heated SqFt per Unit", value=1150, step=50, format="%d")

structure_type = st.sidebar.selectbox("Aux Structure Type", ["Carport", "Garage"])
struct_sqft = st.sidebar.number_input(f"{structure_type} SqFt per Unit", value=200, step=25, format="%d")
base_struct_cost_sf = st.sidebar.slider(f"{structure_type} Cost / SF ($)", min_value=15.0, max_value=90.0, value=31.0 if structure_type == "Carport" else 55.0, step=1.0)

front_porch_sqft = st.sidebar.number_input("Front Porch SqFt", value=60, step=10, format="%d")
front_porch_cost_sf = st.sidebar.slider("Front Porch Cost / SF ($)", min_value=15.0, max_value=70.0, value=35.0, step=1.0)

back_porch_sqft = st.sidebar.number_input("Back Porch SqFt", value=120, step=10, format="%d")
back_porch_cost_sf = st.sidebar.slider("Back Porch Cost / SF ($)", min_value=15.0, max_value=70.0, value=35.0, step=1.0)

struct_total_cost = struct_sqft * base_struct_cost_sf
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf
our_aux_cost_total = struct_total_cost + front_porch_cost + back_porch_cost

comp_struct_sf = cc_col3.number_input("Comp Aux. SF (Garage)", value=200, step=25, format="%d")
comp_front_sf = cc_col4.number_input("Comp Front Porch SF", value=60, step=10, format="%d")
comp_back_sf = cc_col5.number_input("Comp Back Porch SF", value=120, step=10, format="%d")

comp_total_sf = comp_heated_sf + comp_struct_sf + comp_front_sf + comp_back_sf
raw_comp_price_sf = comp_price / comp_heated_sf if comp_heated_sf > 0 else 0
comp_aux_value = (comp_struct_sf * base_struct_cost_sf) + (comp_front_sf * front_porch_cost_sf) + (comp_back_sf * back_porch_cost_sf)
comp_isolated_heated_value = max(0, comp_price - comp_aux_value)
isolated_heated_rate = comp_isolated_heated_value / comp_heated_sf if comp_heated_sf > 0 else 0


if comp_address:
    st.caption(f"📍 **Active Comp:** {comp_address} | Isolated Heated Rate: **${isolated_heated_rate:.2f} / SF** *(Raw Price/SF: ${raw_comp_price_sf:.2f})*")
else:
    st.caption(f"📊 Isolated Heated Rate: **${isolated_heated_rate:.2f} / SF** *(Raw Price/SF: ${raw_comp_price_sf:.2f})*")


st.sidebar.subheader("3. Takeout Appraisal Methodology")
appraisal_mode = st.sidebar.radio("Valuation Mode", ["Sales Comp (Price/SF)", "Income Approach (GRM)"])
if appraisal_mode == "Income Approach (GRM)":
    target_grm = st.sidebar.number_input("Gross Rent Multiplier (GRM)", min_value=4.0, max_value=25.0, value=10.5, step=0.1)
    arv_per_unit = (gross_monthly_rent * 12) * target_grm
    st.sidebar.success(f"📈 **Calculated Unit ARV:** ${arv_per_unit:,.0f}")
else:
    target_grm = 0.0
    appraised_heated_value = isolated_heated_rate * sqft
    arv_per_unit = appraised_heated_value + our_aux_cost_total
    st.sidebar.success(f"📈 **Calculated Unit ARV:** ${arv_per_unit:,.0f}")


st.sidebar.subheader("4. Cost Target Mode (Reverse Engineer)")
cost_calc_mode = st.sidebar.radio(
    "Calculation Logic", 
    [
        "Manual Set (Heated SF)", 
        "Reverse-Engineer from Appraisal"
    ]
)

if cost_calc_mode == "Manual Set (Heated SF)":
    base_direct_cost_sf = st.sidebar.slider("Direct Build Cost / SF ($)", min_value=40.0, max_value=150.0, value=74.0, step=1.0)
    target_heated_hard_cost = base_direct_cost_sf * sqft
    lot_cost_pct = 0.18; margin_pct = 0.20; sales_pct = 0.08; finance_pct = 0.04 
    target_total_hard_cost = target_heated_hard_cost + our_aux_cost_total
else:
    st.sidebar.caption(f"Extracting Target Direct Costs from Unit ARV (${arv_per_unit:,.0f}).")
    lot_cost_pct = st.sidebar.slider("Finished Lot Cost (%)", min_value=0.0, max_value=30.0, value=18.0, step=0.5) / 100.0
    margin_pct = st.sidebar.slider("Gross Margin (O&P) (%)", min_value=0.0, max_value=30.0, value=20.0, step=0.5) / 100.0
    sales_pct = st.sidebar.slider("Sales & Marketing (%)", min_value=0.0, max_value=15.0, value=8.0, step=0.5) / 100.0
    finance_pct = st.sidebar.slider("Soft Costs & Finance (%)", min_value=0.0, max_value=15.0, value=4.0, step=0.5) / 100.0
    
    target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)
    target_total_hard_cost = arv_per_unit * target_hard_cost_pct
    target_heated_hard_cost = max(0, target_total_hard_cost - our_aux_cost_total)
    base_direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0
    st.sidebar.success(f"**Target Heated Cost:**\n${base_direct_cost_sf:.2f} / SF")

st.sidebar.subheader("5. GC Fee, Land & Soft Costs")
gc_fee_mode = st.sidebar.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"])
if gc_fee_mode == "Percentage of Hard Costs (%)":
    gc_fee_pct = st.sidebar.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, value=10.0, step=0.5) / 100.0
    custom_gc_fee = 0
else:
    custom_gc_fee = st.sidebar.number_input("Total Consolidated GC Fee ($)", value=20000, step=1000, format="%d")
    gc_fee_pct = 0.0

land_basis = st.sidebar.number_input("Land Basis per Lot ($)", value=15000, step=1000, format="%d")
soft_costs = st.sidebar.number_input("Soft Costs per Unit ($)", value=5500, step=500, format="%d")

st.sidebar.subheader("6. Financing & Operations")
const_ltv = st.sidebar.slider("Construction Loan LTV (%)", min_value=60.0, max_value=100.0, value=85.0, step=5.0) / 100.0
build_months = st.sidebar.slider("Construction Duration (Months)", min_value=3, max_value=18, value=9, step=1)
const_rate = st.sidebar.slider("Construction Loan Rate (%)", min_value=4.0, max_value=14.0, value=8.5, step=0.5) / 100.0
avg_draw_pct = st.sidebar.slider("Average Draw / Principal Utilization Rate (%)", min_value=20.0, max_value=100.0, value=50.0, step=5.0) / 100.0
const_closing_fee = st.sidebar.number_input("Construction Loan Closing Fee ($ total)", value=6000, step=500, format="%d")

refi_ltv = st.sidebar.slider("Refinance LTV (%)", min_value=60.0, max_value=85.0, value=80.0, step=5.0) / 100.0
refi_term_years = st.sidebar.selectbox("Amortization Term (Years)", [15, 20, 25, 30], index=3)
base_refi_rate = st.sidebar.slider("Base Refi Interest Rate (%)", min_value=4.0, max_value=10.0, value=6.5, step=0.25) / 100.0
refi_closing_fee = st.sidebar.number_input("Refinance Closing Fee ($ total)", value=3650, step=250, format="%d")

apply_buydown = st.sidebar.checkbox("Apply Interest Rate Buydown Points?")
buydown_pts = 0.0
net_refi_rate = base_refi_rate
if apply_buydown:
    buydown_pts = st.sidebar.number_input("Discount Points (1 pt = 1% of Loan)", min_value=0.0, max_value=5.0, value=2.0, step=0.5)
    rate_reduction = buydown_pts * 0.0025  
    net_refi_rate = max(0.01, base_refi_rate - rate_reduction)
    st.sidebar.markdown(f"📉 **Buydown Net Rate:** `{net_refi_rate*100:.3f}%`")

target_dscr_rate = st.sidebar.number_input("Target Lender DSCR Rate", min_value=1.0, max_value=1.5, value=1.20, step=0.05)
vacancy_rate = st.sidebar.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, value=5.0, step=1.0) / 100.0
opex_rate = st.sidebar.slider("Operating Expenses (OpEx) Rate of EGI (%)", min_value=15.0, max_value=50.0, value=30.0, step=1.0) / 100.0

st.sidebar.subheader("PDF Export Options")
pdf_include_sublevels = st.sidebar.checkbox("Include Detailed Sub-Levels in PDF Report", value=True)


# --- DYNAMIC UI PLACEHOLDERS ---
ui_top_metrics = st.container()
ui_op_metrics = st.container()
st.divider()
ui_rev_eng = st.container()
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
    st.caption("Budget dynamically scales proportionally based on your active Direct Cost / SF and the Wickboldt Capital baseline document weightings.")
    direct_cost_sf = base_direct_cost_sf
    struct_cost_sf = base_struct_cost_sf

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
        s_data[f"Per Unit Cost"].append(f"${live_sf * struct_sqft:,.0f}")
    st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True)

else:
    st.caption("Enter your custom $ / SF for each trade division below. Your inputs will sum together to automatically override the Master Model.")
    st.markdown(f"#### 1. Heated Living Area ({sqft} SF)")
    hl_heated = [{"Division / Trade Level": name, "Cost / SF": base_direct_cost_sf * (base/74.0), "Scope": scope} for name, base, is_h, scope in raw_heated_divs if is_h]
    edited_h = st.data_editor(pd.DataFrame(hl_heated), column_config={"Division / Trade Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5), "Scope": st.column_config.TextColumn(disabled=True)}, hide_index=True, use_container_width=True, key="manual_heated_editor")
    direct_cost_sf = edited_h["Cost / SF"].sum()
    st.success(f"**Calculated Manual Direct Cost:** ${direct_cost_sf:.2f} / SF")
    for index, row in edited_h.iterrows():
        live_sf = row["Cost / SF"]
        pdf_granular_data.append((row["Division / Trade Level"], live_sf, live_sf * sqft, live_sf * sqft * units, True))
    
    st.markdown(f"#### 2. {structure_type} Auxiliary ({struct_sqft} SF)")
    hl_struct = [{"Component Level": name, "Cost / SF": base_struct_cost_sf * (base/31.0)} for name, base, is_h in raw_struct_divs if is_h]
    edited_s = st.data_editor(pd.DataFrame(hl_struct), column_config={"Component Level": st.column_config.TextColumn(disabled=True), "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)}, hide_index=True, use_container_width=True, key="manual_struct_editor")
    struct_cost_sf = edited_s["Cost / SF"].sum()

st.markdown(f"#### 3. Porches & Outdoor Living ({front_porch_sqft + back_porch_sqft} Total SF)")
p_data = {
    "Component": ["Front Porch", "Back Porch", "TOTAL PORCHES"],
    "Area (SF)": [f"{front_porch_sqft} SF", f"{back_porch_sqft} SF", f"{front_porch_sqft + back_porch_sqft} SF"],
    "Live Cost / SF": [f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", "-"],
    "Per Unit Cost": [f"${front_porch_cost:,.0f}", f"${back_porch_cost:,.0f}", f"${front_porch_cost + back_porch_cost:,.0f}"]
}
st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)

st.divider()

# --- PRE-LEDGER MATH (Direct Hard Costs) ---
total_under_roof_sqft = sqft + struct_sqft + front_porch_sqft + back_porch_sqft
struct_total_cost = struct_sqft * struct_cost_sf
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf

heated_hard_cost = sqft * direct_cost_sf
hard_cost_per_unit = heated_hard_cost + struct_total_cost + front_porch_cost + back_porch_cost
blended_cost_per_sf = hard_cost_per_unit / total_under_roof_sqft if total_under_roof_sqft > 0 else 0
total_hard_cost = hard_cost_per_unit * units
total_arv = arv_per_unit * units
loan_total = total_arv * refi_ltv


# --- DYNAMIC LEDGER UI ---
st.markdown("### 📊 Detailed Construction Cost & Capital Ledger")
ledger_mode = st.radio("Ledger Input Mode", ["Sync with Global Parameters", "Manual Ledger Override"], horizontal=True)

st.markdown("#### 1. Direct Hard Costs (Driven by Granular Builder)")
direct_data = {
    "Cost Category": ["Heated Living Area", f"{structure_type} Auxiliary", "Front Porch", "Back Porch", "TOTAL DIRECT HARD COSTS"],
    "Area / Metric": [f"{sqft:,.0f} SF", f"{struct_sqft:,.0f} SF", f"{front_porch_sqft:,.0f} SF", f"{back_porch_sqft:,.0f} SF", f"{total_under_roof_sqft:,.0f} SF Under Roof"],
    "Cost / SF": [f"${direct_cost_sf:.2f}", f"${struct_cost_sf:.2f}", f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", f"${blended_cost_per_sf:.2f} (Blended)"],
    "Total Amount ($)": [heated_hard_cost * units, struct_total_cost * units, front_porch_cost * units, back_porch_cost * units, total_hard_cost]
}
st.dataframe(pd.DataFrame(direct_data).style.format({"Total Amount ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)


st.markdown("#### 2. Indirect, Land & Capital Costs")
# Pre-calculate Master Model defaults
default_gcond = total_hard_cost * 0.05
fee_basis = total_hard_cost + default_gcond
default_gc_fee = custom_gc_fee if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else fee_basis * gc_fee_pct
default_premium = total_hard_cost * 0.05
total_land_default = land_basis * units
total_soft_default = soft_costs * units

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
    {"Cost Category": "Soft Costs & Permitting", "Metric / Basis": f"${soft_costs:,.0f} / Unit", "Amount ($)": total_soft_default},
    {"Cost Category": "Construction Loan Closing Fee", "Metric / Basis": "Flat Fee", "Amount ($)": const_closing_fee},
    {"Cost Category": f"Accrued Const. Interest ({build_months} Mos)", "Metric / Basis": f"{avg_draw_pct*100:.0f}% Avg Draw", "Amount ($)": default_carry_int},
    {"Cost Category": "Takeout Refinance Closing Fee", "Metric / Basis": "Flat Fee", "Amount ($)": refi_closing_fee},
    {"Cost Category": "Rate Buydown Points Cost", "Metric / Basis": f"{buydown_pts} Points", "Amount ($)": default_buydown_cost}
]
df_indirects = pd.DataFrame(indirects_data)

if ledger_mode == "Manual Ledger Override":
    st.caption("✏️ **Manual Mode Active:** Edit the amounts in the table below to override the Master Model.")
    edited_df = st.data_editor(
        df_indirects,
        column_config={"Amount ($)": st.column_config.NumberColumn(format="$%.2f", min_value=0.0)},
        disabled=["Cost Category", "Metric / Basis"],
        hide_index=True,
        use_container_width=True
    )
    gcond = edited_df.loc[0, "Amount ($)"]
    gc_fee = edited_df.loc[1, "Amount ($)"]
    premium = edited_df.loc[2, "Amount ($)"]
    total_land = edited_df.loc[3, "Amount ($)"]
    total_soft_costs = edited_df.loc[4, "Amount ($)"]
    final_const_closing = edited_df.loc[5, "Amount ($)"]
    carry_int = edited_df.loc[6, "Amount ($)"]
    final_refi_closing = edited_df.loc[7, "Amount ($)"]
    total_buydown_cost = edited_df.loc[8, "Amount ($)"]
else:
    st.dataframe(df_indirects.style.format({"Amount ($)": "${:,.0f}"}), hide_index=True, use_container_width=True)
    gcond = default_gcond
    gc_fee = default_gc_fee
    premium = default_premium
    total_land = total_land_default
    total_soft_costs = total_soft_default
    final_const_closing = const_closing_fee
    carry_int = default_carry_int
    final_refi_closing = refi_closing_fee
    total_buydown_cost = default_buydown_cost

# Finalize the TRUE Project Basis with whatever values came out of the Ledger UI above!
total_const = total_hard_cost + gcond + gc_fee + premium
total_project_costs_ex_interest = total_land + total_const + total_soft_costs + final_const_closing
total_project_basis = total_project_costs_ex_interest + carry_int + final_refi_closing + total_buydown_cost

st.markdown(f"### 🎯 TOTAL PROJECT BASIS: **${total_project_basis:,.0f}** *(${total_project_basis/units:,.0f} / Door)*")
st.divider()


# --- POST-LEDGER OPERATIONS & DSCR CALCULATIONS ---
monthly_interest_rate = net_refi_rate / 12.0
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


# --- RENDER TOP PLACEHOLDERS (Now populated with post-ledger calculations) ---
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

with ui_rev_eng:
    if cost_calc_mode == "Reverse-Engineer from Appraisal":
        st.markdown("### 🔄 Retail Appraisal Reverse-Engineering Breakdown")
        st.caption(f"Extracting true Heated Construction budget by applying custom standard deductions to your Appraised Unit Value of **${arv_per_unit:,.0f}**, and isolating fixed auxiliary costs.")
        breakdown_data = {
            "Cost Category": [
                f"Target Appraised Value (ARV) per Unit",
                "(-) Finished Lot Cost",
                "(-) Gross Margin (O&P)",
                "(-) Sales & Marketing",
                "(-) Soft Costs & Finance",
                "= Total Hard Cost Budget",
                "(-) Fixed Auxiliary Costs (Carport/Porches)",
                "= Available Budget for Heated Shell"
            ],
            "Value ($)": [
                f"${arv_per_unit:,.0f}",
                f"-${arv_per_unit * lot_cost_pct:,.0f}",
                f"-${arv_per_unit * margin_pct:,.0f}",
                f"-${arv_per_unit * sales_pct:,.0f}",
                f"-${arv_per_unit * finance_pct:,.0f}",
                f"${target_total_hard_cost:,.0f}",
                f"-${our_aux_cost_total:,.0f}",
                f"${target_heated_hard_cost:,.0f}"
            ],
            "Description": [
                "Based on your selected Appraisal Methodology.",
                "Raw land, engineering, road paving, wet/dry utility infrastructure.",
                "Builder gross overhead and corporate net margin.",
                "Realtor commissions, internal sales reps, buyer closing concessions.",
                "Impact fees, plan design, municipal permits, and loan interest carry.",
                "Total budget available for all physical construction.",
                "Locked budget required for your specific outdoor/auxiliary footprint.",
                f"Yields exactly ${base_direct_cost_sf:.2f} / SF across {sqft} Heated SF."
            ]
        }
        st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)


# --- WEALTH & DSCR SECTIONS (Rendered at the bottom) ---
ui_wealth = st.container()
with ui_wealth:
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
        st.error(f"**Capital Trapped:** You are leaving ${abs(cash_surplus):,.0f} of your seed capital in the deal to close the takeout loan. Try lowering your Direct Build Cost / SF or reducing the construction timeline.")
    st.divider()

ui_dscr = st.container()
with ui_dscr:
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
            f"-${annual_opex:,.2f}", f"${annual_noi:,.2f}", f"-${annual_debt_service:,.2f}", f"${monthly_cash_flow * 12:,.2f}",
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
    pdf.cell(0, 6, f"Scale: {units} Unit(s) | Under-Roof: {total_under_roof_sqft:,} SF/Unit", ln=1)
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
