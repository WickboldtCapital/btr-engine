import pandas as pd
import math

def format_surplus(val):
    return f"+${val:,.0f}" if val >= 0 else f"-${-val:,.0f}"

def calc_irr(cash_flows):
    if sum(cash_flows) < 0:
        return 0.0
    rate = 0.1
    for _ in range(100):
        npv = sum(cf / (1 + rate)**i for i, cf in enumerate(cash_flows))
        derivative_npv = sum(-i * cf / (1 + rate)**(i + 1) for i, cf in enumerate(cash_flows) if i > 0)
        if abs(npv) < 1e-6:
            return rate
        if derivative_npv == 0:
            break
        rate = rate - npv / derivative_npv
    return rate

def run_underwriting_engine(params, STRESS_SCENARIOS):
    # ==========================================
    # --- 1. SAFE VARIABLE EXTRACTION ---
    # ==========================================
    units = params.get("units", 1)
    sqft = params.get("sqft", 1173)

    gross_monthly_rent = params.get("gross_monthly_rent", 1600)
    vacancy_rate = params.get("vacancy_rate_pct", 5.0) / 100.0

    total_gross_monthly_income = gross_monthly_rent * units
    monthly_vacancy_loss = total_gross_monthly_income * vacancy_rate
    annual_vacancy_loss = monthly_vacancy_loss * 12.0
    effective_gross_monthly_income = total_gross_monthly_income - monthly_vacancy_loss
    annual_egi = effective_gross_monthly_income * 12.0

    mgmt_fee_pct = params.get("mgmt_fee_pct", 8.0) / 100.0
    monthly_mgmt_fee = effective_gross_monthly_income * mgmt_fee_pct
    annual_mgmt_fee = monthly_mgmt_fee * 12.0

    # OpEx extraction
    opex_entry_mode = params.get("opex_entry_mode", "Percentage of EGI (%)")
    if opex_entry_mode == "Percentage of EGI (%)":
        other_opex_rate = params.get("opex_rate_pct", 17.0) / 100.0
        annual_other_opex = annual_egi * other_opex_rate
        
        mo_other_opex = annual_other_opex / 12.0
        tax_est = mo_other_opex * 0.40
        ins_est = mo_other_opex * 0.30
        flood_est = mo_other_opex * 0.05
        lawn_est = mo_other_opex * 0.10
        capex_est = mo_other_opex * 0.15
        misc_est = 0.0
    else:
        tax_est = params.get("opex_taxes_mo", 150.0) * units
        ins_est = params.get("opex_ins_mo", 115.0) * units
        flood_est = params.get("opex_flood_mo", 30.0) * units
        lawn_est = params.get("opex_lawn_mo", 50.0) * units
        capex_est = params.get("opex_maint_mo", 40.0) * units
        misc_est = params.get("opex_misc_mo", 0.0) * units
        
        mo_other_opex = tax_est + ins_est + flood_est + lawn_est + capex_est + misc_est
        annual_other_opex = mo_other_opex * 12.0

    annual_opex = annual_other_opex + annual_mgmt_fee
    mo_opex = annual_opex / 12.0
    mgmt_est = monthly_mgmt_fee
    opex_rate = annual_opex / annual_egi if annual_egi > 0 else 0

    annual_noi = annual_egi - annual_opex
    monthly_noi = annual_noi / 12.0

    # Physical parameters
    aux_cost_mode = params.get("aux_cost_mode", "Percentage of Heated Rate (%)")
    aux_ratio = params.get("aux_rate_pct", 50.0) / 100.0
    aux_fixed_cost_sf = params.get("aux_fixed_cost_sf", 35.0)

    struct_sqft = params.get("struct_sqft", 213)
    front_porch_sqft = params.get("front_porch_sqft", 49)
    back_porch_sqft = params.get("back_porch_sqft", 0)
    storage_sqft = params.get("storage_sqft", 49)
    additional_foundation_cost = params.get("additional_foundation_cost", 3000)

    # General constraints
    target_dscr_rate = params.get("target_dscr_rate", 1.20)
    target_min_cashflow_per_door = params.get("target_min_cashflow_per_door", 200.0)
    income_tax_rate_pct = params.get("income_tax_rate_pct", 30.0) / 100.0
    appreciation_rate = params.get("appreciation_rate_pct", 3.0) / 100.0

    # Lender Params
    const_ltv = params.get("const_ltv_pct", 80.0) / 100.0
    build_months = params.get("build_months", 7)
    
    # Calculate Dynamic Tiered Construction Rate
    raw_const_rate = params.get("const_rate_pct", 7.50) / 100.0
    selected_ltv_for_discount = params.get("const_ltv_pct", 80.0)
    ltv_discount = max(0.0, (80.0 - selected_ltv_for_discount) / 5.0) * 0.005
    const_rate = max(0.01, raw_const_rate - ltv_discount)

    const_closing_mode = params.get("const_closing_mode", "Flat Lump Sum")
    if const_closing_mode == "Detailed Enterprise Breakout":
        const_closing_fee = sum([
            params.get("const_origination_fee", 3000.0),
            params.get("const_appraisal_fee", 600.0),
            params.get("const_title_fee", 1200.0),
            params.get("const_survey_fee", 500.0),
            params.get("const_legal_fee", 500.0),
            params.get("const_misc_closing_fee", 200.0)
        ])
    else:
        const_closing_fee = params.get("const_closing_fee", 6000)

    const_bank_rent = params.get("const_bank_rent", 1500)
    const_bank_ltv = params.get("const_bank_ltv_pct", 80.0) / 100.0
    const_bank_val_mode = params.get("const_bank_val_mode", "Gross Rent Multiplier (GRM)")
    const_bank_grm = params.get("const_bank_grm", 10.0)
    const_bank_opex_pct = params.get("const_bank_opex_pct", 30.0) / 100.0
    const_bank_vac_pct = params.get("const_bank_vac_pct", 5.0) / 100.0
    const_bank_dscr = params.get("const_bank_dscr", 1.20)
    const_bank_qual_rate = params.get("const_bank_qual_rate_pct", 7.25) / 100.0
    const_bank_amort_yrs = params.get("const_bank_amort_yrs", 30)

    refi_ltv = params.get("refi_ltv_pct", 80.0) / 100.0
    refi_term_years = params.get("refi_term_years", 30)
    base_refi_rate = params.get("base_refi_rate_pct", 7.00) / 100.0
    refi_closing_fee = params.get("refi_closing_fee", 5000)
    apply_buydown = params.get("apply_buydown", True)
    buydown_pts = params.get("buydown_pts", 2.00)
    net_refi_rate = max(0.01, base_refi_rate - (buydown_pts * 0.0025)) if apply_buydown else base_refi_rate

    # Builder params
    contingency_pct = params.get("contingency_pct", 5.0) / 100.0
    indirect_permits_pct = params.get("indirect_permits_pct", 4.5) / 100.0
    indirect_temp_facilities_pct = params.get("indirect_temp_facilities_pct", 3.5) / 100.0

    gc_fee_mode = params.get("gc_fee_mode", "Percentage of Hard Costs (%)")
    gc_fee_pct = params.get("gc_fee_pct", 7.0) / 100.0
    custom_gc_fee = params.get("custom_gc_fee", 20000)

    total_vertical_soft = units * sum([
        params.get("water_tap_fee", 1500.0),
        params.get("sewer_tie_in", 1500.0),
        params.get("electric_drop", 1000.0),
        params.get("gas_lateral", 0.0),
        params.get("impact_fees", 500.0)
    ])

    # ==========================================
    # --- 2. LAND ACQUISITION & DEV ---
    # ==========================================
    land_entry_mode = params.get("land_entry_mode", "Flat Lump Sum per Lot")
    if land_entry_mode == "Detailed Horizontal Infrastructure (LF Parametrics)":
        land_raw_cost = params.get("land_raw_cost", 50000)
        frontage_per_lot = params.get("frontage_per_lot", 50.0)
        lot_depth = params.get("lot_depth", 120.0)
        
        site_type_mode = params.get("site_type_mode", "Auto-Calc LF (Based on Lot Frontage)")
        if site_type_mode == "Auto-Calc LF (Based on Lot Frontage)":
            road_layout = params.get("road_layout", "Double-Sided Street (Yields 2 Lots per LF)")
            total_road_lf = (frontage_per_lot * units) if "Single" in road_layout else (frontage_per_lot * units) / 2.0
        else:
            total_road_lf = params.get("manual_infra_lf", 0.0)
            
        road_width = params.get("road_width", 24.0)
        lot_fill_inches = params.get("lot_fill_inches", 12.0)
        road_fill_inches = params.get("road_fill_inches", 10.0)
        fill_cost_cy = params.get("fill_cost_cy", 18.0)
        
        lot_fill_cy = ((frontage_per_lot * lot_depth * units) * (lot_fill_inches / 12.0)) / 27.0
        road_fill_cy = ((total_road_lf * road_width) * (road_fill_inches / 12.0)) / 27.0
        total_fill_cy = lot_fill_cy + road_fill_cy
        
        land_earthwork = (params.get("clearing_per_lot", 3000.0) * units) + (total_fill_cy * fill_cost_cy)
        land_paving = total_road_lf * params.get("paving_cost_lf", 125.0)
        land_drainage = total_road_lf * params.get("drainage_cost_lf", 85.0)
        land_water_main = total_road_lf * params.get("water_main_lf", 45.0)
        land_sewer_main = total_road_lf * params.get("sewer_main_lf", 65.0)
        land_electric_main = total_road_lf * params.get("electric_main_lf", 35.0)
        land_gas_main = total_road_lf * params.get("gas_main_lf", 20.0)
        
        detention_pond = params.get("detention_pond", 15000.0)
        site_amenities = params.get("site_amenities", 4500.0)
        
        total_land_detailed = sum([land_raw_cost, land_earthwork, land_paving, land_drainage, land_water_main, 
                                   land_sewer_main, land_electric_main, land_gas_main, detention_pond, site_amenities])
        land_basis = total_land_detailed / units if units > 0 else 0
        total_land_default = total_land_detailed
    else:
        land_basis = params.get("land_basis", 10000)
        total_land_default = land_basis * units

    # ==========================================
    # --- 3. VALUATION & APPRAISAL MATH ---
    # ==========================================
    appraisal_mode = params.get("appraisal_mode", "Income Approach (DSCR Loan Sizing)")
    target_grm = params.get("target_grm", 10.0)

    cost_calc_mode = params.get("cost_calc_mode", "Reverse-Engineer from Primary Comp")
    base_direct_cost_sf_input = params.get("base_direct_cost_sf", 75.0)
    lot_cost_pct = params.get("lot_cost_pct", 13.7) / 100.0
    profit_margin_pct = params.get("profit_margin_pct", 11.0) / 100.0
    overhead_pct = params.get("overhead_pct", 5.7) / 100.0
    sales_pct = params.get("sales_pct", 3.6) / 100.0
    finance_pct = params.get("finance_pct", 1.5) / 100.0

    comp_price = params.get("comp_price", 195000)
    comp_heated_sf = params.get("comp_heated_sf", 1275)
    comp_struct_sf = params.get("comp_struct_sf", 213)
    comp_front_sf = params.get("comp_front_sf", 49)
    comp_back_sf = params.get("comp_back_sf", 49)
    comp_storage_sf = params.get("comp_storage_sf", 0)

    aux_sqft_total = struct_sqft + front_porch_sqft + back_porch_sqft + storage_sqft
    total_under_roof_sqft = sqft + aux_sqft_total

    comp_aux_sqft = comp_struct_sf + comp_front_sf + comp_back_sf + comp_storage_sf
    comp_total_sf = comp_heated_sf + comp_aux_sqft
    raw_comp_price_sf = comp_price / comp_heated_sf if comp_heated_sf > 0 else 0

    combined_deductions_pct = lot_cost_pct + profit_margin_pct + overhead_pct + sales_pct + finance_pct
    target_const_budget_pct = max(0, 1.0 - combined_deductions_pct)
    indirect_multiplier = 1.0 + indirect_permits_pct + indirect_temp_facilities_pct + contingency_pct

    # Isolate heated rate
    if aux_cost_mode == "Percentage of Heated Rate (%)":
        effective_comp_heated_sf = comp_heated_sf + (comp_aux_sqft * aux_ratio)
        isolated_heated_rate = comp_price / effective_comp_heated_sf if effective_comp_heated_sf > 0 else 0
        comp_aux_rate_sf = isolated_heated_rate * aux_ratio
        comp_aux_value = comp_aux_sqft * comp_aux_rate_sf
        comp_equivalent_arv = (isolated_heated_rate * sqft) + (aux_sqft_total * comp_aux_rate_sf) + additional_foundation_cost
    else:
        comp_aux_rate_sf = aux_fixed_cost_sf
        comp_aux_value = comp_aux_sqft * comp_aux_rate_sf
        comp_isolated_heated_value = max(0, comp_price - comp_aux_value)
        isolated_heated_rate = comp_isolated_heated_value / comp_heated_sf if comp_heated_sf > 0 else 0
        comp_equivalent_arv = (isolated_heated_rate * sqft) + (aux_sqft_total * comp_aux_rate_sf) + additional_foundation_cost

    # Appraisals (NEW PITIA LOGIC & CF LIMIT)
    grm_arv = (gross_monthly_rent * 12) * target_grm
    refi_monthly_rate = net_refi_rate / 12.0
    refi_term_months = refi_term_years * 12
    
    # 1. Isolate the Bank TIA (Taxes, Insurance, Flood, HOA) per unit
    if params.get("opex_entry_mode", "Percentage of EGI (%)") == "Percentage of EGI (%)":
        mo_other_opex_per_unit = mo_other_opex / units if units > 0 else 0
        bank_tia_per_unit = mo_other_opex_per_unit * 0.75 # Est 75% of other opex is TIA
    else:
        bank_tia_per_unit = params.get("opex_taxes_mo", 150.0) + params.get("opex_ins_mo", 115.0) + params.get("opex_flood_mo", 30.0) + params.get("opex_misc_mo", 0.0)

    # Max PITIA payment allowed by the bank = Gross Rent / Target DSCR
    max_pitia = gross_monthly_rent / target_dscr_rate
    
    # Max Principal & Interest = Max PITIA minus Taxes/Ins/HOA
    max_pi_per_unit = max_pitia - bank_tia_per_unit
    
    if refi_monthly_rate > 0:
        target_loan_per_unit = max_pi_per_unit * ((1.0 - (1.0 + refi_monthly_rate)**-refi_term_months) / refi_monthly_rate)
    else:
        target_loan_per_unit = max_pi_per_unit * refi_term_months
        
    dscr_arv = target_loan_per_unit / refi_ltv if refi_ltv > 0 else 0
    bank_dscr_max_loan_total = target_loan_per_unit * units
    
    # Reverse calculate Cash Flow constrained loan
    max_cf_pi_per_unit = (monthly_noi / units) - target_min_cashflow_per_door
    if max_cf_pi_per_unit > 0:
        if refi_monthly_rate > 0:
            cf_max_loan_per_unit = max_cf_pi_per_unit * ((1.0 - (1.0 + refi_monthly_rate)**-refi_term_months) / refi_monthly_rate)
        else:
            cf_max_loan_per_unit = max_cf_pi_per_unit * refi_term_months
    else:
        cf_max_loan_per_unit = 0
        
    cf_max_loan_total = cf_max_loan_per_unit * units

    if appraisal_mode == "Sales Comp (Price/SF)":
        arv_per_unit = comp_equivalent_arv
    elif appraisal_mode == "Income Approach (GRM)":
        arv_per_unit = grm_arv
    elif appraisal_mode == "Income Approach (DSCR Loan Sizing)":
        arv_per_unit = dscr_arv
    else: 
        arv_per_unit = min(grm_arv, dscr_arv)
        
    # NEW LOGIC: Intercept and override the ARV based on UI Constraints
    arv_constraint_mode = params.get("arv_constraint_mode", "No Override (Use Valuation Mode Above)")
    if arv_constraint_mode == "Force ARV to exactly meet Min. Cash Flow":
        arv_per_unit = cf_arv_per_unit
    elif arv_constraint_mode == "Manual Target ARV Override":
        arv_per_unit = params.get("manual_arv_override", 250000.0)

    # Reverse engineer builder budget
    if cost_calc_mode == "Manual Set (Heated SF)":
        direct_cost_sf = base_direct_cost_sf_input
        struct_cost_sf = direct_cost_sf * aux_ratio if aux_cost_mode == "Percentage of Heated Rate (%)" else aux_fixed_cost_sf
        our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
        target_heated_hard_cost = direct_cost_sf * sqft
        target_direct_hard_cost = target_heated_hard_cost + our_aux_cost_total
        
        if gc_fee_mode == "Percentage of Hard Costs (%)":
            total_construction_budget = target_direct_hard_cost * indirect_multiplier * (1.0 + gc_fee_pct)
        else:
            total_construction_budget = (target_direct_hard_cost * indirect_multiplier) + (custom_gc_fee / units)
            
        reference_price = arv_per_unit
    else:
        reference_price = arv_per_unit if cost_calc_mode == "Reverse-Engineer from Appraisal" else comp_equivalent_arv
            
        total_construction_budget = reference_price * target_const_budget_pct
        if gc_fee_mode == "Percentage of Hard Costs (%)":
            target_direct_hard_cost = total_construction_budget / (indirect_multiplier * (1.0 + gc_fee_pct))
        else:
            target_direct_hard_cost = (total_construction_budget - (custom_gc_fee / units)) / indirect_multiplier
            
        if aux_cost_mode == "Percentage of Heated Rate (%)":
            effective_project_heated_sf = sqft + (aux_sqft_total * aux_ratio)
            direct_cost_sf = max(0, (target_direct_hard_cost - additional_foundation_cost) / effective_project_heated_sf) if effective_project_heated_sf > 0 else 0
            struct_cost_sf = direct_cost_sf * aux_ratio
            our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
            target_heated_hard_cost = direct_cost_sf * sqft
        else:
            struct_cost_sf = aux_fixed_cost_sf
            our_aux_cost_total = (aux_sqft_total * struct_cost_sf) + additional_foundation_cost
            target_heated_hard_cost = max(0, target_direct_hard_cost - our_aux_cost_total)
            direct_cost_sf = target_heated_hard_cost / sqft if sqft > 0 else 0

    # Build up base costs
    front_porch_cost_sf = struct_cost_sf
    back_porch_cost_sf = struct_cost_sf
    storage_cost_sf = struct_cost_sf

    struct_total_cost = struct_sqft * struct_cost_sf
    front_porch_cost = front_porch_sqft * front_porch_cost_sf
    back_porch_cost = back_porch_sqft * back_porch_cost_sf
    storage_cost = storage_sqft * storage_cost_sf
    outdoor_aux_subtotal_unit = front_porch_cost + back_porch_cost + storage_cost

    heated_hard_cost = sqft * direct_cost_sf
    blended_cost_per_sf = (heated_hard_cost + our_aux_cost_total) / total_under_roof_sqft if total_under_roof_sqft > 0 else 0

    total_hard_cost = target_direct_hard_cost * units
    total_arv = arv_per_unit * units
    loan_total = total_arv * refi_ltv
    default_buydown_cost = loan_total * (buydown_pts / 100.0) if apply_buydown else 0

    target_lot_value_per_door = reference_price * lot_cost_pct
    target_total_lot_value = target_lot_value_per_door * units
    land_equity_captured = target_total_lot_value - total_land_default

    contingency_cost = total_hard_cost * contingency_pct
    permits_insurance_cost = total_hard_cost * indirect_permits_pct
    temp_facilities_cost = total_hard_cost * indirect_temp_facilities_pct
    fee_basis = total_hard_cost + permits_insurance_cost + temp_facilities_cost + contingency_cost
    default_gc_fee = custom_gc_fee if gc_fee_mode == "Consolidated Flat Fee ($ Total)" else fee_basis * gc_fee_pct
    total_indirect_costs = permits_insurance_cost + temp_facilities_cost + contingency_cost + default_gc_fee

    # =========================================================================
    # --- 4. S-CURVE ITERATIVE SOLVER & BANK STRESS TESTS ---
    # =========================================================================
    cb_gross_annual_rent = const_bank_rent * units * 12.0

    if const_bank_val_mode == "DSCR Stress Test":
        cb_noi = cb_gross_annual_rent * (1.0 - const_bank_vac_pct) * (1.0 - const_bank_opex_pct)
        cb_max_annual_ds = cb_noi / const_bank_dscr
        cb_monthly_rate = const_bank_qual_rate / 12.0
        cb_term_months = const_bank_amort_yrs * 12
        if cb_monthly_rate > 0:
            bank_stressed_value = (cb_max_annual_ds / 12.0) * ((1.0 - (1.0 + cb_monthly_rate)**-cb_term_months) / cb_monthly_rate)
        else:
            bank_stressed_value = (cb_max_annual_ds / 12.0) * cb_term_months
    else:
        bank_stressed_value = cb_gross_annual_rent * const_bank_grm

    actual_const_loan = bank_stressed_value * const_ltv # updated to use selected LTC
    total_const = total_hard_cost + total_indirect_costs
    total_project_costs_ex_interest = total_land_default + total_const + total_vertical_soft + const_closing_fee

    land_raw_total = params.get("land_raw_cost", 50000) if land_entry_mode == "Detailed Horizontal Infrastructure (LF Parametrics)" else total_land_default
    infra_total = total_land_default - land_raw_total if land_entry_mode == "Detailed Horizontal Infrastructure (LF Parametrics)" else 0.0

    total_draw_budget = infra_total + total_const + total_vertical_soft
    carry_int_base = actual_const_loan * 0.5 * const_rate * (build_months / 12.0)

    # Iterate S-Curve solver
    for _ in range(5):
        total_construction_basis = total_project_costs_ex_interest + carry_int_base
        seed_capital = max(0, total_construction_basis - actual_const_loan)
        
        equity_remaining = seed_capital
        day_1_costs = land_raw_total + const_closing_fee
        
        if equity_remaining >= day_1_costs:
            equity_remaining -= day_1_costs
            drawn_loan_balance = 0.0
        else:
            drawn_loan_balance = day_1_costs - equity_remaining
            equity_remaining = 0.0
            
        actual_scurve_interest = 0.0
        cum_pct = 0.0
        d_schedule = []
        
        for m in range(1, build_months + 1):
            prev_pct = cum_pct
            cum_pct = math.pow(math.sin((math.pi / 2.0) * (m / build_months)), 2)
            month_pct = cum_pct - prev_pct
            month_draw = total_draw_budget * month_pct
            
            month_int = drawn_loan_balance * (const_rate / 12.0)
            actual_scurve_interest += month_int
            
            if equity_remaining >= month_draw:
                equity_remaining -= month_draw
                funded_by_loan = 0.0
            else:
                funded_by_loan = month_draw - equity_remaining
                equity_remaining = 0.0
                
            drawn_loan_balance += funded_by_loan + month_int 
            
            d_schedule.append({
                "Month": f"Month {m}",
                "Cum. % Complete": f"{cum_pct*100:.1f}%",
                "Monthly Draw ($)": month_draw,
                "Capitalized Interest ($)": month_int,
                "Total Drawn Balance ($)": drawn_loan_balance
            })
            
        carry_int_base = actual_scurve_interest

    df_schedule = pd.DataFrame(d_schedule)
    total_construction_basis = total_project_costs_ex_interest + carry_int_base
    total_project_basis = total_construction_basis + refi_closing_fee + default_buydown_cost
    seed_capital = max(0, total_construction_basis - actual_const_loan)

    # Actual Returns
    monthly_interest_rate = net_refi_rate / 12.0
    total_payments = refi_term_years * 12
    if monthly_interest_rate > 0:
        monthly_pi_per_unit = (loan_total / units) * (monthly_interest_rate * (1 + monthly_interest_rate)**total_payments) / ((1 + monthly_interest_rate)**total_payments - 1)
    else:
        monthly_pi_per_unit = (loan_total / units) / total_payments if total_payments > 0 else 0

    total_monthly_pi = monthly_pi_per_unit * units
    annual_debt_service = total_monthly_pi * 12.0
    
    # NEW DSCR (PITIA) METHOD LOGIC
    monthly_pitia_per_unit = monthly_pi_per_unit + bank_tia_per_unit
    actual_dscr = gross_monthly_rent / monthly_pitia_per_unit if monthly_pitia_per_unit > 0 else 0
    dscr_variance = actual_dscr - target_dscr_rate
    
    monthly_cash_flow = monthly_noi - total_monthly_pi
    monthly_cash_flow_per_door = monthly_cash_flow / units if units > 0 else 0

    net_cash_at_closing = loan_total - actual_const_loan - refi_closing_fee - default_buydown_cost
    cash_surplus = net_cash_at_closing - seed_capital
    retained_equity = total_arv - loan_total
    day1_wealth = default_gc_fee + max(0.0, cash_surplus) + retained_equity

    btr_finance_closing = carry_int_base + const_closing_fee + refi_closing_fee + default_buydown_cost
    lot_benchmark = target_total_lot_value
    developer_margin = total_arv - (lot_benchmark + total_hard_cost + total_indirect_costs + total_vertical_soft + btr_finance_closing)

    # Multi-unit scaling logic
    unit_land = land_basis
    unit_hard = target_direct_hard_cost
    unit_soft = (permits_insurance_cost + contingency_cost + total_vertical_soft) / units
    unit_fin = btr_finance_closing / units
    unit_gc_baseline = (temp_facilities_cost + default_gc_fee) / units

    cap_1 = unit_land + unit_hard + unit_soft + unit_fin + unit_gc_baseline
    loan_1 = loan_total / units
    surplus_1 = loan_1 - cap_1
    eq_1 = (total_arv / units) - loan_1
    wealth_1 = unit_gc_baseline + max(0, surplus_1) + eq_1

    opt_gc_3 = 20000
    savings_per_door = unit_gc_baseline - (opt_gc_3 / 3)
    cap_3 = (unit_land + unit_hard + unit_soft + unit_fin) * 3 + opt_gc_3
    loan_3 = loan_1 * 3
    surplus_3 = loan_3 - cap_3
    eq_3 = eq_1 * 3
    wealth_3 = opt_gc_3 + max(0, surplus_3) + eq_3

    opt_gc_6 = 40000
    cap_6 = (unit_land + unit_hard + unit_soft + unit_fin) * 6 + opt_gc_6
    loan_6 = loan_1 * 6
    surplus_6 = loan_6 - cap_6
    eq_6 = eq_1 * 6
    wealth_6 = opt_gc_6 + max(0, surplus_6) + eq_6

    monthly_cf_6 = monthly_cash_flow_per_door * 6
    annual_cf_6 = monthly_cf_6 * 12

    # =========================================================================
    # --- 5. STRESS TESTING MATRICES ---
    # =========================================================================
    stress_results = []
    for scn in STRESS_SCENARIOS:
        s_arv = total_arv * (1 + scn["ARV_Shift"])
        s_loan_total = s_arv * refi_ltv
        s_buydown = s_loan_total * (buydown_pts / 100.0) if apply_buydown else 0
        s_months = build_months + scn["Delay"]
        
        s_carry = actual_const_loan * 0.5 * const_rate * (s_months / 12.0)
        for _ in range(3):
            s_basis_ex_refi = total_project_costs_ex_interest + s_carry
            s_seed = max(0, s_basis_ex_refi - actual_const_loan)
            eq_rem = s_seed
            if eq_rem >= day_1_costs:
                eq_rem -= day_1_costs
                d_bal = 0.0
            else:
                d_bal = day_1_costs - eq_rem
                eq_rem = 0.0
            
            s_int = 0.0
            cp = 0.0
            for m in range(1, s_months + 1):
                pp = cp
                cp = math.pow(math.sin((math.pi / 2.0) * (m / s_months)), 2)
                m_drw = total_draw_budget * (cp - pp)
                m_i = d_bal * (const_rate / 12.0)
                s_int += m_i
                
                if eq_rem >= m_drw:
                    eq_rem -= m_drw
                    f_loan = 0.0
                else:
                    f_loan = m_drw - eq_rem
                    eq_rem = 0.0
                d_bal += f_loan + m_i
            s_carry = s_int
            
        s_seed_final = max(0, total_project_costs_ex_interest + s_carry - actual_const_loan)
        s_net_cash = s_loan_total - actual_const_loan - refi_closing_fee - s_buydown
        s_surplus = s_net_cash - s_seed_final
        s_retained_eq = s_arv - s_loan_total
        s_wealth = default_gc_fee + max(0.0, s_surplus) + s_retained_eq
        
        s_net_rate = net_refi_rate + scn["Rate_Shift"]
        s_m_rate = s_net_rate / 12.0
        if s_m_rate > 0:
            s_pi = (s_loan_total / units) * (s_m_rate * (1 + s_m_rate)**total_payments) / ((1 + s_m_rate)**total_payments - 1)
        else:
            s_pi = (s_loan_total / units) / total_payments if total_payments > 0 else 0
            
        s_ds = s_pi * units * 12.0
        
        s_monthly_pitia_per_unit = s_pi + bank_tia_per_unit
        s_dscr = gross_monthly_rent / s_monthly_pitia_per_unit if s_monthly_pitia_per_unit > 0 else 0
        
        dscr_str = f"PASS: {s_dscr:.2f}x" if s_dscr >= target_dscr_rate else f"FAIL: {s_dscr:.2f}x"
        surplus_str = f"+${s_surplus:,.0f}" if s_surplus >= 0 else f"-${abs(s_surplus):,.0f}"
        
        stress_results.append({
            "Stress Scenario": scn["Name"],
            "Final ARV": f"${s_arv:,.0f}",
            "Refi Rate": f"{s_net_rate*100:.2f}%",
            "Build Time": f"{s_months} mos",
            "DSCR Status": dscr_str,
            "Net Cash Surplus / (Trapped)": surplus_str,
            "Total Day-1 Wealth": f"${s_wealth:,.0f}",
            "Raw DSCR": s_dscr,
            "Raw Surplus": s_surplus
        })
    df_stress = pd.DataFrame(stress_results)

    # --- OPEX SENSITIVITY ---
    opex_sensitivity_data = []
    raw_opex_nois = []
    raw_opex_dscrs = []
    opex_labels = []
    opex_colors = []
    test_rates = [0.25, 0.30, 0.35]

    for rate in test_rates:
        mo_opex = total_gross_monthly_income * rate
        mo_vac = total_gross_monthly_income * vacancy_rate
        mo_noi = total_gross_monthly_income - mo_vac - mo_opex
        dscr = mo_noi / total_monthly_pi if total_monthly_pi > 0 else 0
        
        if dscr >= target_dscr_rate:
            status = "Approved (Passes standard guidelines)"
            color = '#2ca02c'
        elif dscr >= 1.0:
            status = "Requires Additional Buydown / Lower LTV"
            color = '#ff7f0e'
        else:
            status = "Fails Underwriting (Breakeven only)"
            color = '#d62728'
            
        label = "25% (Baseline)" if rate == 0.25 else f"{rate*100:.0f}%"

        raw_opex_nois.append(mo_noi)
        raw_opex_dscrs.append(dscr)
        opex_labels.append(label)
        opex_colors.append(color)

        opex_sensitivity_data.append({
            "OpEx Rate": label,
            "Monthly OpEx": f"-${mo_opex:,.0f}",
            "NOI": f"${mo_noi:,.0f}",
            "Monthly P&I": f"-${total_monthly_pi:,.0f}",
            "Resulting DSCR": f"{dscr:.2f}x",
            f"Underwriting Status (Target: {target_dscr_rate:.2f}x)": status
        })
    df_opex_sens = pd.DataFrame(opex_sensitivity_data)

    # --- GROSS RENT SENSITIVITY ---
    rent_sensitivity_data = []
    raw_rents = []
    raw_rent_cfs = []
    raw_rent_dscrs = []
    rent_colors = []
    test_rents = [gross_monthly_rent + offset for offset in range(-100, 201, 50)]

    for r in test_rents:
        mo_vac = r * vacancy_rate
        if opex_entry_mode == "Percentage of EGI (%)":
            mo_egi = r - mo_vac
            mo_mgmt = mo_egi * mgmt_fee_pct
            mo_other = mo_egi * other_opex_rate
            total_mo_opex = mo_mgmt + mo_other
        else:
            mo_egi = r - mo_vac
            mo_mgmt = mo_egi * mgmt_fee_pct
            mo_other = mo_other_opex / units if units > 0 else 0
            total_mo_opex = mo_mgmt + mo_other

        mo_noi = r - mo_vac - total_mo_opex
        
        # New PITIA DSCR calculation for Rent Sensitivity Matrix
        r_monthly_pitia_per_unit = monthly_pi_per_unit + bank_tia_per_unit
        dscr = r / r_monthly_pitia_per_unit if r_monthly_pitia_per_unit > 0 else 0
        
        net_cf = mo_noi - monthly_pi_per_unit
        
        raw_rents.append(f"${r:,.0f}")
        raw_rent_cfs.append(net_cf)
        raw_rent_dscrs.append(dscr)
        
        if net_cf >= target_min_cashflow_per_door:
            color = '#2ca02c' 
        elif net_cf >= 0:
            color = '#ff7f0e' 
        else:
            color = '#d62728' 
        rent_colors.append(color)

        rent_sensitivity_data.append({
            "Gross Rent": f"${r:,.0f}" + (" (Target)" if r == gross_monthly_rent else ""),
            f"Vacancy ({vacancy_rate*100:.1f}%)": f"-${mo_vac:,.0f}",
            "OpEx": f"-${total_mo_opex:,.0f}",
            "Monthly NOI": f"${mo_noi:,.0f}",
            "Commercial DSCR": f"{dscr:.2f}x",
            "Net Monthly Cash Flow": f"${net_cf:,.0f} / mo"
        })
    df_rent_sens = pd.DataFrame(rent_sensitivity_data)

    # --- REVERSE ENGINEERING DATA ---
    lot_val = reference_price * lot_cost_pct
    profit_val = reference_price * profit_margin_pct
    overhead_val = reference_price * overhead_pct
    sales_val = reference_price * sales_pct
    finance_val = reference_price * finance_pct

    # --- LONG-TERM PORTFOLIO WEALTH / IRR ---
    depreciable_basis = max(0, total_project_basis - total_land_default)
    annual_depreciation = depreciable_basis / 27.5
    annual_tax_savings = annual_depreciation * income_tax_rate_pct

    proj_years = list(range(0, refi_term_years + 1))
    asset_vals = [total_arv * ((1 + appreciation_rate) ** y) for y in proj_years]

    r_monthly = net_refi_rate / 12.0
    n_months = refi_term_years * 12
    loan_vals = []

    for y in proj_years:
        m = y * 12
        if r_monthly > 0:
            bal = loan_total * (((1 + r_monthly)**n_months - (1 + r_monthly)**m) / ((1 + r_monthly)**n_months - 1))
        else:
            bal = loan_total * (1 - m / n_months) if n_months > 0 else 0
        loan_vals.append(max(0, bal))

    equity_vals = [av - lv for av, lv in zip(asset_vals, loan_vals)]
    cumulative_cf = [monthly_cash_flow * 12 * y for y in proj_years]
    principal_paid = [loan_total - lv for lv in loan_vals]

    yr1_cf = monthly_cash_flow * 12
    yr1_prin = principal_paid[1]
    yr1_appr = asset_vals[1] - total_arv
    yr1_tax = annual_tax_savings
    total_yr1_return = yr1_cf + yr1_prin + yr1_appr + yr1_tax

    if cash_surplus >= 0:
        irr_5_str = "Infinite (Zero Capital Trapped)"
        irr_10_str = "Infinite (Zero Capital Trapped)"
    else:
        cfs_5 = [cash_surplus] + [monthly_cash_flow * 12 + annual_tax_savings] * 4 + [(monthly_cash_flow * 12 + annual_tax_savings) + equity_vals[5]]
        irr_5 = calc_irr(cfs_5)
        irr_5_str = f"{irr_5*100:.1f}%"
        
        cfs_10 = [cash_surplus] + [monthly_cash_flow * 12 + annual_tax_savings] * 9 + [(monthly_cash_flow * 12 + annual_tax_savings) + equity_vals[10]]
        irr_10 = calc_irr(cfs_10)
        irr_10_str = f"{irr_10*100:.1f}%"

    # --- RETAIL COMPARISON DATA ---
    retail_tax_rate = 0.30
    retail_sales_costs = total_arv * 0.08
    retail_total_invested = total_land_default + total_const + total_vertical_soft + const_closing_fee + carry_int_base + retail_sales_costs
    retail_pre_tax_profit = total_arv - retail_total_invested
    retail_taxes = max(0, retail_pre_tax_profit * retail_tax_rate)
    retail_net_cash = retail_pre_tax_profit - retail_taxes

    # Returns EVERY variable calculated above as a massive dictionary
    return locals()
