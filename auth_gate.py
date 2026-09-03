import time
import streamlit as st
from supabase import Client

def check_session_timeout():
    """Enforces a 30-minute inactivity timeout on active Streamlit sessions."""
    timeout_limit = 30 * 60  # 30 minutes in seconds
    
    if "last_active" not in st.session_state:
        st.session_state.last_active = time.time()
        
    current_time = time.time()
    elapsed_time = current_time - st.session_state.last_active
    
    if elapsed_time > timeout_limit:
        # Clear sensitive session data and force re-authentication
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.warning("Session expired due to 30 minutes of inactivity. Please sign in again.")
        st.rerun()
        
    # Refresh timestamp on user interaction
    st.session_state.last_active = current_time

def render_auth_gate(supabase: Client):
    """Renders the secure login interface if an authenticated session is missing."""
    if "user" not in st.session_state or st.session_state.user is None:
        st.subheader("Wickboldt Capital — Secure Portal")
        st.markdown("Enter your authorized credentials to access project underwriting and development logs.")
        
        with st.form("login_form"):
            email = st.text_input("Corporate Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    st.session_state.user = response.user
                    st.session_state.last_active = time.time()
                    st.success("Authentication successful.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
        return False
    
    # Enforce timeout checks on active sessions
    check_session_timeout()
    return True
