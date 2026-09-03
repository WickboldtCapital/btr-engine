import streamlit as st
import os
import sys
import traceback

st.title("📚 Enterprise Technical Document Library")

try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from document_engine import render_dynamic_document, get_available_variables
    from calculations import run_underwriting_engine
    from config import STRESS_SCENARIOS

    if "units" not in st.session_state:
        st.session_state["units"] = 1
        st.session_state["gross_monthly_rent"] = 1600
        st.session_state["target_dscr_rate"] = 1.20
        st.session_state["refi_ltv_pct"] = 80.0

    calc = run_underwriting_engine(st.session_state, STRESS_SCENARIOS)

    st.markdown("Draft, version-control, and export dynamic technical briefs, reports, and theses.")
    st.divider()

    # Use Tabs to separate the Workspace (Editor + Preview) from the Reference Ledger
    tab_workspace, tab_ledger = st.tabs(["✍️ Document Editor & Preview", "📋 Variable Ledger Reference"])

    with tab_workspace:
        col_editor, col_preview = st.columns(2, gap="large")

        with col_editor:
            st.markdown("### Markdown Editor")
            default_text = """### Executive Summary

The project requires **{{ seed_capital | currency }}** in Day-1 seed capital. 
Upon stabilization, the asset will yield a **{{ actual_dscr | multiple }}** DSCR, generating **{{ monthly_cash_flow_per_door | currency }}** per door in net monthly cash flow.

Because the takeout loan of **{{ loan_total | currency }}** fully covers the **{{ total_project_basis | currency }}** capital basis, the project achieves a net cash surplus of **{{ cash_surplus | currency }}** at closing.
"""
            raw_markdown = st.text_area(
                "Document Content", 
                value=default_text, 
                height=600, 
                label_visibility="collapsed"
            )
            st.button("💾 Commit New Version (Coming Soon)", type="primary", use_container_width=True, disabled=True)

        with col_preview:
            st.markdown("### Live Rendered Preview")
            with st.container(height=650, border=True):
                rendered_document = render_dynamic_document(raw_markdown, calc)
                st.markdown(rendered_document)

    with tab_ledger:
        st.markdown("### Available Data Variables")
        st.caption("Search or browse all live calculation variables. Copy the tag syntax to use in your documents.")
        
        search_var = st.text_input("Search Variables", placeholder="e.g., dscr, rent, cost")
        available_vars = get_available_variables(calc)
        if search_var:
            filtered_vars = [v for v in available_vars if search_var.lower() in v.lower()]
        else:
            filtered_vars = available_vars

        # Display in a clean 3-column card grid for easy reading
        col_count = 3
        cols = st.columns(col_count)
        for idx, var in enumerate(filtered_vars):
            val = calc.get(var, "N/A")
            if isinstance(val, (int, float)):
                val_preview = f"{val:,.2f}"
            else:
                val_preview = str(val)[:30]
            
            target_col = cols[idx % col_count]
            with target_col:
                st.code(f"{{{{ {var} }}}}", language="markdown")
                st.caption(f"Value: `{val_preview}`")
                st.markdown("---")

except Exception as e:
    st.error("🚨 An error occurred while loading the Technical Library:")
    st.code(traceback.format_exc())
