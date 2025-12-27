import time
import bcrypt
import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- Infrastructure ---

@st.cache_resource
def init_connection() -> Client:
    """Singleton connection to Supabase."""
    try:
        creds = st.secrets["connections"]["supabase"] if "connections" in st.secrets else st.secrets
        return create_client(creds["URL"], creds["KEY"])
    except Exception:
        return None

# --- Auth Logic ---

def authenticate(username: str, password: str, cookie_manager):
    """
    Validates credentials against DB, checks bcrypt hash, and sets session/cookies.
    """
    supabase = init_connection()
    if not supabase:
        st.error("Service unavailable (DB Connection).")
        return

    try:
        # Fetch user record
        res = supabase.table("Users").select("*").eq("username", username).execute()
        
        if not res.data:
            st.error("Invalid credentials.")
            return

        user_record = res.data[0]

        # Check account status
        if not user_record.get('active', True):
            st.warning("Account is disabled. Contact Admin.")
            return

        # Verify Password (Bcrypt)
        try:
            if bcrypt.checkpw(password.encode('utf-8'), user_record['password'].encode('utf-8')):
                # 1. Update Session State (RAM)
                st.session_state.update({
                    "logged_in": True,
                    "username": user_record['username'],
                    "real_name": user_record['name'],
                    "role": user_record['role']
                })
                
                # 2. Set Persistence Cookie (1 Day TTL)
                expiry = datetime.now() + timedelta(days=1)
                cookie_manager.set('cordoba_user', user_record['username'], expires_at=expiry)
                
                st.toast("Login successful", icon="🔓")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid credentials.")
        except ValueError:
            st.error("Security error during hash verification.")
            
    except Exception as e:
        # Log error to console for debugging, show generic error to user
        print(f"[Auth Error] {e}")
        st.error("Authentication failed due to internal error.")

# --- UI Rendering ---

def show(cookie_manager):
    # CSS Override specifically for Login alignment
    st.markdown("""
        <style>
            .block-container { padding-top: 3rem !important; }
        </style>
    """, unsafe_allow_html=True)

    # Centered Layout using Columns
    _, col_center, _ = st.columns([1, 1, 1])

    with col_center:
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>🏦</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; color: #1F2937;'>Workspace Access</h3>", unsafe_allow_html=True)
            st.caption("Please enter your credentials.")
            
            with st.form("login_form"):
                user_in = st.text_input("Username", placeholder="e.g. jdoe").strip()
                pass_in = st.text_input("Password", type="password").strip()
                
                # Submit Button
                submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
                
                if submitted:
                    if user_in and pass_in:
                        authenticate(user_in, pass_in, cookie_manager)
                    else:
                        st.warning("Username and password are required.")

        st.markdown(
            "<div style='text-align: center; color: #9CA3AF; font-size: 0.8em; margin-top: 1rem;'>"
            "🔒 Secure Connection (256-bit SSL)</div>", 
            unsafe_allow_html=True
        )
