import os
import tempfile
from fpdf import FPDF

class TechnicalBriefReport(FPDF):
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
        self.cell(0, 5, "Master Development Technical Briefs", ln=1, align='R')
        self.ln(10)
        self.line(12.7, self.get_y(), 203.3, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | Confidential & Proprietary - {self.borrower_company}', 0, 0, 'C')

def create_tb1_lvp_pdf(ui):
    company = ui.get('borrower_company', 'Wickboldt Capital')
    name = ui.get('borrower_name', 'Stephen J. Wickboldt, Jr.')

    pdf = TechnicalBriefReport(borrower_name=name, borrower_company=company, orientation='P', unit='mm', format='Letter')
    pdf.set_margins(12.7, 12.7, 12.7)
    pdf.set_auto_page_break(auto=True, margin=15.0)
    pdf.add_page()
    
    # --- TITLE ---
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, "Technical Brief 1: Comprehensive LVP Wear Layer Financial Break-Even", ln=1, align='L')
    pdf.ln(2)
    
    # --- INTRO ---
    pdf.set_font('Arial', '', 11)
    intro = "To substantiate the long-term capital expenditure efficiency specified in Section 7, the following financial break-even analysis evaluates 12 mil versus 20 mil luxury vinyl plank (LVP) flooring over a conservative 15-year holding period based on average 2026 industry costs."
    pdf.multi_cell(0, 5, intro)
    pdf.ln(6)
    
    # --- SECTION 1 ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 1. Cost & Material Assumptions (Per 1,000 Sq. Ft. Baseline)", ln=1, fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.ln(3)
    p1 = "- Material Pricing: 12 mil LVP material is budgeted at $3.00/sq. ft., while commercial-grade 20 mil LVP material is priced at $3.60/sq. ft., representing a $0.60/sq. ft. upfront material premium.\n- Constant Installation & Prep Costs: Professional installation labor ($3.00/sq. ft.), old floor tear-out ($1.50/sq. ft.), and subfloor preparation ($1.50/sq. ft.) remain identical across both tiers at $6.00/sq. ft. combined."
    pdf.multi_cell(0, 5, p1)
    pdf.ln(4)
    
    # Render Table
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(75, 7, "Cost Component", 1, 0, 'L')
    pdf.cell(55, 7, "12 Mil Option (per sq. ft.)", 1, 0, 'C')
    pdf.cell(55, 7, "20 Mil Option (per sq. ft.)", 1, 1, 'C')
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(75, 7, "Material Cost", 1, 0, 'L')
    pdf.cell(55, 7, "$3.00", 1, 0, 'C')
    pdf.cell(55, 7, "$3.60", 1, 1, 'C')
    
    pdf.cell(75, 7, "Labor, Tear-Out & Prep", 1, 0, 'L')
    pdf.cell(55, 7, "$6.00", 1, 0, 'C')
    pdf.cell(55, 7, "$6.00", 1, 1, 'C')
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(75, 7, "Total Fully Installed Cost", 1, 0, 'L')
    pdf.cell(55, 7, "$9.00", 1, 0, 'C')
    pdf.cell(55, 7, "$9.60", 1, 1, 'C')
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(75, 7, "Total Cost for 1,000 Sq. Ft.", 1, 0, 'L', fill=True)
    pdf.cell(55, 7, "$9,000", 1, 0, 'C', fill=True)
    pdf.cell(55, 7, "$9,600", 1, 1, 'C', fill=True)
    pdf.ln(6)

    # --- SECTION 2 ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 2. Lifecycle Cost Comparison (15-Year Horizon)", ln=1, fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.ln(3)
    p2 = "Because a 12 mil floor must be completely replaced every 5 years in a rental property due to rapid tenant turnover, pet claws, and rough treatment, it requires three separate installations over a 15-year investment period ($9,000 x 3 = $27,000 total lifecycle cost). In contrast, a commercial-grade 20 mil floor lasts 12 years under the same conditions, requiring only one mid-cycle replacement at Year 12 ($9,600 x 2 = $19,200 total lifecycle cost), with 9 years of residual life remaining at year 15."
    pdf.multi_cell(0, 5, p2)
    pdf.ln(6)

    # --- SECTION 3 ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 3. Break-Even Point & Return Calculation", ln=1, fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(55, 6, "Upfront Cost Premium:", 0, 0, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, "The upfront cost premium to buy the 20 mil flooring instead of the 12 mil tier", 0, 1, 'L')
    pdf.cell(55, 6, "", 0, 0, 'L')
    pdf.cell(0, 6, "is exactly $600 ($9,600 - $9,000).", 0, 1, 'L')
    pdf.ln(3)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, "Annualized Run Rates:", ln=1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(5, 6, "")
    pdf.cell(0, 6, "- 12 Mil Annual Cost: $9,000 / 5 years = $1,800 / year", ln=1)
    pdf.cell(5, 6, "")
    pdf.cell(0, 6, "- 20 Mil Annual Cost: $9,600 / 12 years = $800 / year", ln=1)
    pdf.cell(5, 6, "")
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, "- Annual Savings: $1,800 - $800 = $1,000 / year", ln=1)
    pdf.ln(3)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(55, 6, "Break-Even Formula:", 0, 0, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, "Upfront Cost Premium ($600) / Annual Savings ($1,000) = 0.6 Years (approx. 7.2 Months).", 0, 1, 'L')
    pdf.ln(4)

    # Conclusion Box
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, "Conclusion:", 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 11)
    conc = "The 20 mil flooring breaks even just 7 months into the first tenancy. Everything after that point is pure, preserved rental profit that protects net operating income over the asset lifecycle."
    pdf.multi_cell(0, 6, conc, fill=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

def create_tb2_shower_pdf(ui):
    company = ui.get('borrower_company', 'Wickboldt Capital')
    name = ui.get('borrower_name', 'Stephen J. Wickboldt, Jr.')

    pdf = TechnicalBriefReport(borrower_name=name, borrower_company=company, orientation='P', unit='mm', format='Letter')
    pdf.set_margins(12.7, 12.7, 12.7)
    pdf.set_auto_page_break(auto=True, margin=15.0)
    pdf.add_page()
    
    # --- TITLE ---
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 8, "Technical Brief 2: Shower Enclosures vs. Custom Tile Financial & Premium Rent Analysis", ln=1, align='L')
    pdf.ln(2)
    
    # --- INTRO ---
    pdf.set_font('Arial', '', 11)
    intro = "To evaluate the long-term capital expenditure efficiency, tenant retention impact, and rental income premiums across the 24-lot portfolio, the following financial break-even analysis compares standard prefabricated acrylic shower enclosures against premium, custom-tiled upgraded showers over a 15-year holding period."
    pdf.multi_cell(0, 5, intro)
    pdf.ln(6)
    
    # --- SECTION 1 ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 1. Cost, Material & Income Assumptions (Per Unit Baseline)", ln=1, fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.ln(3)
    p1 = "- Prefabricated Acrylic Enclosure: Initial material and professional installation cost is budgeted at $1,200.00 per unit. Standard acrylic units are prone to caulking failures, seam leaks, and bottom-pan flexing in rental environments.\n\n- Upgraded Custom Tile Shower: Initial material, cement backer board, waterproofing membrane, and skilled tile-setting labor total $3,800.00 per unit, representing an upfront cost premium of $2,600.00.\n\n- Premium Rental Income Generation: High-end custom tile showers elevate perceived property value in university-adjacent and workforce rental markets, directly supporting a projected monthly rental premium of $50.00 to $75.00 ($600 to $900 annually per unit).\n\n- Maintenance & Leak Risk: Prefabricated units typically incur recurring minor service calls for re-caulking every 2-3 years, with complete unit replacement required around Year 7. Upgraded tile showers feature continuous waterproofing membranes that eliminate subfloor water damage and boast a 15+ year lifespan."
    pdf.multi_cell(0, 5, p1.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(6)

    # --- SECTION 2 ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 2. Lifecycle Cost Comparison (15-Year Horizon)", ln=1, fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.ln(3)
    p2 = "Prefabricated enclosures require complete rip-out and replacement every 7 years, necessitating two full installations over a 15-year period ($1,200 initial + $1,400 replacement/demo labor = $2,600 total lifecycle cost per unit). In contrast, a properly waterproofed custom tile shower lasts the full holding period without structural replacement, requiring zero mid-cycle rebuilds over 15 years ($3,800 total lifecycle cost per unit)."
    pdf.multi_cell(0, 5, p2)
    pdf.ln(6)

    # --- SECTION 3 ---
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, " 3. Break-Even Point & Net Value Return", ln=1, fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.ln(3)
    
    p3 = "- Upfront Cost Premium: The initial capital expenditure premium to install the upgraded tile shower instead of the standard acrylic enclosure is $2,600 - $1,200 = $1,400.00.\n\n- Rapid Payback via Rental Premium: Capturing just a modest $65.00/month rental premium ($780/year) generated by luxury bathroom finishes fully recovers the $1,400 upfront cost premium in less than 22 months (approx. 1.8 years).\n\n- Avoided Failure Savings: Tile showers completely bypass mid-cycle replacement outlays at Year 7 (~$1,400) and eliminate the risk of catastrophic slow framing rot and subfloor water damage (averaging $800 in avoided emergency remediation)."
    pdf.multi_cell(0, 5, p3.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(4)

    # Conclusion Box
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, "Conclusion:", 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 11)
    conc = "Upgraded custom tile showers pay for themselves rapidly through enhanced rental income premiums and avoided maintenance failures, delivering superior durability and maximized net operating income over the portfolio's investment horizon."
    pdf.multi_cell(0, 6, conc, fill=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()
