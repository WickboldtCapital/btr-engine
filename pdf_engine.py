import os
import tempfile
import pandas as pd
from fpdf import FPDF

class EnterpriseReport(FPDF):
    def __init__(self, borrower_name, borrower_company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.borrower_name = borrower_name
        self.borrower_company = borrower_company

    def header(self):
        try:
            if os.path.exists("Gemini_Generated_Image_.png"):
                self.image("Gemini_Generated_Image_.png", 10, 8, 45)
        except Exception:
            pass
        self.set_y(12)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 8, 'BTR Pro Forma Report', border=0, ln=1, align='R')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 6, "Today's Foundation. Tomorrow's Legacy.", border=0, ln=1, align='R')
        self.set_y(32)
        self.line(10, 30, 200, 30)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | Prepared by: {self.borrower_name} - {self.borrower_company}', 0, 0, 'C')


def create_pdf(detail_mode, ui, calc, texts, tables):
    # --- Unpack UI Inputs ---
    project_name = ui.get("project_name", "")
    project_address = ui.get("project_address", "")
    project_beds = ui.get("project_beds", 3)
    project_baths = ui.get("project_baths", 2.0)
    report_date = ui.get("report_date", "")
    borrower_name = ui.get("borrower_name", "")
    borrower_company = ui.get("borrower_company", "")

    # --- Unpack Calc Metrics ---
    units = calc.get("units", 1)
    total_under_roof_sqft = calc.get("total_under_roof_sqft", 0)
    total_project_basis = calc.get("total_project_basis", 0)
    total_arv = calc.get("total_arv", 0)
    actual_const_loan = calc.get("actual_const_loan", 0)
    refi_ltv = calc.get("refi_ltv", 0.8)
    loan_total = calc.get("loan_total", 0)
    cash_surplus = calc.get("cash_surplus", 0)
    monthly_cash_flow_per_door = calc.get("monthly_cash_flow_per_door", 0)
    day1_wealth = calc.get("day1_wealth", 0)
    total_land_default = calc.get("total_land_default", 0)
    direct_cost_sf = calc.get("direct_cost_sf", 0)
    heated_hard_cost = calc.get("heated_hard_cost", 0)
    struct_cost_sf = calc.get("struct_cost_sf", 0)
    struct_total_cost = calc.get("struct_total_cost", 0)
    blended_cost_per_sf = calc.get("blended_cost_per_sf", 0)
    target_direct_hard_cost = calc.get("target_direct_hard_cost", 0)
    const_bank_val_mode = calc.get("const_bank_val_mode", "")
    const_bank_dscr = calc.get("const_bank_dscr", 1.2)
    bank_stressed_value = calc.get("bank_stressed_value", 0)
    const_bank_ltv = calc.get("const_bank_ltv", 0.8)
    seed_capital = calc.get("seed_capital", 0)
    const_bank_rent = calc.get("const_bank_rent", 0)
    const_bank_vac_pct = calc.get("const_bank_vac_pct", 0)
    const_bank_opex_pct = calc.get("const_bank_opex_pct", 0)
    const_bank_grm = calc.get("const_bank_grm", 0)
    lot_cost_pct = calc.get("lot_cost_pct", 0)
    lot_benchmark = calc.get("lot_benchmark", 0)
    const_closing_fee = calc.get("const_closing_fee", 0)
    total_hard_cost = calc.get("total_hard_cost", 0)
    carry_int_base = calc.get("carry_int_base", 0)
    total_indirect_costs = calc.get("total_indirect_costs", 0)
    refi_closing_fee = calc.get("refi_closing_fee", 0)
    total_vertical_soft = calc.get("total_vertical_soft", 0)
    buydown_pts = calc.get("buydown_pts", 0)
    default_buydown_cost = calc.get("default_buydown_cost", 0)
    btr_finance_closing = calc.get("btr_finance_closing", 0)
    developer_margin = calc.get("developer_margin", 0)
    total_const = calc.get("total_const", 0)
    misc_est = calc.get("misc_est", 0)
    mgmt_est = calc.get("mgmt_est", 0)
    tax_est = calc.get("tax_est", 0)
    ins_est = calc.get("ins_est", 0)
    flood_est = calc.get("flood_est", 0)
    lawn_est = calc.get("lawn_est", 0)
    capex_est = calc.get("capex_est", 0)
    net_cash_at_closing = calc.get("net_cash_at_closing", 0)
    target_dscr_rate = calc.get("target_dscr_rate", 1.2)
    vacancy_rate = calc.get("vacancy_rate", 0.05)
    cost_calc_mode = calc.get("cost_calc_mode", "")
    reference_price = calc.get("reference_price", 0)
    profit_margin_pct = calc.get("profit_margin_pct", 0)
    overhead_pct = calc.get("overhead_pct", 0)
    sales_pct = calc.get("sales_pct", 0)
    finance_pct = calc.get("finance_pct", 0)
    total_construction_budget = calc.get("total_construction_budget", 0)
    our_aux_cost_total = calc.get("our_aux_cost_total", 0)
    target_heated_hard_cost = calc.get("target_heated_hard_cost", 0)
    sqft = calc.get("sqft", 0)
    
    # Missing Math Variables
    total_construction_basis = calc.get("total_construction_basis", 0)
    cb_gross_annual_rent = calc.get("cb_gross_annual_rent", 0)
    cb_noi = calc.get("cb_noi", 0)
    total_gross_monthly_income = calc.get("total_gross_monthly_income", 0)
    total_monthly_pi = calc.get("total_monthly_pi", 0)
    monthly_cash_flow = calc.get("monthly_cash_flow", 0)
    actual_dscr = calc.get("actual_dscr", 0)
    monthly_vacancy_loss = calc.get("monthly_vacancy_loss", 0)
    annual_egi = calc.get("annual_egi", 0)
    monthly_mgmt_fee = calc.get("monthly_mgmt_fee", 0)
    mo_other_opex = calc.get("mo_other_opex", 0)
    annual_noi = calc.get("annual_noi", 0)
    annual_mgmt_fee = calc.get("annual_mgmt_fee", 0)
    annual_other_opex = calc.get("annual_other_opex", 0)
    annual_debt_service = calc.get("annual_debt_service", 0)
    dscr_variance = calc.get("dscr_variance", 0)
    net_refi_rate = calc.get("net_refi_rate", 0)
    build_months = calc.get("build_months", 0)
    retail_sales_costs = calc.get("retail_sales_costs", 0)
    retail_total_invested = calc.get("retail_total_invested", 0)
    retail_taxes = calc.get("retail_taxes", 0)
    retail_net_cash = calc.get("retail_net_cash", 0)
    default_gc_fee = calc.get("default_gc_fee", 0)

    # --- Unpack Texts ---
    executive_summary_text = texts.get("executive_summary_text", "")
    horizontal_summary_text = texts.get("horizontal_summary_text", "")
    granular_summary_text = texts.get("granular_summary_text", "")
    operating_summary_text = texts.get("operating_summary_text", "")
    waterfall_summary_text = texts.get("waterfall_summary_text", "")
    strategy_comparison_text = texts.get("strategy_comparison_text", "")
    strategy_footnote_text = texts.get("strategy_footnote_text", "")
    scaling_intro = texts.get("scaling_intro", "")
    scaling_takeaway = texts.get("scaling_takeaway", "")
    scurve_summary = texts.get("scurve_summary", "")
    stress_test_summary = texts.get("stress_test_summary", "")
    opex_sens_summary = texts.get("opex_sens_summary", "")
    rent_sens_summary = texts.get("rent_sens_summary", "")
    long_term_intro = texts.get("long_term_intro", "")

    # --- Unpack Tables ---
    horizontal_data = tables.get("horizontal_data", {})
    direct_rollup_df = tables.get("direct_rollup_df", pd.DataFrame())
    pdf_granular_data = tables.get("pdf_granular_data", [])
    df_schedule = tables.get("df_schedule", pd.DataFrame())
    df_stress = tables.get("df_stress", pd.DataFrame())
    df_opex_sens = tables.get("df_opex_sens", pd.DataFrame())
    df_rent_sens = tables.get("df_rent_sens", pd.DataFrame())
    projection_data = tables.get("projection_data", {})
    strategy_data = tables.get("strategy_data", {})
    scaling_data = tables.get("scaling_data", {})
    dscr_summary_data = tables.get("dscr_summary_data", {})

    pdf = EnterpriseReport(borrower_name=borrower_name, borrower_company=borrower_company)
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
    clean_summary = executive_summary_text.replace("**Executive Summary:**\n", "").encode('latin-1', 'replace').decode('latin-1')
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

    # 3. HORIZONTAL LAND DEVELOPMENT
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 3. Horizontal Land Development & Lot Basis", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    clean_horiz_summary = horizontal_summary_text.replace("**", "").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_horiz_summary)
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 9)
    pdf.cell(100, 6, "Cost Category", 1, 0, 'C')
    pdf.cell(45, 6, "Total Project Cost", 1, 0, 'C')
    pdf.cell(45, 6, "Cost Per Door", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i in range(len(horizontal_data["Cost Category"])):
        cat = str(horizontal_data["Cost Category"][i])
        tot = str(horizontal_data["Total Project Cost"][i])
        per = str(horizontal_data["Cost Per Door"][i])
        if "TOTAL" in cat or "TARGET" in cat or "CAPTURED" in cat:
            pdf.set_font("Arial", 'B', 8)
            pdf.set_fill_color(240, 240, 240)
            fill = True
        else:
            pdf.set_font("Arial", '', 8)
            fill = False
        pdf.cell(100, 6, cat[:50], 1, 0, 'L', fill=fill)
        pdf.cell(45, 6, tot, 1, 0, 'R', fill=fill)
        pdf.cell(45, 6, per, 1, 1, 'R', fill=fill)
    pdf.ln(5)

    # 4. CONSTRUCTION BUILDUP SELECTION
    if detail_mode == "High-Level Roll-up Only":
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 4. Vertical Direct Hard Cost Master Roll-up", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        clean_gran = granular_summary_text.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_gran)
        pdf.ln(3)
        
        pdf.set_font("Arial", 'B', 9)
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
        pdf.cell(0, 8, " 4. Granular Vertical Direct Hard Cost Buildup", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        clean_gran = granular_summary_text.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_gran)
        pdf.ln(3)
        
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(90, 6, "Division / Trade Level", 1, 0, 'C')
        pdf.cell(30, 6, "Live Cost / SF", 1, 0, 'C')
        pdf.cell(35, 6, f"Per Unit", 1, 0, 'C')
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

    # 5. CONSTRUCTION LENDER LIMITS
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 5. Construction Bank Limits & Loan Cap", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    if const_bank_val_mode == "DSCR Stress Test":
        pdf_dscr_info_text = (
            f"Construction Loan Underwriting: The bank determines the implied asset value based on a "
            f"{const_bank_dscr:.2f}x DSCR stress test (yielding ${bank_stressed_value:,.0f}). "
            f"They apply their {const_bank_ltv*100:.1f}% LTV limit to offer a maximum loan of ${actual_const_loan:,.0f}, "
            f"and subtract that from your Total Basis (${total_construction_basis:,.0f}) to determine your required Day-1 Seed Capital of ${seed_capital:,.0f}."
        )
        pdf.multi_cell(0, 6, pdf_dscr_info_text.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(3)
        pdf.cell(100, 7, "Bank Assumed Rent & Target DSCR:", 0, 0)
        pdf.cell(90, 7, f"${const_bank_rent:,.0f}/mo | {const_bank_dscr:.2f}x DSCR", 0, 1, 'R')
        pdf.cell(100, 7, "Bank Vacancy & OpEx Deductions:", 0, 0)
        pdf.cell(90, 7, f"{const_bank_vac_pct*100:.1f}% Vac | {const_bank_opex_pct*100:.1f}% OpEx", 0, 1, 'R')
        pdf.cell(100, 7, "Bank Implied Asset Value (Refi Stress Test):", 0, 0)
        pdf.cell(90, 7, f"${bank_stressed_value:,.0f}", 0, 1, 'R')
    else:
        pdf_grm_info_text = (
            f"Construction Loan Underwriting: The bank determines the implied asset value based on a "
            f"{const_bank_grm:.1f}x Gross Rent Multiplier (yielding ${bank_stressed_value:,.0f}). "
            f"They apply their {const_bank_ltv*100:.1f}% LTV limit to offer a maximum loan of ${actual_const_loan:,.0f}, "
            f"and subtract that from your Total Basis (${total_construction_basis:,.0f}) to determine your required Day-1 Seed Capital of ${seed_capital:,.0f}."
        )
        pdf.multi_cell(0, 6, pdf_grm_info_text.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(3)
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

    # 6. DEVELOPER CAPITAL & CONSTRUCTION LEDGER
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 6. Developer Capital & Construction Ledger", fill=True, ln=1)
    
    pdf.ln(3)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 6, "Pro Forma Valuation Allocation", 0, 0, 'L')
    pdf.cell(95, 6, "Financing Breakdown", 0, 1, 'L')
    
    pdf.set_font("Arial", '', 9)
    pdf.cell(65, 5, f"Finished Lot Benchmark ({lot_cost_pct*100:.0f}%):", 0, 0, 'L')
    pdf.cell(30, 5, f"${lot_benchmark:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, "Const. Loan Closing Fees:", 0, 0, 'L')
    pdf.cell(30, 5, f"${const_closing_fee:,.0f}", 0, 1, 'R')
    pdf.cell(65, 5, "Adjusted BTR Hard Costs:", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_hard_cost:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, "Carrying Interest:", 0, 0, 'L')
    pdf.cell(30, 5, f"${carry_int_base:,.0f}", 0, 1, 'R')
    pdf.cell(65, 5, "Indirects + GC Fee:", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_indirect_costs:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, "Perm. Takeout Fees:", 0, 0, 'L')
    pdf.cell(30, 5, f"${refi_closing_fee:,.0f}", 0, 1, 'R')
    pdf.cell(65, 5, "On-Lot Utilities & Soft Costs:", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_vertical_soft:,.0f}", 0, 0, 'R')
    pdf.cell(65, 5, f"Rate Buydown ({buydown_pts:.2f} pts):", 0, 0, 'L')
    pdf.cell(30, 5, f"${default_buydown_cost:,.0f}", 0, 1, 'R')
    pdf.cell(65, 5, "Finance, Closing & Buydown:", 0, 0, 'L')
    pdf.cell(30, 5, f"${btr_finance_closing:,.0f}", 0, 1, 'R')
    pdf.cell(65, 5, "Built-in Developer Margin:", 0, 0, 'L')
    pdf.cell(30, 5, f"${developer_margin:,.0f}", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(65, 5, "Total Appraised Value (ARV):", 0, 0, 'L')
    pdf.cell(30, 5, f"${total_arv:,.0f}", 0, 1, 'R')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(50, 6, "Phase / Cash Event", 1, 0, 'C')
    pdf.cell(110, 6, "Transaction Scope", 1, 0, 'C')
    pdf.cell(30, 6, "Outlay", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    transactions = [
        ("1. Horizontal Dev & Land", "Out-of-pocket acquisition and civil infrastructure", f"-${total_land_default:,.0f}"),
        ("2. Vertical Const. Cost", "Baseline Hard Costs + Indirects + Cont. + GC Fee", f"-${total_const:,.0f}"),
        ("3. Taps & Soft Costs", "Water/sewer/electric/gas tie-ins, permits", f"-${total_vertical_soft:,.0f}"),
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

    # 7. OPERATING PERFORMANCE & DSCR
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 7. Operating Performance & DSCR Requirements", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    clean_op_summary = operating_summary_text.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_op_summary)
    pdf.ln(3)

    pdf.set_font("Arial", 'I', 9)
    if misc_est > 0:
        opex_breakdown_str = f"OpEx Breakdown (Estimated): Mgmt ~${mgmt_est:,.0f}/mo, Taxes ~${tax_est:,.0f}/mo, Insurance ~${ins_est:,.0f}/mo, Flood ~${flood_est:,.0f}/mo, Lawn ~${lawn_est:,.0f}/mo, CapEx ~${capex_est:,.0f}/mo, Misc ~${misc_est:,.0f}/mo."
    else:
        opex_breakdown_str = f"OpEx Breakdown (Estimated): Mgmt ~${mgmt_est:,.0f}/mo, Taxes ~${tax_est:,.0f}/mo, Insurance ~${ins_est:,.0f}/mo, Flood ~${flood_est:,.0f}/mo, Lawn ~${lawn_est:,.0f}/mo, CapEx ~${capex_est:,.0f}/mo."
    pdf.multi_cell(0, 6, opex_breakdown_str)
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 9)
    pdf.cell(80, 6, "Pro Forma Line Item", 1, 0, 'C')
    pdf.cell(55, 6, "Monthly", 1, 0, 'C')
    pdf.cell(55, 6, "Annual", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i in range(len(dscr_summary_data["Pro Forma Line Item"])):
        item = str(dscr_summary_data["Pro Forma Line Item"][i])
        mo = str(dscr_summary_data["Monthly"][i])
        yr = str(dscr_summary_data["Annual"][i])
        pdf.cell(80, 6, item, 1, 0, 'L')
        pdf.cell(55, 6, mo, 1, 0, 'R')
        pdf.cell(55, 6, yr, 1, 1, 'R')
    pdf.ln(5)

    # 8. REFINANCE CASH WATERFALL
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 8. Refinance Cash Waterfall (Payoff & Cash-Out)", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    clean_waterfall_summary = waterfall_summary_text.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_waterfall_summary)
    pdf.ln(3)
    
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

    # 9. STRATEGY COMPARISON: RETAIL VS BTR
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 9. Strategy Comparison: Retail Sell vs. Build-to-Rent", ln=1, fill=True)
    pdf.set_font("Arial", '', 9)
    
    pdf.set_font("Arial", '', 10)
    clean_strategy_summary = strategy_comparison_text.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_strategy_summary)
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 9)
    pdf.cell(70, 6, "Financial Metric", 1, 0, 'C')
    pdf.cell(60, 6, "National Builder (Retail Sell)", 1, 0, 'C')
    pdf.cell(60, 6, "Build-to-Rent (DSCR Takeout)", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i in range(len(strategy_data["Financial Metric"])):
        metric = str(strategy_data["Financial Metric"][i])
        retail = str(strategy_data["National Builder (Retail Sell)"][i])
        
        # CORRECTED DICTIONARY KEY MATCH
        btr = str(strategy_data["Build-to-Rent (DSCR Takeout)"][i])
        
        if "(~8% Realtor & concessions)" in retail:
            retail = retail.replace("(~8% Realtor & concessions)", "(8% Fees)")
        if "Estimated Capital Gains Taxes" in metric:
            metric = "Taxes Paid (30%)"
        if "(Taxable Profit)" in retail:
            retail = retail.replace(" (Taxable Profit)", "")
        if "(After-Tax)" in retail:
            retail = retail.replace(" (After-Tax)", "")
        if "(Const. finance, takeout, buydown)" in btr:
            btr = btr.replace("(Const. finance, takeout, buydown)", "(Financing Fees)")
        if "LTV DSCR Loan" in btr:
            btr = btr.replace(" LTV DSCR Loan", " LTV)")
        if "(Seed Capital Retained)" in btr:
            btr = btr.replace("(Seed Capital Retained)", "(Retained)")
        if "(Tax-Free Cash Out)" in btr:
            btr = btr.replace("(Tax-Free Cash Out)", "(Cash Out)")
        if "(Tax-Deferred Refinance)" in btr:
            btr = btr.replace(" (Tax-Deferred Refinance)", "")
            
        pdf.cell(70, 6, metric[:45], 1, 0, 'L')
        pdf.cell(60, 6, retail[:45], 1, 0, 'C')
        pdf.cell(60, 6, btr[:45], 1, 1, 'C')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 8)
    clean_footnote = strategy_footnote_text.replace("*Note: ", "Note: ").replace("*", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, clean_footnote)
    pdf.ln(5)
    
    # 10. MULTI-UNIT PHASE & ANNUAL PROGRAM ANALYSIS
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 10. Multi-Unit Phase & Annual Program Analysis", ln=1, fill=True)
    
    pdf.set_font("Arial", '', 10)
    clean_scaling_intro = scaling_intro.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_scaling_intro)
    pdf.ln(3)

    pdf.set_font("Arial", 'B', 8)
    pdf.cell(50, 6, "Portfolio Metric", 1, 0, 'C')
    pdf.cell(40, 6, "1-House Baseline", 1, 0, 'C')
    pdf.cell(40, 6, "3-House Phase", 1, 0, 'C')
    pdf.cell(40, 6, "6-House Annual", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 7)
    for i in range(len(scaling_data["Portfolio Metric"])):
        metric = str(scaling_data["Portfolio Metric"][i])
        val1 = str(scaling_data["Single-House Baseline"][i])
        val3 = str(scaling_data["3-House Simultaneous Phase"][i])
        val6 = str(scaling_data["6-House Annual Build (Year 1)"][i])
        
        metric = metric.replace("Permanent Commercial Loan Proceeds", "Takeout Loan Proceeds")
        metric = metric.replace("Total Retained Asset Equity", "Retained Asset Equity")
        
        pdf.cell(50, 6, metric[:40], 1, 0, 'L')
        pdf.cell(40, 6, val1[:30], 1, 0, 'C')
        pdf.cell(40, 6, val3[:30], 1, 0, 'C')
        pdf.cell(40, 6, val6[:30], 1, 1, 'C')
        
    pdf.ln(4)
    pdf.set_font("Arial", 'I', 9)
    clean_scaling_takeaway = scaling_takeaway.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, clean_scaling_takeaway)
    pdf.ln(5)

    # 11. ENTERPRISE S-CURVE DRAW SCHEDULE
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 11. Enterprise S-Curve Draw Schedule", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    clean_scurve_summary = scurve_summary.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_scurve_summary)
    pdf.ln(3)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(30, 6, "Month", 1, 0, 'C')
    pdf.cell(40, 6, "Cum. % Complete", 1, 0, 'C')
    pdf.cell(40, 6, "Monthly Draw", 1, 0, 'C')
    pdf.cell(40, 6, "Capitalized Int.", 1, 0, 'C')
    pdf.cell(40, 6, "Total Drawn Bal.", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 9)
    for i, row in df_schedule.iterrows():
        pdf.cell(30, 6, str(row["Month"]), 1, 0, 'C')
        pdf.cell(40, 6, str(row["Cum. % Complete"]), 1, 0, 'C')
        pdf.cell(40, 6, f"${row['Monthly Draw ($)']:,.0f}", 1, 0, 'R')
        pdf.cell(40, 6, f"${row['Capitalized Interest ($)']:,.0f}", 1, 0, 'R')
        pdf.cell(40, 6, f"${row['Total Drawn Balance ($)']:,.0f}", 1, 1, 'R')
    pdf.ln(5)
    
    # 12. SENSITIVITY ANALYSIS (STRESS TEST)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 12. Sensitivity Analysis (Stress Testing)", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    clean_stress_summary = stress_test_summary.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_stress_summary)
    pdf.ln(3)
    
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(60, 6, "Stress Scenario", 1, 0, 'C')
    pdf.cell(25, 6, "Final ARV", 1, 0, 'C')
    pdf.cell(20, 6, "Refi Rate", 1, 0, 'C')
    pdf.cell(25, 6, "DSCR Status", 1, 0, 'C')
    pdf.cell(35, 6, "Net Cash Surplus", 1, 0, 'C')
    pdf.cell(30, 6, "Day-1 Wealth", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i, row in df_stress.iterrows():
        dscr_clean = str(row["DSCR Status"]).replace("🟢 ", "").replace("🔴 ", "")
        surplus_clean = str(row["Net Cash Surplus / (Trapped)"]).replace("🟢 ", "").replace("🔴 ", "")
        
        pdf.cell(60, 6, str(row["Stress Scenario"])[:35], 1, 0, 'L')
        pdf.cell(25, 6, str(row["Final ARV"]), 1, 0, 'C')
        pdf.cell(20, 6, str(row["Refi Rate"]), 1, 0, 'C')
        pdf.cell(25, 6, dscr_clean, 1, 0, 'C')
        pdf.cell(35, 6, surplus_clean, 1, 0, 'R')
        pdf.cell(30, 6, str(row["Total Day-1 Wealth"]), 1, 1, 'R')
    pdf.ln(5)

    # 13. OPERATING EXPENSE (OPEX) SENSITIVITY
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 13. Operating Expense (OpEx) Sensitivity", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    clean_opex_summary = opex_sens_summary.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_opex_summary)
    pdf.ln(3)
    
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(25, 6, "OpEx Rate", 1, 0, 'C')
    pdf.cell(25, 6, "Mo. OpEx", 1, 0, 'C')
    pdf.cell(25, 6, "NOI", 1, 0, 'C')
    pdf.cell(25, 6, "Mo. P&I", 1, 0, 'C')
    pdf.cell(20, 6, "DSCR", 1, 0, 'C')
    pdf.cell(75, 6, f"Underwriting Status (Target: {target_dscr_rate:.2f}x)", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i, row in df_opex_sens.iterrows():
        pdf.cell(25, 6, str(row["OpEx Rate"]), 1, 0, 'C')
        pdf.cell(25, 6, str(row["Monthly OpEx"]), 1, 0, 'C')
        pdf.cell(25, 6, str(row["NOI"]), 1, 0, 'C')
        pdf.cell(25, 6, str(row["Monthly P&I"]), 1, 0, 'C')
        pdf.cell(20, 6, str(row["Resulting DSCR"]), 1, 0, 'C')
        status_clean = str(row[f"Underwriting Status (Target: {target_dscr_rate:.2f}x)"])[:45]
        pdf.cell(75, 6, status_clean, 1, 1, 'C')
    pdf.ln(5)

    # 14. GROSS RENT SENSITIVITY MATRIX
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 14. Gross Rent Sensitivity Matrix", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    clean_rent_summary = rent_sens_summary.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_rent_summary)
    pdf.ln(3)
    
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(25, 6, "Gross Rent", 1, 0, 'C')
    pdf.cell(25, 6, "Vacancy", 1, 0, 'C')
    pdf.cell(25, 6, "OpEx", 1, 0, 'C')
    pdf.cell(25, 6, "Mo. NOI", 1, 0, 'C')
    pdf.cell(25, 6, "DSCR", 1, 0, 'C')
    pdf.cell(40, 6, "Net Mo. Cash Flow", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i, row in df_rent_sens.iterrows():
        rent_clean = str(row["Gross Rent"]).replace(" (Target)", "")
        vac_col = [c for c in df_rent_sens.columns if "Vacancy" in c][0]
        
        pdf.cell(25, 6, rent_clean, 1, 0, 'C')
        pdf.cell(25, 6, str(row[vac_col]), 1, 0, 'C')
        pdf.cell(25, 6, str(row["OpEx"]), 1, 0, 'C')
        pdf.cell(25, 6, str(row["Monthly NOI"]), 1, 0, 'C')
        pdf.cell(25, 6, str(row["Commercial DSCR"]), 1, 0, 'C')
        pdf.cell(40, 6, str(row["Net Monthly Cash Flow"]), 1, 1, 'C')
    pdf.ln(5)

    # 15. REVERSE-ENGINEERING BREAKDOWN
    if cost_calc_mode in ["Reverse-Engineer from Appraisal", "Reverse-Engineer from Primary Comp"]:
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 8, " 15. Retail Comp & Appraisal Reverse-Engineering", ln=1, fill=True)
        pdf.set_font("Arial", '', 10)
        
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
        
        pdf.cell(130, 7, "(-) Indirects (Permits, Temp Site, Cont, GC Fee):", 0, 0)
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
        
    # 16. LONG-TERM PORTFOLIO WEALTH
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 16. Long-Term Portfolio Wealth (IRR & ROI)", ln=1, fill=True)
    pdf.set_font("Arial", '', 10)
    
    clean_long_term = long_term_intro.replace("**", "").replace(r"\$", "$").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_long_term)
    pdf.ln(3)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(85, 6, "Metric", 1, 0, 'C')
    pdf.cell(35, 6, "Year 1", 1, 0, 'C')
    pdf.cell(35, 6, "Year 5", 1, 0, 'C')
    pdf.cell(35, 6, "Year 10", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for i in range(len(projection_data["Metric"])):
        metric = str(projection_data["Metric"][i])
        y1 = str(projection_data["Year 1"][i])
        y5 = str(projection_data["Year 5"][i])
        y10 = str(projection_data["Year 10"][i])
        
        pdf.cell(85, 6, metric[:45], 1, 0, 'L')
        pdf.cell(35, 6, y1, 1, 0, 'C')
        pdf.cell(35, 6, y5, 1, 0, 'C')
        pdf.cell(35, 6, y10, 1, 1, 'C')
    pdf.ln(5)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

def create_lender_letter_pdf(letter_type, ui, calc):
    borrower_company = ui.get('borrower_company', '')
    borrower_address = ui.get('borrower_address', '')
    borrower_phone = ui.get('borrower_phone', '')
    borrower_email = ui.get('borrower_email', '')
    report_date = ui.get('report_date', '')
    project_address = ui.get('project_address', '')
    borrower_name = ui.get('borrower_name', '')
    
    units = calc.get('units', 1)
    actual_const_loan = calc.get('actual_const_loan', 0)
    seed_capital = calc.get('seed_capital', 0)
    total_project_basis = calc.get('total_project_basis', 0)
    total_arv = calc.get('total_arv', 0)
    const_ltv = calc.get('const_ltv', 0)
    build_months = calc.get('build_months', 0)
    loan_total = calc.get('loan_total', 0)
    refi_ltv = calc.get('refi_ltv', 0)
    annual_noi = calc.get('annual_noi', 0)
    actual_dscr = calc.get('actual_dscr', 0)
    total_gross_monthly_income = calc.get('total_gross_monthly_income', 0)
    monthly_cash_flow = calc.get('monthly_cash_flow', 0)
    net_refi_rate = calc.get('net_refi_rate', 0)
    
    const_bank_name = ui.get('const_bank_name', 'Local Regional Bank')
    const_bank_contact = ui.get('const_bank_contact', 'Commercial Loan Officer')
    refi_bank_name = ui.get('refi_bank_name', 'National DSCR Lender')
    refi_bank_contact = ui.get('refi_bank_contact', 'Takeout Underwriter')

    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.set_margins(left=12.7, top=12.7, right=12.7)
    pdf.set_auto_page_break(auto=True, margin=12.7)
    pdf.add_page()
    
    try:
        if os.path.exists("Gemini_Generated_Image_.png"):
            pdf.image("Gemini_Generated_Image_.png", x=12.7, y=10, w=40)
    except Exception:
        pass
    
    pdf.set_y(12)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 5, borrower_company.upper(), ln=1, align='R')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, borrower_address, ln=1, align='R')
    if borrower_phone or borrower_email:
        contact_str = f"{borrower_phone} | {borrower_email}".strip(" | ")
        pdf.cell(0, 5, contact_str, ln=1, align='R')
    
    pdf.ln(15) 
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, f"Date: {report_date}", ln=1)
    pdf.ln(6) 
    
    if letter_type == "Construction":
        subject = f"Construction Financing Proposal - Build-to-Rent (BTR) Development at {project_address if project_address else '[Subject Property]'}"
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, f"To: {const_bank_contact}", ln=1)
        pdf.cell(0, 5, f"Company: {const_bank_name}", ln=1)
        pdf.ln(4)
        
        pdf.cell(0, 5, f"RE: {subject}", ln=1)
        pdf.line(12.7, pdf.get_y(), 203.3, pdf.get_y())
        pdf.ln(8) 
        
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 5, f"Dear {const_bank_contact},", ln=1)
        pdf.ln(6) 
        
        p1 = f"{borrower_company} respectfully submits this funding proposal for the vertical and horizontal development of a purpose-built, {units}-unit Build-to-Rent (BTR) asset located at {project_address if project_address else 'the subject property'}."
        pdf.multi_cell(0, 5, p1.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(2)
        
        p2 = f"To execute this project, we are requesting a construction debt facility of ${actual_const_loan:,.0f}. The project is underwritten with a highly favorable cost basis, allowing us to fully collateralize the facility and meet all lender reserve requirements with ${seed_capital:,.0f} in Day-1 cash equity required at closing."
        pdf.multi_cell(0, 5, p2.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(6) 
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, "Project & Facility Highlights:", ln=1)
        pdf.set_font('Arial', '', 11)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Requested Loan Amount: ${actual_const_loan:,.0f}", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Total Capital Basis: ${total_project_basis:,.0f}", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Projected As-Repaired Value (ARV): ${total_arv:,.0f}", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Target Leverage: {const_ltv*100:.1f}% Loan-to-Cost (LTC)", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Construction Lifecycle: {build_months} Months", ln=1)
        pdf.ln(6) 
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, "Exit Strategy:", ln=1)
        pdf.set_font('Arial', '', 11)
        p3 = f"Upon issuance of the Certificate of Occupancy and subsequent tenant placement, our defined exit strategy is to execute a commercial Debt Service Coverage Ratio (DSCR) takeout refinance. This will return the construction facility's principal while allowing {borrower_company} to retain and manage the stabilized asset long-term within our corporate portfolio."
        pdf.multi_cell(0, 5, p3.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(2)
        
        p4 = f"To support your underwriting process, please find the enclosed comprehensive reporting package, which includes our algorithmic pro forma model, a granular direct hard-cost breakdown, and the projected S-Curve capital drawdown schedule."
        pdf.multi_cell(0, 5, p4.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(3)

    else:
        subject = f"Permanent Commercial Refinance Takeout - Stabilized Asset at {project_address if project_address else '[Subject Property]'}"
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, f"To: {refi_bank_contact}", ln=1)
        pdf.cell(0, 5, f"Company: {refi_bank_name}", ln=1)
        pdf.ln(4)
        
        pdf.cell(0, 5, f"RE: {subject}", ln=1)
        pdf.line(12.7, pdf.get_y(), 203.3, pdf.get_y())
        pdf.ln(8)
        
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 5, f"Dear {refi_bank_contact},", ln=1)
        pdf.ln(6)
        
        p1 = f"{borrower_company} respectfully submits this permanent financing proposal to secure a commercial Debt Service Coverage Ratio (DSCR) takeout facility for our newly stabilized, purpose-built {units}-unit Build-to-Rent (BTR) asset located at {project_address if project_address else 'the subject property'}."
        pdf.multi_cell(0, 5, p1.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(2)
        
        p2 = f"The objective of this facility is to execute a strategic refinance of the asset's original construction debt, locking in long-term permanent financing at a requested loan amount of ${loan_total:,.0f}. Having successfully navigated the development and stabilization phases, the asset now operates at peak efficiency with a proven, highly favorable cost basis."
        pdf.multi_cell(0, 5, p2.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(6) 
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 5, "Stabilized Asset & Facility Highlights:", ln=1)
        pdf.set_font('Arial', '', 11)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Requested Loan Amount: ${loan_total:,.0f}", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Stabilized Appraised Value (ARV): ${total_arv:,.0f}", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Target Leverage: {refi_ltv*100:.1f}% Loan-to-Value (LTV)", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Net Operating Income (NOI): ${annual_noi:,.0f} / year", ln=1)
        pdf.cell(5, 5, "")
        pdf.cell(0, 5, f"- Underwritten DSCR: {actual_dscr:.2f}x", ln=1)
        pdf.ln(4)
        
        p3 = f"This asset delivers institutional-grade operating metrics. Upon stabilization, the property generates ${total_gross_monthly_income:,.0f} in top-line monthly revenue. Operating at a compliant {actual_dscr:.2f}x DSCR against debt service modeled at {net_refi_rate*100:.3f}%, the portfolio yields an exceptionally resilient Net Operating Income (NOI), allowing for strong risk-adjusted coverage and producing ${monthly_cash_flow:,.0f} in unencumbered free cash flow every month."
        pdf.multi_cell(0, 5, p3.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(2)
        
        p4 = f"To expedite your firm's underwriting and due diligence, we have enclosed a comprehensive pro forma reporting package. This includes our fully stabilized operating ledger, itemized OpEx schedules, and a transparent capitalization audit."
        pdf.multi_cell(0, 5, p4.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(3)

    pdf.multi_cell(0, 5, "Thank you for your time, review, and continued partnership. We look forward to discussing this facility with your committee in further detail.")
    
    pdf.ln(6)
    pdf.cell(0, 5, "Sincerely,", ln=1)
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, borrower_name, ln=1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, f"Principal, {borrower_company}", ln=1)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()
