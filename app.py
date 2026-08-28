# --- DSCR CONSTRUCTION CAPPING & ALGEBRAIC CIRCULAR FIX ---
total_const_default = fee_basis + default_gc_fee + default_premium
total_project_costs_ex_interest_default = total_land_default + total_const_default + total_soft_default + const_closing_fee

# 1. Determine Bank's Capped Loan Size (DSCR Stress Limit)
cb_noi = (const_bank_rent * units * 12.0) * (1.0 - const_bank_vac_pct) * (1.0 - const_bank_opex_pct)
cb_max_annual_ds = cb_noi / const_bank_dscr
cb_monthly_rate = const_bank_qual_rate / 12.0
cb_term_months = const_bank_amort_yrs * 12
if cb_monthly_rate > 0:
    max_const_loan_dscr = (cb_max_annual_ds / 12.0) * ((1.0 - (1.0 + cb_monthly_rate)**-cb_term_months) / cb_monthly_rate)
else:
    max_const_loan_dscr = (cb_max_annual_ds / 12.0) * cb_term_months

# 2. Mathematically Pure Unconstrained LTC Loan 
time_years = build_months / 12.0
interest_multiplier = const_ltv * avg_draw_pct * const_rate * time_years

if interest_multiplier >= 1.0:
    normal_const_loan = total_project_costs_ex_interest_default * const_ltv 
else:
    normal_const_loan = (const_ltv * total_project_costs_ex_interest_default) / (1.0 - interest_multiplier)

# 3. Apply the Bank DSCR Cap
actual_const_loan = min(normal_const_loan, max_const_loan_dscr)

# 4. Calculate Final Capitalized Interest Reserve
# Since the loan is capped, interest is strictly derived from actual allowed loan proceeds
default_carry_int = actual_const_loan * avg_draw_pct * const_rate * time_years

# 5. Define the Shortfall (Day-1 Equity Gap)
gap_proceeds = max(0, normal_const_loan - actual_const_loan)
dscr_shortfall_reserve = gap_proceeds

# Variables kept at 0 or redefined to prevent breaking downstream UI references
carry_int_base = default_carry_int
carry_int_reserve = 0  # Sponsor equity does not accrue bank interest

# 6. Final Project Basis & Required Cash to Close
total_const = total_hard_cost + default_gcond + default_gc_fee + default_premium
total_project_costs_ex_interest = total_land_default + total_const + total_soft_default + const_closing_fee 
total_project_basis = total_project_costs_ex_interest + default_carry_int + refi_closing_fee + default_buydown_cost

# Day-1 Cash to Close = Total Capitalized Costs minus the Construction Loan Proceeds
seed_capital = (total_project_costs_ex_interest + default_carry_int) - actual_const_loan
