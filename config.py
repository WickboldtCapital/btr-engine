# config.py

# ==========================================
# --- MASTER DEFAULTS DICTIONARY ---
# ==========================================
HARDCODED_DRIVERS = {
    "units": 1,
    "sqft": 1173,
    "aux_cost_mode": "Percentage of Heated Rate (%)",
    "aux_rate_pct": 50.0,
    "aux_fixed_cost_sf": 35.0,
    "structure_type": "Carport", 
    "struct_sqft": 213,
    "front_porch_sqft": 49,
    "back_porch_sqft": 0,
    "storage_sqft": 49,
    "additional_foundation_cost": 3000,
    
    "gross_monthly_rent": 1600,
    "target_dscr_rate": 1.20,
    "target_min_cashflow_per_door": 200.0,
    "vacancy_rate_pct": 5.0,
    "mgmt_fee_pct": 8.0,
    "opex_entry_mode": "Percentage of EGI (%)",
    "opex_rate_pct": 17.0,
    "opex_taxes_mo": 150.0,
    "opex_ins_mo": 115.0,
    "opex_flood_mo": 30.0,
    "opex_lawn_mo": 50.0,
    "opex_maint_mo": 40.0,
    "opex_misc_mo": 0.0,
    "income_tax_rate_pct": 30.0,
    "appreciation_rate_pct": 3.0,
    
    "const_ltv_pct": 80.0,
    "build_months": 7,
    "const_rate_pct": 7.50,
   
    # Lender Specifics
    "const_bank_name": "Local Regional Bank",
    "const_bank_contact": "Commercial Loan Officer",
    "refi_bank_name": "National DSCR Lender",
    "refi_bank_contact": "Takeout Underwriter",
    
    # Borrower Details
    "borrower_name": "Stephen Wickboldt Jr.",
    "borrower_company": "Wickboldt Capital",
    "borrower_address": "Prairieville, LA",
    "borrower_phone": "(555) 555-5555",
    "borrower_email": "stephen@wickboldtcapital.com",
    
    # Construction Loan Closing Fees
    "const_closing_mode": "Flat Lump Sum",
    "const_closing_fee": 6000,
    "const_origination_fee": 3000.0,
    "const_appraisal_fee": 600.0,
    "const_title_fee": 1200.0,
    "const_survey_fee": 500.0,
    "const_legal_fee": 500.0,
    "const_misc_closing_fee": 200.0,
    
    # Construction Lender Stress Constraints
    "const_bank_rent": 1500,
    "const_bank_ltv_pct": 80.0,
    "const_bank_val_mode": "Gross Rent Multiplier (GRM)",
    "const_bank_grm": 10.0,
    "const_bank_opex_pct": 30.0,
    "const_bank_vac_pct": 5.0,
    "const_bank_dscr": 1.20,
    "const_bank_qual_rate_pct": 7.25,
    "const_bank_amort_yrs": 30,
    "reserve_accrual_pct": 100.0,
    
    "refi_ltv_pct": 80.0,
    "refi_term_years": 30,
    "base_refi_rate_pct": 7.00,
    "refi_closing_fee": 5000,
    "apply_buydown": True,
    "buydown_pts": 2.00,
    
    # Soft Costs & Fees
    "indirect_permits_pct": 4.5,
    "indirect_temp_facilities_pct": 3.5,
    "contingency_pct": 5.0,
    "gc_fee_mode": "Percentage of Hard Costs (%)",
    "gc_fee_pct": 7.0,
    "custom_gc_fee": 20000,
    
    # Horizontal Parametric Development
    "land_entry_mode": "Flat Lump Sum per Lot",
    "site_type_mode": "Auto-Calc LF (Based on Lot Frontage)",
    "manual_infra_lf": 0.0,
    "land_basis": 10000,
    "land_raw_cost": 50000,
    "frontage_per_lot": 50.0,
    "lot_depth": 120.0,
    "road_width": 24.0,
    "road_layout": "Double-Sided Street (Yields 2 Lots per LF)",
    "lot_fill_inches": 12,
    "road_fill_inches": 10,
    "fill_cost_cy": 18.0,
    "clearing_per_lot": 3000.0,
    "paving_type": "Concrete",
    "paving_cost_lf": 125.0,
    "drainage_type": "Curb & Subsurface Catch Basins",
    "drainage_cost_lf": 85.0,
    "water_main_lf": 45.0,
    "sewer_main_lf": 65.0,
    "electric_main_lf": 35.0,
    "gas_main_lf": 20.0,
    "detention_pond": 15000.0,
    "site_amenities": 4500.0,
    
    # Vertical Hookups / Tap Fees
    "water_tap_fee": 1500.0,
    "sewer_tie_in": 1500.0,
    "electric_drop": 1000.0,
    "gas_lateral": 0.0,
    "impact_fees": 500.0,
    
    "appraisal_mode": "Income Approach (DSCR Loan Sizing)",
    "target_grm": 10.0,
    
    # NAHB & Indirect Cost Breakdowns
    "cost_calc_mode": "Reverse-Engineer from Primary Comp",
    "base_direct_cost_sf": 75.0,
    "lot_cost_pct": 13.7,
    "profit_margin_pct": 11.0,
    "overhead_pct": 5.7,
    "sales_pct": 3.6,
    "finance_pct": 1.5,
    
    "comp_address": "",
    "comp_price": 195000,
    "comp_heated_sf": 1275,
    "comp_struct_sf": 213,
    "comp_front_sf": 49,
    "comp_back_sf": 49,
    "comp_storage_sf": 0,
    
    "refi_points_pct": 3.0,       # Default lender discount points for 6.99% pricing
    "amortization_type": "Interest-Only (10-Yr IO Rider)",
    "refi_bundle_mode": "Standard Fixed ($6,500)",
    "manual_refi_bundle": 6500.0,}


# ==========================================
# --- NAHB 36-COMPONENT TRADE MAPPINGS ---
# ==========================================
NAHB_HEATED_DIVS = [
    ("I. SITE WORK", 7.6, True),
    ("- Building Permit Fees", 1.8, False),
    ("- Impact Fee", 1.5, False),
    ("- Water & Sewer Fees / Inspections", 1.5, False),
    ("- Architecture & Engineering", 1.5, False),
    ("- Site Work - Other", 1.3, False),

    ("II. FOUNDATIONS", 10.5, True),
    ("- Excavation, Foundation, Concrete, Backfill", 10.0, False),
    ("- Foundations - Other", 0.5, False),

    ("III. FRAMING", 16.6, True),
    ("- Framing (including roof)", 11.6, False),
    ("- Trusses", 3.0, False),
    ("- Sheathing", 1.5, False),
    ("- General Metal, Steel", 0.4, False),
    ("- Framing - Other", 0.1, False),

    ("IV. EXTERIOR FINISHES", 13.4, True),
    ("- Exterior Wall Finish", 5.7, False),
    ("- Roofing", 3.9, False),
    ("- Windows and Doors (incl. garage door)", 3.7, False),
    ("- Exterior Finishes - Other", 0.1, False),

    ("V. MAJOR SYSTEMS ROUGH-INS", 19.2, True),
    ("- Plumbing (except fixtures)", 6.3, False),
    ("- Electrical (except fixtures)", 6.4, False),
    ("- HVAC", 6.3, False),
    ("- Major Systems - Other", 0.2, False),

    ("VI. INTERIOR FINISHES", 24.1, True),
    ("- Insulation", 1.6, False),
    ("- Drywall", 3.3, False),
    ("- Interior Trims, Doors, and Mirrors", 3.0, False),
    ("- Painting", 2.6, False),
    ("- Lighting", 1.3, False),
    ("- Cabinets, Countertops", 4.4, False),
    ("- Appliances", 1.7, False),
    ("- Flooring", 3.6, False),
    ("- Plumbing Fixtures", 1.8, False),
    ("- Fireplace", 0.6, False),
    ("- Interior Finishes - Other", 0.2, False),

    ("VII. FINAL STEPS", 6.5, True),
    ("- Landscaping", 2.2, False),
    ("- Outdoor Structures (deck, patio, porches)", 1.1, False),
    ("- Driveway", 2.3, False),
    ("- Clean Up", 0.9, False),

    ("VIII. OTHER", 2.1, True),
    ("- Miscellaneous / Other", 2.1, False),
]

NAHB_STRUCT_DIVS = [("AUXILIARY: CARPORT / GARAGE", 35.00, True)]


# ==========================================
# --- STRESS TESTING SCENARIOS ---
# ==========================================
STRESS_SCENARIOS = [
    {"Name": "1. Baseline Target (Pro Forma)", "ARV_Shift": 0.0, "Rate_Shift": 0.0, "Delay": 0},
    {"Name": "2. Mild Rate Hike (+0.50%)", "ARV_Shift": 0.0, "Rate_Shift": 0.005, "Delay": 0},
    {"Name": "3. Severe Rate Hike (+1.00%)", "ARV_Shift": 0.0, "Rate_Shift": 0.01, "Delay": 0},
    {"Name": "4. Mild Appraisal Miss (-5%)", "ARV_Shift": -0.05, "Rate_Shift": 0.0, "Delay": 0},
    {"Name": "5. Severe Appraisal Miss (-10%)", "ARV_Shift": -0.10, "Rate_Shift": 0.0, "Delay": 0},
    {"Name": "6. Supply Chain Delay (+2 Months)", "ARV_Shift": 0.0, "Rate_Shift": 0.0, "Delay": 2},
    {"Name": "7. The Perfect Storm (-10% ARV, +1% Rate, +2 Mos)", "ARV_Shift": -0.10, "Rate_Shift": 0.01, "Delay": 2},
]
