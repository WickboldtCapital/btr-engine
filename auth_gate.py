import streamlit as st

def render_auth_gate(supabase):
    """
    Renders a secure Supabase authentication gate.
    Returns True if authenticated, False if the user needs to log in.
    """
    # Check if user session already exists in Streamlit state
    if "user_session" in st.session_state and st.session_state["user_session"] is not None:
        return True

    # Center the login box for a clean UI look
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
                    if response.user:
                        st.session_state["user_session"] = response
                        st.success("Authentication successful! Loading portal...")
                        st.rerun()
                    else:
                        st.error("Invalid login credentials.")
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
                    
    return False