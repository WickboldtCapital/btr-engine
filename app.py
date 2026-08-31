def create_slide_pdf():
    # Landscape orientation, millimeters, Letter size
    pdf = FPDF(orientation='L', unit='mm', format='Letter')
    
    # 1. Title Slide
    pdf.add_page()
    pdf.set_font('Arial', 'B', 28)
    pdf.cell(0, 40, '', ln=1) # Vertical Spacer
    pdf.cell(0, 15, 'Wickboldt Capital | BTR Pro Forma Analysis', align='C', ln=1)
    pdf.set_font('Arial', 'I', 16)
    pdf.cell(0, 10, f"Project: {project_name if project_name else 'TBD'}", align='C', ln=1)
    pdf.cell(0, 10, f"Address: {project_address if project_address else 'TBD'}", align='C', ln=1)
    pdf.cell(0, 10, f"Prepared: {report_date}", align='C', ln=1)
    
    # 2. Exec Summary
    pdf.add_page()
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, 'Executive Summary', ln=1)
    pdf.line(10, 30, 270, 30) # Separator line
    pdf.set_font('Arial', '', 18)
    pdf.ln(10)
    pdf.cell(0, 12, f"- Project Scale: {units} Unit(s)", ln=1)
    pdf.cell(0, 12, f"- Total Appraised Value (ARV): ${total_arv:,.0f}", ln=1)
    pdf.cell(0, 12, f"- Total Project Basis: ${total_project_basis:,.0f}", ln=1)
    pdf.cell(0, 12, f"- Built-in Developer Margin: ${developer_margin:,.0f}", ln=1)
    cash_text = f"- Net Cash Surplus at Refi: ${cash_surplus:,.0f}" if cash_surplus >= 0 else f"- Retained Seed Capital: ${-cash_surplus:,.0f}"
    pdf.cell(0, 12, cash_text, ln=1)
    
    # 3. Operating Metrics
    pdf.add_page()
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, 'Operating & DSCR Metrics', ln=1)
    pdf.line(10, 30, 270, 30)
    pdf.set_font('Arial', '', 18)
    pdf.ln(10)
    pdf.cell(0, 12, f"- Gross Monthly Income: ${total_gross_monthly_income:,.0f}", ln=1)
    pdf.cell(0, 12, f"- Net Operating Income (NOI): ${annual_noi/12:,.0f} / mo", ln=1)
    pdf.cell(0, 12, f"- Permanent Debt Service (P&I): ${total_monthly_pi:,.0f} / mo", ln=1)
    pdf.cell(0, 12, f"- Monthly Net Cash Flow: ${monthly_cash_flow:,.0f} (${monthly_cash_flow_per_door:,.0f} per door)", ln=1)
    pdf.cell(0, 12, f"- Actual DSCR: {actual_dscr:.2f}x (Target: {target_dscr_rate:.2f}x)", ln=1)
    
    # 4. Capital Ledger
    pdf.add_page()
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, 'Capital Outlay Breakdown', ln=1)
    pdf.line(10, 30, 270, 30)
    pdf.set_font('Arial', '', 18)
    pdf.ln(10)
    pdf.cell(0, 12, f"- Horizontal Land Basis: ${total_land_default:,.0f}", ln=1)
    pdf.cell(0, 12, f"- Vertical Direct Hard Costs: ${total_hard_cost:,.0f} (${blended_cost_per_sf:.2f} / SF)", ln=1)
    pdf.cell(0, 12, f"- Indirects & GC Fee: ${total_indirect_costs:,.0f}", ln=1)
    pdf.cell(0, 12, f"- Soft Costs & Utilities: ${total_vertical_soft:,.0f}", ln=1)
    pdf.cell(0, 12, f"- Financing & Closing Costs: ${btr_finance_closing:,.0f}", ln=1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()
