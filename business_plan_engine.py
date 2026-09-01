import os
import tempfile
import pandas as pd
from fpdf import FPDF
import math

class BusinessPlanReport(FPDF):
    def __init__(self, borrower_name, borrower_company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.borrower_name = borrower_name
        self.borrower_company = borrower_company

    def header(self):
        try:
            if os.path.exists("Gemini_Generated_Image_.png"):
                self.image("Gemini_Generated_Image_.png", 12.7, 10, 40)
        except Exception:
            pass
        self.set_y(12)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, self.borrower_company.upper(), ln=1, align='R')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, "Master Development Business Plan", ln=1, align='R')
        self.ln(10)
        self.line(12.7, self.get_y(), 203.3, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | Confidential & Proprietary - {self.borrower_company}', 0, 0, 'C')

def create_business_plan_pdf(ui, calc):
    # Extract Data
    company = ui.get('borrower_company', 'Wickboldt Capital')
    name = ui.get('borrower_name', 'Stephen J. Wickboldt, Jr.')
    address = ui.get('project_address', 'Rogers Moore Parkway, Hammond, Louisiana')
    
    units = calc.get('units', 24)
    sqft = calc.get('sqft', 1150)
    beds = ui.get('project_beds', 3)
    baths = ui.get('project_baths', 2.5)
    struct_type = calc.get('structure_type', 'garage').lower()
    
    dscr_target = calc.get('target_dscr_rate', 1.20)
    ltv = calc.get('refi_ltv', 0.75) * 100
    
    # Financials (Per Unit & Total)
    hard_costs = calc.get('total_hard_cost', 0)
    gc_fee = calc.get('default_gc_fee', 0)
    soft_costs = calc.get('total_vertical_soft', 0) + calc.get('total_indirect_costs', 0) - gc_fee
    const_close = calc.get('const_closing_fee', 0)
    const_int = calc.get('carry_int_base', 0)
    refi_close = calc.get('refi_closing_fee', 0)
    land_basis = calc.get('total_land_default', 0)
    
    tpc_total = hard_costs + gc_fee + soft_costs + const_close + const_int + refi_close + land_basis
    
    # Operating
    gpr_mo = calc.get('total_gross_monthly_income', 0)
    vac_mo = calc.get('monthly_vacancy_loss', 0)
    egi_mo = gpr_mo - vac_mo
    opex_mo = calc.get('mo_other_opex', 0) + calc.get('monthly_mgmt_fee', 0)
    noi_mo = calc.get('monthly_noi', 0)
    pi_mo = calc.get('total_monthly_pi', 0)
    ncf_mo = calc.get('monthly_cash_flow', 0)
    
    # 10-Year Wealth
    tax_savings_yr = calc.get('annual_tax_savings', 0)
    cum_ncf = calc.get('cumulative_cf', [0]*11)[10]
    prin_paydown = calc.get('principal_paid', [0]*11)[10]
    appreciation_gain = calc.get('asset_vals', [0]*11)[10] - calc.get('total_arv', 0)
    cum_tax_savings = tax_savings_yr * 10
    total_wealth = cum_ncf + prin_paydown + appreciation_gain + cum_tax_savings

    pdf = BusinessPlanReport(borrower_name=name, borrower_company=company, orientation='P', unit='mm', format='Letter')
    pdf.set_margins(12.7, 12.7, 12.7)
    pdf.set_auto_page_break(auto=True, margin=15.0)
    pdf.add_page()
    
    # --- TITLE SECTION ---
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 8, company.upper(), ln=1, align='C')
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, "MASTER DEVELOPMENT BUSINESS PLAN", ln=1, align='C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 6, f"{units}-Lot Build-to-Rent Residential Portfolio", ln=1, align='C')
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, f"Project Location: {address}", ln=1, align='C')
    pdf.cell(0, 6, "Asset Class: High-Efficiency Narrow-Footprint Residential Rental Portfolio", ln=1, align='C')
    pdf.cell(0, 6, f"Prepared By: {name}", ln=1, align='C')
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, f"Licensed General Contractor & Principal, {company}", ln=1, align='C')
    pdf.ln(10)

    # --- 1. EXECUTIVE SUMMARY ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 1. Executive Summary & Strategic Vision", ln=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    p1 = f"{company} is launching a premier multi-phase build-to-rent residential development located at {address}. The master development encompasses {units} total building lots, structured across distinct phases. This business plan outlines the institutional-grade execution strategy for the portfolio, focusing on two-story, narrow-footprint, high-efficiency single-family rental homes configured with {beds} bedrooms, {baths} bathrooms, and an integrated {struct_type} within an optimized {sqft:,.0f} sq ft footprint."
    pdf.multi_cell(0, 5, p1.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(2)
    p2 = f"Leveraging advanced framing and insulation methodologies—including 2x6 wood-frame construction with 9-foot ceilings and high-performance spray foam insulation—{company} delivers superior structural durability, extreme energy efficiency, and minimized long-term maintenance overhead. The primary financing strategy relies on targeted commercial bank construction-to-permanent loans, capitalizing on a strong institutional equity position anchored by land value, maximum appraised value underwriting at a {dscr_target:.2f} DSCR ({ltv:.0f}% LTV permanent loan), and significant state/utility energy rebates serving as additional portfolio upside."
    pdf.multi_cell(0, 5, p2.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(6)

    # --- 2. INVESTMENT THESIS ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " 2. Investment Thesis, Favorable Demographics & Market Opportunity", ln=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    p3 = "The regional housing market experiences persistent undersupply in modern, energy-efficient rental housing designed for working households and small families. Wickboldt Capital addresses this deficit through a disciplined build-to-rent model.\n\nStrategic Location & Dual-Demographic Demand: Situated near major economic and academic hubs, the development is uniquely positioned to capture highly reliable tenant pools. This proximity creates a recession-resistant tenant pipeline, guaranteeing consistent year-round demand, commanding premium rent rates, and drastically minimizing vacancy risk.\n\nProperty Development Strategy: Undervalued Land Acquisition & Equity Creation: Wickboldt Capital's foundational edge relies on identifying and securing strategically positioned, undervalued property parcels, transforming raw land into high-performing institutional assets. By acquiring parcels at attractive basis points and constructing purpose-built housing in supply-constrained corridors, the firm captures immediate development premiums, builds institutional-grade equity, and establishes resilient income-generating properties.\n\nYield & Capital Velocity: Structuring developments to achieve rapid equity recapture via cash-out refinancing milestones, optimizing investor cash-on-cash return profiles."
    pdf.multi_cell(0, 5, p3.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(6)

    # --- 3. MASTER SITE DEVELOPMENT & PHASING ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " 3. Master Site Development & Phasing Plan", ln=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    pdf.multi_cell(0, 5, "The development is engineered for phased deployment to manage construction risk, maximize absorption rates, and streamline capital deployment.")
    pdf.ln(3)
    
    phase_1_lots = math.ceil(units * 0.4)
    phase_2_lots = units - phase_1_lots
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(30, 6, "Project Phase", 1, 0, 'C')
    pdf.cell(25, 6, "Lot Count", 1, 0, 'C')
    pdf.cell(130, 6, "Development Focus", 1, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(30, 6, "Phase One", 1, 0, 'C')
    pdf.cell(25, 6, f"{phase_1_lots} Lots", 1, 0, 'C')
    pdf.cell(130, 6, "Primary infrastructure, initial street frontage, and launch.", 1, 1, 'L')
    pdf.cell(30, 6, "Phase Two", 1, 0, 'C')
    pdf.cell(25, 6, f"{phase_2_lots} Lots", 1, 0, 'C')
    pdf.cell(130, 6, "Secondary infrastructure rollout, portfolio expansion, and stabilization.", 1, 1, 'L')
    pdf.ln(6)

    # --- 4. COMPREHENSIVE FINANCIAL PROFORMA ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " 4. Comprehensive Financial Proforma & Underwriting (Single Unit Basis)", ln=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    p4 = f"The financial model is structured around an optimized {sqft:,.0f} sq ft two-story {beds}-bedroom, {baths}-bathroom single-family rental unit. The underwriting accounts for upfront construction loan closing costs, interest-only construction loan servicing, and permanent refinance closing fees."
    pdf.multi_cell(0, 5, p4.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(4)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "Total Project Cost Breakdown & Uses of Funds (Per Unit)", ln=1)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(95, 6, "Cost Category", 1, 0, 'C')
    pdf.cell(30, 6, "Total Amount", 1, 0, 'C')
    pdf.cell(30, 6, "Cost Per Sq Ft", 1, 0, 'C')
    pdf.cell(30, 6, "% of TPC", 1, 1, 'C')
    
    pdf.set_font('Arial', '', 9)
    tpc_rows = [
        ("Direct Build Cost (Hard Costs)", hard_costs/units),
        ("General Contractor Fee (Flat)", gc_fee/units),
        ("Soft Costs, Permits & Architecture", soft_costs/units),
        ("Const. Loan Closing Costs", const_close/units),
        ("Const. Loan Interest (Carry)", const_int/units),
        ("Refinance Closing & Origination", refi_close/units),
        ("Land / Equity Position", land_basis/units),
    ]
    for name, amt in tpc_rows:
        pct = (amt / (tpc_total/units)) * 100 if tpc_total > 0 else 0
        psf = amt / sqft if sqft > 0 else 0
        pdf.cell(95, 6, name, 1, 0, 'L')
        pdf.cell(30, 6, f"${amt:,.2f}", 1, 0, 'R')
        pdf.cell(30, 6, f"${psf:,.2f} / sf", 1, 0, 'R')
        pdf.cell(30, 6, f"{pct:.2f}%", 1, 1, 'R')
        
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(95, 6, "Total Project Cost (TPC)", 1, 0, 'L')
    pdf.cell(30, 6, f"${tpc_total/units:,.2f}", 1, 0, 'R')
    pdf.cell(30, 6, f"${(tpc_total/units)/sqft:,.2f} / sf", 1, 0, 'R')
    pdf.cell(30, 6, "100.00%", 1, 1, 'R')
    pdf.ln(6)

    # Operating Table
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, "Operating Projections & Stabilized Return Profile (Per Unit)", ln=1)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(95, 6, "Operating Metric", 1, 0, 'C')
    pdf.cell(45, 6, "Monthly", 1, 0, 'C')
    pdf.cell(45, 6, "Annual", 1, 1, 'C')
    
    pdf.set_font('Arial', '', 9)
    op_rows = [
        ("Gross Potential Rent (GPR)", gpr_mo/units),
        ("Less Vacancy", -(vac_mo/units)),
        ("Effective Gross Income (EGI)", egi_mo/units),
        ("Operating Expenses", -(opex_mo/units)),
        ("Net Operating Income (NOI)", noi_mo/units),
        (f"Permanent Debt Service (ADS @ {dscr_target:.2f} DSCR)", -(pi_mo/units)),
        ("Net Cash Flow (Post-Stabilization)", ncf_mo/units)
    ]
    for name, mo_amt in op_rows:
        if "Net" in name or "Effective" in name:
            pdf.set_font('Arial', 'B', 9)
        else:
            pdf.set_font('Arial', '', 9)
        pdf.cell(95, 6, name, 1, 0, 'L')
        pdf.cell(45, 6, f"${mo_amt:,.2f}", 1, 0, 'R')
        pdf.cell(45, 6, f"${mo_amt*12:,.2f}", 1, 1, 'R')
    pdf.ln(6)

    # --- 5. 10-YEAR WEALTH ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " 5. 10-Year Wealth Accumulation & Tax Strategy", ln=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    p5 = f"Wickboldt Capital executes a capital recycling strategy by utilizing cash-out refinancing upon stabilization, enhanced by significant real estate tax advantages.\n\nTax Strategy & Depreciation:\n- Depreciable Basis: ${((tpc_total-land_basis)/units):,.2f}\n- Annual Depreciation: ${(tax_savings_yr/units):,.2f} per year in offset value.\n- Tax-Free Yield: 100% of the operating cash flow is completely shielded from federal income taxes across the decade-long holding period.\n\n10-Year Wealth Summary (Single Unit):\n- Cumulative Net Cash Flow: ${(cum_ncf/units):,.2f} (100% Tax-Free)\n- Loan Principal Paydown: ${(prin_paydown/units):,.2f}\n- 10-Year Tax Savings: ${(cum_tax_savings/units):,.2f}\n- Total 10-Year Wealth Gain: ${(total_wealth/units):,.2f}"
    pdf.multi_cell(0, 5, p5.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(6)

    # --- 6. PORTFOLIO WEALTH ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f" 6. {units}-Unit Portfolio: 10-Year Wealth Generation", ln=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    p6 = f"To maintain conservatism, the comprehensive portfolio wealth generation model scales across the entire {units}-lot portfolio over an extended 10-year horizon. The aggregate wealth generated incorporates staggered operating timelines across distinct tranches."
    pdf.multi_cell(0, 5, p6.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(60, 6, "Wealth Metric", 1, 0, 'C')
    pdf.cell(40, 6, "Portfolio Total", 1, 0, 'C')
    pdf.cell(85, 6, "Notes", 1, 1, 'C')
    pdf.set_font('Arial', '', 9)
    
    pdf.cell(60, 6, "Cumulative Net Cash Flow", 1, 0, 'L')
    pdf.cell(40, 6, f"${cum_ncf:,.2f}", 1, 0, 'R')
    pdf.cell(85, 6, "Aggregated across phased unit stabilization", 1, 1, 'L')
    
    pdf.cell(60, 6, "Cumulative Equity Gain", 1, 0, 'L')
    pdf.cell(40, 6, f"${prin_paydown + appreciation_gain:,.2f}", 1, 0, 'R')
    pdf.cell(85, 6, "Includes principal paydown & appreciation", 1, 1, 'L')
    
    pdf.cell(60, 6, "Cumulative Tax Savings", 1, 0, 'L')
    pdf.cell(40, 6, f"${cum_tax_savings:,.2f}", 1, 0, 'R')
    pdf.cell(85, 6, "Calculated paper loss offset", 1, 1, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(60, 6, "Total Portfolio Wealth Gain", 1, 0, 'L')
    pdf.cell(40, 6, f"${total_wealth:,.2f}", 1, 0, 'R')
    pdf.cell(85, 6, f"Gross wealth creation across {units} units", 1, 1, 'L')
    pdf.ln(6)

    # --- 7. CONSTRUCTION METHODOLOGIES ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " 7. Construction Methodologies & Technical Specifications", ln=1, fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    p7 = "Building quality is the cornerstone of Wickboldt Capital's long-term asset value proposition, specifically targeting extreme energy efficiency, structural longevity, and optimized operational overhead for long-term rental portfolios.\n\n- Elevated Stem Wall Foundation: Constructed with a reinforced concrete stem wall system (featuring a 30-inch stem wall and integrated foam brick ledge) to elevate the primary living space above natural grade.\n- Conditioned Attic & Advanced Envelope: Premium 2x6 wood-frame construction with 9-foot ceilings and fully encapsulated closed-cell spray foam roof insulation.\n- High-Efficiency Climate Control: Implementation of ducted mini-split systems. Strict adherence to Manual J, S, D, and T protocols guarantees perfectly sized, ultra-efficient balanced airflow.\n- Heavy-Duty Fixtures & Finishes: Homes are specified with commercial-grade plumbing and hardware assets, solid core doors, luxury vinyl plank (LVP) flooring, and custom-tiled showers.\n- Architectural Integrity: Engineered with a narrow 22-foot width to optimize urban infill lots."
    pdf.multi_cell(0, 5, p7.encode('latin-1', 'replace').decode('latin-1'))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()
