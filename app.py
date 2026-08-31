# ==========================================
# --- 15. PRESENTATION DECK GENERATION ---
# ==========================================
st.markdown("### 📊 15. Export Presentation Deck (PPTX & PDF)")
st.info("Automatically generates a 4-slide executive summary deck suitable for investor and commercial lender reviews.")

def create_pptx():
    prs = Presentation()
    
    # 1. Title Slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "Wickboldt Capital | BTR Pro Forma Analysis"
    subtitle.text = f"Project: {project_name if project_name else 'TBD'}\nAddress: {project_address if project_address else 'TBD'}\nPrepared: {report_date}"

    # 2. Exec Summary
    bullet_slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(bullet_slide_layout)
    shapes = slide.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    title_shape.text = "Executive Summary"
    tf = body_shape.text_frame
    tf.text = f"Project Scale: {units} Unit(s)"
    
    p = tf.add_paragraph()
    p.text = f"Total Appraised Value (ARV): ${total_arv:,.0f}"
    p = tf.add_paragraph()
    p.text = f"Total Project Basis: ${total_project_basis:,.0f}"
    p = tf.add_paragraph()
    p.text = f"Built-in Developer Margin: ${developer_margin:,.0f}"
    p = tf.add_paragraph()
    p.text = f"Net Cash Surplus at Refi: ${cash_surplus:,.0f}" if cash_surplus >= 0 else f"Retained Seed Capital: ${-cash_surplus:,.0f}"

    # 3. Operating Metrics
    slide = prs.slides.add_slide(bullet_slide_layout)
    shapes = slide.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    title_shape.text = "Operating & DSCR Metrics"
    tf = body_shape.text_frame
    tf.text = f"Gross Monthly Income: ${total_gross_monthly_income:,.0f}"
    
    p = tf.add_paragraph()
    p.text = f"Net Operating Income (NOI): ${annual_noi/12:,.0f} / mo"
    p = tf.add_paragraph()
    p.text = f"Permanent Debt Service (P&I): ${total_monthly_pi:,.0f} / mo"
    p = tf.add_paragraph()
    p.text = f"Monthly Net Cash Flow: ${monthly_cash_flow:,.0f} (${monthly_cash_flow_per_door:,.0f} per door)"
    p = tf.add_paragraph()
    p.text = f"Actual DSCR: {actual_dscr:.2f}x (Target: {target_dscr_rate:.2f}x)"

    # 4. Capital Ledger
    slide = prs.slides.add_slide(bullet_slide_layout)
    shapes = slide.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    title_shape.text = "Capital Outlay Breakdown"
    tf = body_shape.text_frame
    tf.text = f"Horizontal Land Basis: ${total_land_default:,.0f}"
    p = tf.add_paragraph()
    p.text = f"Vertical Direct Hard Costs: ${total_hard_cost:,.0f} (${blended_cost_per_sf:.2f} / SF)"
    p = tf.add_paragraph()
    p.text = f"Indirects & GC Fee: ${total_indirect_costs:,.0f}"
    p = tf.add_paragraph()
    p.text = f"Soft Costs & Utilities: ${total_vertical_soft:,.0f}"
    p = tf.add_paragraph()
    p.text = f"Financing & Closing Costs: ${btr_finance_closing:,.0f}"

    # Save
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        prs.save(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

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
    pdf.cell(0, 12, f"• Project Scale: {units} Unit(s)", ln=1)
    pdf.cell(0, 12, f"• Total Appraised Value (ARV): ${total_arv:,.0f}", ln=1)
    pdf.cell(0, 12, f"• Total Project Basis: ${total_project_basis:,.0f}", ln=1)
    pdf.cell(0, 12, f"• Built-in Developer Margin: ${developer_margin:,.0f}", ln=1)
    cash_text = f"• Net Cash Surplus at Refi: ${cash_surplus:,.0f}" if cash_surplus >= 0 else f"• Retained Seed Capital: ${-cash_surplus:,.0f}"
    pdf.cell(0, 12, cash_text, ln=1)
    
    # 3. Operating Metrics
    pdf.add_page()
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, 'Operating & DSCR Metrics', ln=1)
    pdf.line(10, 30, 270, 30)
    pdf.set_font('Arial', '', 18)
    pdf.ln(10)
    pdf.cell(0, 12, f"• Gross Monthly Income: ${total_gross_monthly_income:,.0f}", ln=1)
    pdf.cell(0, 12, f"• Net Operating Income (NOI): ${annual_noi/12:,.0f} / mo", ln=1)
    pdf.cell(0, 12, f"• Permanent Debt Service (P&I): ${total_monthly_pi:,.0f} / mo", ln=1)
    pdf.cell(0, 12, f"• Monthly Net Cash Flow: ${monthly_cash_flow:,.0f} (${monthly_cash_flow_per_door:,.0f} per door)", ln=1)
    pdf.cell(0, 12, f"• Actual DSCR: {actual_dscr:.2f}x (Target: {target_dscr_rate:.2f}x)", ln=1)
    
    # 4. Capital Ledger
    pdf.add_page()
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, 'Capital Outlay Breakdown', ln=1)
    pdf.line(10, 30, 270, 30)
    pdf.set_font('Arial', '', 18)
    pdf.ln(10)
    pdf.cell(0, 12, f"• Horizontal Land Basis: ${total_land_default:,.0f}", ln=1)
    pdf.cell(0, 12, f"• Vertical Direct Hard Costs: ${total_hard_cost:,.0f} (${blended_cost_per_sf:.2f} / SF)", ln=1)
    pdf.cell(0, 12, f"• Indirects & GC Fee: ${total_indirect_costs:,.0f}", ln=1)
    pdf.cell(0, 12, f"• Soft Costs & Utilities: ${total_vertical_soft:,.0f}", ln=1)
    pdf.cell(0, 12, f"• Financing & Closing Costs: ${btr_finance_closing:,.0f}", ln=1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

col1, col2 = st.columns(2)

with col1:
    st.download_button(
        label="📊 Download Presentation (PowerPoint)",
        data=create_pptx(),
        file_name=f"Wickboldt_Capital_Deck_{report_date.replace(' ', '_').replace(',', '')}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        type="secondary",
        use_container_width=True
    )

with col2:
    st.download_button(
        label="📄 Download Presentation (PDF Slides)",
        data=create_slide_pdf(),
        file_name=f"Wickboldt_Capital_Slide_Deck_{report_date.replace(' ', '_').replace(',', '')}.pdf",
        mime="application/pdf",
        type="secondary",
        use_container_width=True
    )
