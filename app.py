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

comp_address = st.text_input("Comparable Property Address (Optional)", placeholder="e.g. 16144 South Bud Broussard Road, Prairieville, LA")

cc_col1, cc_col2, cc_col3, cc_col4, cc_col5 = st.columns(5)
comp_price = cc_col1.number_input("Comp Total Sale Price / Value ($)", value=182600, step=1000, format="%d")
comp_heated_sf = cc_col2.number_input("Comp Heated SF", value=1150, step=50, format="%d")
comp_struct_sf = cc_col3.number_input("Comp Garage/Carport SF", value=200, step=25, format="%d")
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

# Fixed GC Fee Structure Toggle
gc_fee_mode = st.sidebar.radio("GC Fee Structure", ["Percentage of Hard Costs (%)", "Consolidated Flat Fee ($ Total)"])
if gc_fee_mode == "Percentage of Hard Costs (%)":
    gc_fee_pct = st.sidebar.number_input("GC Management Fee (%)", min_value=0.0, max_value=50.0, value=10.0, step=0.5) / 100.0
    custom_gc_fee = 0
else:
    custom_gc_fee = st.sidebar.number_input("Total Consolidated GC Fee ($)", value=20000, step=1000, format="%d")
    gc_fee_pct = 0.0

st.sidebar.subheader("Construction Costs (Heated Area)")
sqft = st.sidebar.number_input("Heated SqFt per Unit", value=1150, step=50, format="%d")

# Streamlined Cost Calculation Mode
cost_calc_mode = st.sidebar.radio(
    "Cost Calculation Mode", 
    [
        "Manual Set (Heated SF)", 
        "Reverse-Engineer from Comp (Adjustable Breakdown)"
    ]
)

if cost_calc_mode == "Manual Set (Heated SF)":
    direct_cost_sf = st.sidebar.slider("Direct Build Cost / SF ($)", min_value=40.0, max_value=150.0, value=74.0, step=1.0)
else:
    # Fully Automated Top-Down Retail Price Reverse Engineering with adjustable sliders
    st.sidebar.caption("Retail Price / SF is dynamically derived from your Market Comp inputs.")
    retail_price_sf = comp_blended_cost
    st.sidebar.markdown(f"**Comp Retail Price:** `${retail_price_sf:.2f} / SF`")
    
    st.sidebar.markdown("**Adjustable Deductions:**")
    lot_cost_pct = st.sidebar.slider("Finished Lot Cost (%)", min_value=0.0, max_value=30.0, value=18.0, step=0.5) / 100.0
    margin_pct = st.sidebar.slider("Gross Margin (O&P) (%)", min_value=0.0, max_value=30.0, value=20.0, step=0.5) / 100.0
    sales_pct = st.sidebar.slider("Sales & Marketing (%)", min_value=0.0, max_value=15.0, value=8.0, step=0.5) / 100.0
    finance_pct = st.sidebar.slider("Soft Costs & Finance (%)", min_value=0.0, max_value=15.0, value=4.0, step=0.5) / 100.0
    
    target_hard_cost_pct = 1.0 - (lot_cost_pct + margin_pct + sales_pct + finance_pct)
    direct_cost_sf = retail_price_sf * target_hard_cost_pct
    
    st.sidebar.success(f"**Output Direct Cost:**\n${direct_cost_sf:.2f} / SF (Heated)")

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


# --- CORE CALCULATIONS ---
struct_total_cost = struct_sqft * struct_cost_sf
front_porch_cost = front_porch_sqft * front_porch_cost_sf
back_porch_cost = back_porch_sqft * back_porch_cost_sf
total_under_roof_sqft = sqft + struct_sqft + front_porch_sqft + back_porch_sqft

# Calculate Heated Hard Cost identically regardless of mode
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

total_gross_monthly_income = gross_monthly_rent * units
effective_gross_monthly_income = total_gross_monthly_income * (1.0 - vacancy_rate)
annual_egi = effective_gross_monthly_income * 12.0
annual_opex = annual_egi * opex_rate
annual_noi = annual_egi - annual_opex
monthly_noi = annual_noi / 12.0

annual_debt_service = total_monthly_pi * 12.0
actual_dscr = annual_noi / annual_debt_service if annual_debt_service > 0 else 0
monthly_cash_flow = monthly_noi - total_monthly_pi

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

def create_pdf():
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
    pdf.cell(0, 8, " 2. Operating Performance & DSCR", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    pdf.cell(100, 7, "Monthly Gross Rent:", 0, 0)
    pdf.cell(90, 7, f"${total_gross_monthly_income:,.2f}", 0, 1, 'R')
    pdf.cell(100, 7, f"Annual OpEx ({opex_rate*100:.0f}%):", 0, 0)
    pdf.cell(90, 7, f"${annual_opex:,.2f}", 0, 1, 'R')
    pdf.cell(100, 7, "Net Operating Income (NOI - Annual):", 0, 0)
    pdf.cell(90, 7, f"${annual_noi:,.2f}", 0, 1, 'R')
    pdf.cell(100, 7, "Total Debt Service (P&I - Annual):", 0, 0)
    pdf.cell(90, 7, f"${annual_debt_service:,.2f}", 0, 1, 'R')
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 7, "Actual DSCR Rate:", 0, 0)
    pdf.cell(90, 7, f"{actual_dscr:.2f}x (Target: {target_dscr_rate:.2f}x)", 0, 1, 'R')
    pdf.cell(100, 7, "Monthly Net Cash Flow:", 0, 0)
    pdf.cell(90, 7, f"${monthly_cash_flow:,.2f} /mo", 0, 1, 'R')
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
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

with download_placeholder:
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📄 Download Enterprise Report (PDF)",
        data=create_pdf(),
        file_name=f"Wickboldt_Capital_ProForma_{report_date.replace(' ', '_').replace(',', '')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

# --- REVERSE ENGINEER UI BLOCKS ---
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
            f"${direct_cost_sf:.2f}"
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

# --- DASHBOARD UI ---

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

st.markdown("### 🏢 Operating & DSCR Metrics")
op1, op2, op3, op4 = st.columns(4)

op1.metric("Derived Unit ARV", f"${arv_per_unit:,.0f}", f"${total_arv:,.0f} Total ARV")
op2.metric("Actual DSCR Rate", f"{actual_dscr:.2f}x", f"Target: {target_dscr_rate:.2f}x", delta_color="normal" if actual_dscr >= target_dscr_rate else "inverse")
op3.metric("Monthly Cash Flow", f"${monthly_cash_flow:,.0f} /mo", f"${monthly_cash_flow*12:,.0f} Annual", delta_color="normal" if monthly_cash_flow >= 0 else "inverse")
op4.metric("Monthly P&I Payment", f"${total_monthly_pi:,.0f} /mo", f"{refi_term_years}Yr @ {net_refi_rate*100:.3f}%")

st.divider()

# --- VERTICAL STACK FOR TABLES ---

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
    "Metric Item": [
        "Gross Rental Income", 
        "Effective Gross Income (EGI)", 
        f"Operating Expenses (OpEx) @ {opex_rate*100:.0f}%", 
        "Net Operating Income (NOI)", 
        "Total Debt Service (P&I)"
    ],
    "Monthly ($)": [
        f"${total_gross_monthly_income:,.2f}", 
        f"${annual_egi / 12:,.2f}", 
        f"${annual_opex / 12:,.2f}", 
        f"${monthly_noi:,.2f}", 
        f"${total_monthly_pi:,.2f}"
    ],
    "Annual ($)": [
        f"${total_gross_monthly_income * 12:,.2f}", 
        f"${annual_egi:,.2f}", 
        f"${annual_opex:,.2f}", 
        f"${annual_noi:,.2f}", 
        f"${annual_debt_service:,.2f}"
    ]
}
df_dscr = pd.DataFrame(dscr_summary_data)
st.dataframe(df_dscr, hide_index=True, use_container_width=True)
