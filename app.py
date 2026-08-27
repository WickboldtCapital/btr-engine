import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
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

# 1. Initialize session state variables so the Zillow button can automatically update them
if "comp_address" not in st.session_state:
    st.session_state.comp_address = ""
if "comp_price" not in st.session_state:
    st.session_state.comp_price = 182600
if "comp_heated_sf" not in st.session_state:
    st.session_state.comp_heated_sf = 1150

# 2. Toggle Mode
comp_entry_mode = st.radio(
    "Comparable Data Entry Mode", 
    ["Manual Entry", "Zillow Auto-Fetch (API)"], 
    horizontal=True
)

if comp_entry_mode == "Zillow Auto-Fetch (API)":
    z_col1, z_col2 = st.columns([4, 1])
    zillow_url = z_col1.text_input("Zillow Listing URL (Requires API Key)", placeholder="Paste Zillow URL here (e.g. https://www.zillow.com/homedetails/...)")

    if z_col2.button("Fetch Zillow Data", use_container_width=True):
        if zillow_url:
            # -------------------------------------------------------------------------
            # LIVE API CODE: 
            # When you add your RapidAPI key to Railway, delete the triple quotes (''') 
            # around this block and delete the MOCK DATA block below.
            # -------------------------------------------------------------------------
            '''
            import requests
            import json
            
            rapidapi_key = st.secrets.get("RAPIDAPI_KEY", "")
            if rapidapi_key:
                try:
                    # ---> 1. REPLACE THIS URL WITH THE ONE FROM YOUR RAPIDAPI SNIPPET <---
                    api_url = "https://zillow-com-realtime-scraper.p.rapidapi.com/property" 
                    
                    querystring = {"url": zillow_url} 
                    
                    headers = {
                        "X-RapidAPI-Key": rapidapi_key,
                        # ---> 2. REPLACE THIS HOST WITH THE ONE FROM YOUR RAPIDAPI SNIPPET <---
                        "X-RapidAPI-Host": "zillow-com-realtime-scraper.p.rapidapi.com"
                    }
                    
                    response = requests.get(api_url, headers=headers, params=querystring)
                    if response.status_code == 200:
                        data = response.json()
                        
                        st.session_state.comp_price = data.get("price") or data.get("zestimate") or 182600
                        st.session_state.comp_heated_sf = data.get("livingArea") or data.get("livingAreaValue") or data.get("sqft") or 1150
                        
                        addr = data.get("address", {})
                        if isinstance(addr, dict):
                            st.session_state.comp_address = f"{addr.get('streetAddress', '')}, {addr.get('city', '')}, {addr.get('state', '')}"
                        else:
                            st.session_state.comp_address = str(addr)
                            
                        st.success("Listing successfully imported!")
                        st.rerun()
                    else:
                        st.error(f"Failed to fetch data. Code: {response.status_code}")
                except Exception as e:
                    st.error(f"Error fetching data: {e}")
            else:
                st.error("Missing RAPIDAPI_KEY in environment variables.")
            '''

            # MOCK DATA FOR DEMONSTRATION (Delete this block when you uncomment the live code above)
            st.toast("Zillow API Key not detected. Injecting simulated listing data...")
            st.session_state.comp_address = "123 Simulated Zillow Listing, Hammond, LA"
            st.session_state.comp_price = 245000
            st.session_state.comp_heated_sf = 1450
            st.rerun()
            
    st.info("💡 Zillow Mode is active. Address, Price, and Heated SF are locked to the scraped data. Switch to 'Manual Entry' to edit them.")
    
    comp_address = st.text_input("Comparable Property Address", value=st.session_state.comp_address, disabled=True)
    cc_col1, cc_col2, cc_col3, cc_col4, cc_col5 = st.columns(5)
    comp_price = cc_col1.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, disabled=True)
    comp_heated_sf = cc_col2.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, disabled=True)

else:
    comp_address = st.text_input("Comparable Property Address", value=st.session_state.comp_address, placeholder="e.g. 16144 South Bud Broussard Road, Prairieville, LA")
    cc_col1, cc_col2, cc_col3, cc_col4, cc_col5 = st.columns(5)
    comp_price = cc_col1.number_input("Comp Sale Price ($)", value=st.session_state.comp_price, step=1000, format="%d")
    comp_heated_sf = cc_col2.number_input("Comp Heated SF", value=st.session_state.comp_heated_sf, step=50, format="%d")
    
    # Save manual typing to session state so it doesn't revert
    st.session_state.comp_price = comp_price
    st.session_state.comp_heated_sf = comp_heated_sf
    st.session_state.comp_address = comp_address

# Auxiliary details are always editable because Zillow doesn't provide them reliably
comp_struct_sf = cc_col3.number_input("Comp Aux. SF (Garage)", value=200, step=25, format="%d")
comp_front_sf = cc_col4.number_input("Comp Front Porch SF", value=60, step=10, format="%d")
comp_back_sf = cc_col5.number_input("Comp Back Porch SF", value=120, step=10, format="%d")

comp_total_sf = comp_heated_sf + comp_struct_sf + comp_front_sf + comp_back_sf
comp_blended_cost = comp_price / comp_total_sf if comp_total_sf > 0 else 0

if comp_address:
    st.caption(f"📍 **Active Comp:** {comp_address} | Comp Retail Blended Rate: **${comp_blended_cost:.2f} / SF**")
else:
    st.caption(f"📊 Comp Retail Blended Rate: **${comp_blended_cost:.2f} / SF**")

st.divider()

# --- SIDEBAR: MASTER MODEL DRIVERS ---
st.sidebar.header("Master Model Drivers")

st.sidebar.subheader("Project Scale & GC Fee Structure")
units = st.sidebar.number_input("Number of Units (Doors)", min_value=1, value=1, step=1, format="%d")

gc_fee_mode = st.sidebar.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"])
if gc_fee_mode == "Percentage of Hard Costs (%)":
    gc_fee_pct = st.sidebar.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, value=10.0, step=0.5) / 100.0
    custom_gc_fee = 0
else:
    custom_gc_fee = st.sidebar.number_input("Total Consolidated GC Fee ($)", value=20000, step=1000, format="%d")
    gc_fee_pct = 0.0

st.sidebar.subheader("Construction Costs (Heated Area)")
sqft = st.sidebar.number_input("Heated SqFt per Unit", value=1150, step=50, format="%d")

cost_calc_mode = st.sidebar.radio(
    "Cost Calculation Mode", 
    [
        "Manual Set (Heated SF)", 
        "Reverse-Engineer from Comp (Adjustable Breakdown)"
    ]
)

if cost_calc_mode == "Manual Set (Heated SF)":
    base_direct_cost_sf = st.sidebar.slider("Direct Build Cost / SF ($)", min_value=40.0, max_value=150.0, value=74.0, step=1.0)
else:
    st.sidebar.caption("Retail Price / SF is dynamically derived from your Market Comp inputs.")
    retail_price_sf = comp_blended_cost
    st.sidebar.markdown(f"**Comp Retail Price:** `${retail_price_sf:.2f} / SF`")
    
    st.sidebar.markdown("**Adjustable Deductions:**")
    lot_cost_pct = st.sidebar.slider("Finished Lot Cost (%)", min_value=0.0, max_value=30.0, value=18.0, step=0.5) / 100.0
    margin_pct = st.sidebar.slider("Gross Margin (O&P) (%)", min_value=0.0, max_value=30.0, value=20.0, step=0.5) / 100.0
    sales_pct = st.sidebar.slider("Sales & Marketing (%)", min_value=0.0, max_value=15.0, value=8.0, step=0.5) / 100.0
    finance_pct = st.sidebar.slider("Soft Costs & Finance (%)", min_value=0.0, max_value=15.0, value=4.0, step=0.5) / 100.0
    
    target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)
    base_direct_cost_sf = retail_price_sf * target_hard_cost_pct
    
    st.sidebar.success(f"**Output Direct Cost:**\n${base_direct_cost_sf:.2f} / SF (Heated)")

st.sidebar.subheader("Auxiliary Structure (Carport / Garage)")
structure_type = st.sidebar.selectbox("Structure Type", ["Carport", "Garage"])
struct_sqft = st.sidebar.number_input(f"{structure_type} SqFt per Unit", value=200, step=25, format="%d")
default_struct_cost = 31.0 if structure_type == "Carport" else 55.0
base_struct_cost_sf = st.sidebar.slider(f"{structure_type} Cost / SF ($)", min_value=15.0, max_value=90.0, value=default_struct_cost, step=1.0)

st.sidebar.subheader("Porches (Front & Back)")
front_porch_sqft = st.sidebar.number_input("Front Porch SqFt", value=60, step=10, format="%d")
front_porch_cost_sf = st.sidebar.slider("Front Porch Cost / SF ($)", min_value=15.0, max_value=70.0, value=35.0, step=1.0)

back_porch_sqft = st.sidebar.number_input("Back Porch SqFt", value=120, step=10, format="%d")
back_porch_cost_sf = st.sidebar.slider("Back Porch Cost / SF ($)", min_value=15.0, max_value=70.0, value=35.0, step=1.0)

# --- SECTION 1: CONSTRUCTION LOAN FINANCING & TIMELINE ---
st.sidebar.subheader("Construction Loan Financing & Timeline")
const_ltv = st.sidebar.slider("Construction Loan LTV (%)", min_value=60.0, max_value=100.0, value=85.0, step=5.0) / 100.0
build_months = st.sidebar.slider("Construction Duration (Months)", min_value=3, max_value=18, value=9, step=1)
const_rate = st.sidebar.slider("Construction Loan Rate (%)", min_value=4.0, max_value=14.0, value=8.5, step=0.5) / 100.0
avg_draw_pct = st.sidebar.slider("Average Draw / Principal Utilization Rate (%)", min_value=20.0, max_value=100.0, value=50.0, step=5.0) / 100.0
const_closing_fee = st.sidebar.number_input("Construction Loan Closing Fee ($ total)", value=6000, step=500, format="%d")

# --- SECTION 2: PERMANENT REFINANCE (TAKEOUT) ---
st.sidebar.subheader("Permanent Refinance (Takeout)")
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
    st.sidebar.markdown(f"💵 **Points Cost:** `{buydown_pts}% of Takeout Loan`")

# --- SECTION 3: DSCR & OPERATING SECTION ---
st.sidebar.subheader("DSCR & Operating Metrics")
target_dscr_rate = st.sidebar.number_input("Target Lender DSCR Rate", min_value=1.0, max_value=1.5, value=1.20, step=0.05)
gross_monthly_rent = st.sidebar.number_input("Gross Monthly Rental Income per Unit ($)", value=1650, step=50, format="%d")
vacancy_rate = st.sidebar.slider("Vacancy Rate (%)", min_value=0.0, max_value=15.0, value=5.0, step=1.0) / 100.0
opex_rate = st.sidebar.slider("Operating Expenses (OpEx) Rate of EGI (%)", min_value=15.0, max_value=50.0, value=30.0, step=1.0) / 100.0

st.sidebar.subheader("Land & Soft Costs")
land_basis = st.sidebar.number_input("Land Basis per Lot ($)", value=15000, step=1000, format="%d")
soft_costs = st.sidebar.number_input("Soft Costs per Unit ($)", value=5500, step=500, format="%d")

st.sidebar.subheader("PDF Export Options")
pdf_include_sublevels = st.sidebar.checkbox("Include Detailed Sub-Levels in PDF Report", value=True)


# --- UI PLACEHOLDERS FOR TOP METRICS ---
ui_top_metrics = st.container()
ui_op_metrics = st.container()
st.divider()
ui_rev_eng = st.container()


# --- RAW GRANULAR DATA (DOCUMENT MATCHING) ---
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


# --- GRANULAR HARD COST BUILDUP UI (DRIVES THE CORE CALCULATIONS) ---
st.markdown("### 🧱 Granular Direct Hard Cost Buildup (Trade Divisions)")

granular_mode = st.radio(
    "Buildup Entry Mode", 
    ["Auto-Proportional (Linked to Master Model)", "Manual Custom Entry (Bottom-Up)"], 
    horizontal=True
)

pdf_granular_data = [] # Stores final data for PDF export

if granular_mode == "Auto-Proportional (Linked to Master Model)":
    st.caption("Budget dynamically scales proportionally based on your active Direct Cost / SF and the Wickboldt Capital baseline document weightings.")
    
    # Values default to sidebar
    direct_cost_sf = base_direct_cost_sf
    struct_cost_sf = base_struct_cost_sf

    show_sub_items = st.toggle("Show Detailed Sub-Level Trade Itemization", value=False)
    
    # 1. Heated Area
    st.markdown(f"#### 1. Heated Living Area ({sqft} SF @ ${direct_cost_sf:.2f} / SF)")
    h_data = {"Division / Trade Level": [], "Live Cost / SF": [], f"Per Unit Cost": [], "Scope Specifications": []}
    
    for name, base_val, is_header, scope in raw_heated_divs:
        if not show_sub_items and not is_header:
            continue
        live_sf = direct_cost_sf * (base_val / 74.0)
        h_data["Division / Trade Level"].append(name)
        h_data["Live Cost / SF"].append(f"${live_sf:.2f}")
        h_data[f"Per Unit Cost"].append(f"${live_sf * sqft:,.0f}")
        h_data["Scope Specifications"].append(scope)
        pdf_granular_data.append((name, live_sf, live_sf * sqft, live_sf * sqft * units, is_header))
        
    st.dataframe(pd.DataFrame(h_data), hide_index=True, use_container_width=True)
    
    # 2. Structure Area
    st.markdown(f"#### 2. {structure_type} Auxiliary ({struct_sqft} SF @ ${struct_cost_sf:.2f} / SF)")
    s_data = {"Component Level": [], "Live Cost / SF": [], f"Per Unit Cost": []}
    
    for name, base_val, is_header in raw_struct_divs:
        if not show_sub_items and not is_header:
            continue
        live_sf = struct_cost_sf * (base_val / 31.0)
        s_data["Component Level"].append(name)
        s_data["Live Cost / SF"].append(f"${live_sf:.2f}")
        s_data[f"Per Unit Cost"].append(f"${live_sf * struct_sqft:,.0f}")
        
    st.dataframe(pd.DataFrame(s_data), hide_index=True, use_container_width=True)

else:
    st.caption("Enter your custom $ / SF for each trade division below. Your inputs will sum together to automatically override the Master Model.")
    
    # 1. Heated Area (Manual Editor)
    st.markdown(f"#### 1. Heated Living Area ({sqft} SF)")
    hl_heated = [{"Division / Trade Level": name, "Cost / SF": base_direct_cost_sf * (base/74.0), "Scope": scope} for name, base, is_h, scope in raw_heated_divs if is_h]
    
    edited_h = st.data_editor(
        pd.DataFrame(hl_heated),
        column_config={
            "Division / Trade Level": st.column_config.TextColumn(disabled=True),
            "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5),
            "Scope": st.column_config.TextColumn(disabled=True)
        },
        hide_index=True,
        use_container_width=True,
        key="manual_heated_editor"
    )
    # The sum of their manual entries becomes the new Master Direct Cost!
    direct_cost_sf = edited_h["Cost / SF"].sum()
    st.success(f"**Calculated Manual Direct Cost:** ${direct_cost_sf:.2f} / SF")
    
    for index, row in edited_h.iterrows():
        live_sf = row["Cost / SF"]
        pdf_granular_data.append((row["Division / Trade Level"], live_sf, live_sf * sqft, live_sf * sqft * units, True))
    
    # 2. Structure Area (Manual Editor)
    st.markdown(f"#### 2. {structure_type} Auxiliary ({struct_sqft} SF)")
    hl_struct = [{"Component Level": name, "Cost / SF": base_struct_cost_sf * (base/31.0)} for name, base, is_h in raw_struct_divs if not is_h]
    
    edited_s = st.data_editor(
        pd.DataFrame(hl_struct),
        column_config={
            "Component Level": st.column_config.TextColumn(disabled=True),
            "Cost / SF": st.column_config.NumberColumn(format="$%.2f", min_value=0.0, step=0.5)
        },
        hide_index=True,
        use_container_width=True,
        key="manual_struct_editor"
    )
    # The sum becomes the new Master Structure Cost!
    struct_cost_sf = edited_s["Cost / SF"].sum()


# 3. PORCHES STACK (Always renders below Granular logic)
st.markdown(f"#### 3. Porches & Outdoor Living ({front_porch_sqft + back_porch_sqft} Total SF)")
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf
p_data = {
    "Component": ["Front Porch", "Back Porch", "TOTAL PORCHES"],
    "Area (SF)": [f"{front_porch_sqft} SF", f"{back_porch_sqft} SF", f"{front_porch_sqft + back_porch_sqft} SF"],
    "Live Cost / SF": [f"${front_porch_cost_sf:.2f}", f"${back_porch_cost_sf:.2f}", "-"],
    "Per Unit Cost": [f"${front_porch_cost:,.0f}", f"${back_porch_cost:,.0f}", f"${front_porch_cost + back_porch_cost:,.0f}"]
}
st.dataframe(pd.DataFrame(p_data), hide_index=True, use_container_width=True)

st.divider()


# --- CORE CALCULATIONS (RUNS USING FINAL DIRECT & STRUCT COSTS) ---
struct_total_cost = struct_sqft * struct_cost_sf
total_under_roof_sqft = sqft + struct_sqft + front_porch_sqft + back_porch_sqft

heated_hard_cost = sqft * direct_cost_sf
hard_cost_per_unit = heated_hard_cost + struct_total_cost + front_porch_cost + back_porch_cost
blended_cost_per_sf = hard_cost_per_unit / total_under_roof_sqft if total_under_roof_sqft > 0 else 0

total_hard_cost = hard_cost_per_unit * units
arv_per_unit = comp_blended_cost * total_under_roof_sqft
total_arv = arv_per_unit * units

loan_total = total_arv * refi_ltv
total_buydown_cost = loan_total * (buydown_pts / 100.0) if apply_buydown else 0

monthly_interest_rate = net_refi_rate / 12.0
total_payments = refi_term_years * 12
if monthly_interest_rate > 0:
    monthly_pi_per_unit = loan_total / units * (monthly_interest_rate * (1 + monthly_interest_rate)**total_payments) / ((1 + monthly_interest_rate)**total_payments - 1)
else:
    monthly_pi_per_unit = (loan_total / units) / total_payments if total_payments > 0 else 0

total_monthly_pi = monthly_pi_per_unit * units

# Advanced Operating Calculations
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

gcond = total_hard_cost * 0.05
fee_basis = total_hard_cost + gcond

if gc_fee_mode == "Consolidated Flat Fee ($ Total)":
    gc_fee = custom_gc_fee
else:
    gc_fee = fee_basis * gc_fee_pct

premium = total_hard_cost * 0.05
total_const = fee_basis + gc_fee + premium

total_soft_costs = soft_costs * units
total_land = land_basis * units

total_project_costs_ex_interest = total_land + total_const + total_soft_costs + const_closing_fee
construction_loan_limit = total_project_costs_ex_interest * const_ltv
carry_int = construction_loan_limit * avg_draw_pct * const_rate * (build_months / 12.0)

total_project_basis = total_project_costs_ex_interest + carry_int + refi_closing_fee + total_buydown_cost
cash_surplus = loan_total - total_project_basis
retained_equity = total_arv - loan_total
day1_wealth = gc_fee + max(0, cash_surplus) + retained_equity


# --- POPULATE THE TOP PLACEHOLDERS WITH CALCULATED DATA ---
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

    op1.metric("Derived Unit ARV", f"${arv_per_unit:,.0f}", f"${total_arv:,.0f} Total ARV")
    op2.metric("Actual DSCR Rate", f"{actual_dscr:.2f}x", f"Target: {target_dscr_rate:.2f}x", delta_color="normal" if actual_dscr >= target_dscr_rate else "inverse")
    op3.metric("Monthly Cash Flow", f"${monthly_cash_flow:,.0f} /mo", f"${monthly_cash_flow*12:,.0f} Annual", delta_color="normal" if monthly_cash_flow >= 0 else "inverse")
    op4.metric("Monthly P&I Payment", f"${total_monthly_pi:,.0f} /mo", f"{refi_term_years}Yr @ {net_refi_rate*100:.3f}%")

with ui_rev_eng:
    if cost_calc_mode == "Reverse-Engineer from Comp (Adjustable Breakdown)":
        st.markdown("### 🔄 Retail Price Reverse-Engineering Breakdown")
        st.caption(f"Isolating Target Direct Hard Costs by applying custom standard deductions to your Comp's Retail Price of **${retail_price_sf:.2f} / SF**.")
        
        breakdown_data = {
            "Cost Category": [
                "Retail Listing / Comp Price",
                "(-) Finished Lot Cost",
                "(-) Gross Margin (O&P)",
                "(-) Sales & Marketing",
                "(-) Soft Costs & Finance",
                "Target Direct Hard Costs"
            ],
            "Typical % of Price": [
                "100.0%",
                f"{lot_cost_pct*100:.1f}%",
                f"{margin_pct*100:.1f}%",
                f"{sales_pct*100:.1f}%",
                f"{finance_pct*100:.1f}%",
                f"{target_hard_cost_pct*100:.1f}%"
            ],
            "Cost / SF ($)": [
                f"${retail_price_sf:.2f}",
                f"-${retail_price_sf * lot_cost_pct:.2f}",
                f"-${retail_price_sf * margin_pct:.2f}",
                f"-${retail_price_sf * sales_pct:.2f}",
                f"-${retail_price_sf * finance_pct:.2f}",
                f"${base_direct_cost_sf:.2f}"
            ],
            "Description": [
                "MLS listing price / retail takeout appraisal.",
                "Raw land, engineering, road paving, wet/dry utility infrastructure.",
                "Builder gross overhead and corporate net margin.",
                "Realtor commissions, internal sales reps, buyer closing concessions.",
                "Impact fees, plan design, municipal permits, and loan interest carry.",
                "Sticks, bricks, equipment, and turnkey subcontractor labor."
            ]
        }
        st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)
        st.divider()


# --- VERTICAL STACK FOR MAIN TABLES ---
st.markdown("### 📊 Detailed Construction Cost & Capital Ledger")
ledger_data = {
    "Cost Category / Sub-Level": [
        "--- DIRECT HARD COSTS ---",
        "Heated Living Area (Sub-Level)", 
        f"{structure_type} (Sub-Level)",
        "Front Porch (Sub-Level)",
        "Back Porch (Sub-Level)",
        "SUBTOTAL DIRECT HARD COSTS",
        "--- INDIRECT & OVERHEAD HARD COSTS ---",
        "General Conditions (5% of Direct)", 
        "GC Management Fee", 
        "BTR Buying Power Premium (5% of Direct)", 
        "TOTAL HARD COSTS",
        "--- LAND, SOFT & FINANCING COSTS ---",
        "Land Acquisition Basis",
        "Soft Costs & Permitting",
        "Construction Loan Closing Fee",
        f"Accrued Const. Interest ({build_months} Mos)",
        "Takeout Refinance Closing Fee",
        "Rate Buydown Points Cost",
        "TOTAL PROJECT BASIS"
    ],
    "Area (SF) / Metric": [
        "",
        f"{sqft:,.0f} SF",
        f"{struct_sqft:,.0f} SF",
        f"{front_porch_sqft:,.0f} SF",
        f"{back_porch_sqft:,.0f} SF",
        f"{total_under_roof_sqft:,.0f} SF Under Roof",
        "",
        "5.0% Basis",
        "Flat Fee" if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else f"{gc_fee_pct*100:.1f}% Basis",
        "5.0% Basis",
        f"{total_under_roof_sqft:,.0f} Total SF",
        "",
        f"{units:,.0f} Lot(s)",
        "Per Unit Basis",
        "Flat Fee",
        f"{avg_draw_pct*100:.0f}% Avg Draw",
        "Flat Fee",
        f"{buydown_pts} Points ({buydown_pts}% of Loan)",
        f"${total_project_basis/units:,.0f} / Door"
    ],
    "Cost / SF ($)": [
        "",
        f"${direct_cost_sf:.2f} /SF",
        f"${struct_cost_sf:.2f} /SF",
        f"${front_porch_cost_sf:.2f} /SF",
        f"${back_porch_cost_sf:.2f} /SF",
        f"${blended_cost_per_sf:.2f} /SF (Blended)",
        "",
        "-", "-", "-", "-", "", "-", "-", "-", "-", "-", "-", "-"
    ],
    "Total Amount ($)": [
        "",
        heated_hard_cost * units,
        struct_total_cost * units,
        front_porch_cost * units,
        back_porch_cost * units,
        total_hard_cost,
        "",
        gcond,
        gc_fee,
        premium,
        total_const,
        "",
        total_land,
        total_soft_costs,
        const_closing_fee,
        carry_int,
        refi_closing_fee,
        total_buydown_cost,
        total_project_basis
    ]
}
df_ledger = pd.DataFrame(ledger_data)
df_ledger['Total Amount ($)'] = df_ledger['Total Amount ($)'].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)
st.dataframe(df_ledger, hide_index=True, use_container_width=True)

st.divider()

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

st.divider()

st.markdown("### 🏢 Operating Performance Summary")
dscr_summary_data = {
    "Pro Forma Line Item": [
        "Gross Potential Rent (GPR)", 
        f"(-) Vacancy Loss @ {vacancy_rate*100:.1f}%", 
        "= Effective Gross Income (EGI)", 
        f"(-) Operating Expenses (OpEx) @ {opex_rate*100:.1f}%", 
        "= Net Operating Income (NOI)", 
        "(-) Total Debt Service (P&I)",
        "= Net Cash Flow",
        "---",
        "Actual DSCR Rate",
        "Target Lender DSCR",
        "DSCR Variance"
    ],
    "Monthly": [
        f"${total_gross_monthly_income:,.2f}", 
        f"-${monthly_vacancy_loss:,.2f}", 
        f"${annual_egi / 12:,.2f}", 
        f"-${annual_opex / 12:,.2f}", 
        f"${monthly_noi:,.2f}", 
        f"-${total_monthly_pi:,.2f}",
        f"${monthly_cash_flow:,.2f}",
        "---",
        f"{actual_dscr:.2f}x",
        f"{target_dscr_rate:.2f}x",
        f"{dscr_variance:+.2f}x"
    ],
    "Annual": [
        f"${total_gross_monthly_income * 12:,.2f}", 
        f"-${annual_vacancy_loss:,.2f}", 
        f"${annual_egi:,.2f}", 
        f"-${annual_opex:,.2f}", 
        f"${annual_noi:,.2f}", 
        f"-${annual_debt_service:,.2f}",
        f"${monthly_cash_flow * 12:,.2f}",
        "---",
        f"{actual_dscr:.2f}x",
        f"{target_dscr_rate:.2f}x",
        f"{dscr_variance:+.2f}x"
    ]
}
df_dscr = pd.DataFrame(dscr_summary_data)
st.dataframe(df_dscr, hide_index=True, use_container_width=True)


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

    # PDF SECTION 2: Full Operating Waterfall
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
    
    gc_label = "Consolidated GC Flat Fee:" if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else f"GC Management Fee ({gc_fee_pct*100:.1f}%):"
    pdf.cell(100, 7, gc_label, 0, 0)
    pdf.cell(90, 7, f"${gc_fee:,.0f}", 0, 1, 'R')
    
    pdf.cell(100, 7, "Land Acquisition Basis:", 0, 0)
    pdf.cell(90, 7, f"${total_land:,.0f}", 0, 1, 'R')
    pdf.cell(100, 7, "Accrued Construction Loan Interest:", 0, 0)
    pdf.cell(90, 7, f"${carry_int:,.0f}", 0, 1, 'R')
    pdf.cell(100, 7, "Total Soft Costs & Closing Fees:", 0, 0)
    pdf.cell(90, 7, f"${total_soft_costs + const_closing_fee + refi_closing_fee + total_buydown_cost:,.0f}", 0, 1, 'R')
    
    # PDF SECTION 4: Dynamically pulls from what was actually shown in the UI
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
        # Check conditional toggle logic if we are running Auto mode
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
