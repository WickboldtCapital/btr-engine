import streamlit as st

def render_auth_gate(supabase):
    """
    Renders a secure Supabase authentication gate.
    Returns True if authenticated, False if the user needs to log in.
    """
    # 1. Check if session state exists AND has an active user
    if "user_session" in st.session_state and st.session_state["user_session"] is not None:
        # We are logged in. Do NOT inject any CSS here. 
        # Streamlit will naturally render the sidebar.
        return True

    # 2. If not logged in, force-hide the sidebar immediately via CSS
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {display: none !important;}
        </style>
        """,
        unsafe_allow_html=True
    )

    # 3. Center the login box
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 🔐 Wickboldt Capital — Secure Portal")
        st.markdown("Please sign in with your authorized credentials to access the Underwriting Engine.")
        
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password.")
                    return False
                try:
                    # Authenticate against Supabase
                    response = supabase.auth.sign_in_with_password({
                        "email": email.strip(),
                        "password": password.strip()
                    })
                    if response and getattr(response, "user", None):
                        st.session_state["user_session"] = response
                        st.success("Authentication successful! Loading portal...")
                        st.rerun()
                    else:
                        st.error("Invalid login credentials.")
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
                    
    return False