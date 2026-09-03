import streamlit as st
import os
import sys
import traceback

st.title("📚 Enterprise Technical Document Library")

try:
    # Ensure it can find our other files
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    from document_engine import render_dynamic_document, get_available_variables
    from calculations import run_underwriting_engine
    from config import STRESS_SCENARIOS

    # Safely initialize session state if user landed directly on this page
    if "units" not in st.session_state:
        st.session_state["units"] = 1
        st.session_state["gross_monthly_rent"] = 1600
        st.session_state["target_dscr_rate"] = 1.20
        st.session_state["refi_ltv_pct"] = 80.0

    # Run the engine silently to get the live data context
    calc = run_underwriting_engine(st.session_state, STRESS_SCENARIOS)

    st.markdown("Draft, version-control, and export dynamic technical briefs, reports, and theses.")
    st.divider()

    # Build the Three-Column Workspace
    col_ledger, col_editor, col_preview = st.columns([1, 2, 2], gap="large")

    # --- COLUMN 1: THE VARIABLE LEDGER ---
    with col_ledger:
        st.markdown("### 📋 Variable Ledger")
        st.caption("Click the tag to copy it, then paste into your document.")
        
        search_var = st.text_input("Search Variables", placeholder="e.g., dscr")
        
        available_vars = get_available_variables(calc)
        if search_var:
            filtered_vars = [v for v in available_vars if search_var.lower() in v.lower()]
        else:
            filtered_vars = available_vars
        
        with st.container(height=600):
            for var in filtered_vars:
                val = calc.get(var, "N/A")
                if isinstance(val, (int, float)):
                    val_preview = f"{val:,.2f}"
                else:
                    val_preview = str(val)[:20]
                    
                st.code(f"{{{{ {var} }}}}", language="markdown")
                st.caption(f"Current Value: `{val_preview}`")
                st.markdown("---")

    # --- COLUMN 2: THE RAW EDITOR ---
    with col_editor:
        st.markdown("### ✍️ Markdown Editor")
        
        default_text = """### Executive Summary

The project requires **{{ seed_capital | currency }}** in Day-1 seed capital. 
Upon stabilization, the asset will yield a **{{ actual_dscr | multiple }}** DSCR, generating **{{ monthly_cash_flow_per_door | currency }}** per door in net monthly cash flow.

Because the takeout loan of **{{ loan_total | currency }}** fully covers the **{{ total_project_basis | currency }}** capital basis, the project achieves a net cash surplus of **{{ cash_surplus | currency }}** at closing.
"""
        
        raw_markdown = st.text_area(
            "Document Content", 
            value=default_text, 
            height=550, 
            label_visibility="collapsed"
        )
        
        st.button("💾 Commit New Version (Coming Soon)", type="primary", use_container_width=True, disabled=True)

    # --- COLUMN 3: THE LIVE PREVIEW ---
    with col_preview:
        st.markdown("### 👁️ Live Rendered Preview")
        
        with st.container(height=600, border=True):
            rendered_document = render_dynamic_document(raw_markdown, calc)
            st.markdown(rendered_document)

except Exception as e:
    st.error("🚨 An error occurred while loading the Technical Library:")
    st.code(traceback.format_exc())
