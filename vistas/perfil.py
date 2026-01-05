# vistas/perfil.py
import time
import streamlit as st

# --- IMPORTACIONES ---
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

# Importamos el nuevo servicio
import services.auth_service as auth_service

# --- UI Rendering ---

def show():
    st.title("⚙️ User Profile")
    st.caption("Account management & Security settings.")
    
    # Session Data
    username = st.session_state.get("username", "N/A")
    full_name = st.session_state.get("real_name", "Unknown User")
    role = st.session_state.get("role", "N/A")

    # Profile Header
    with st.container(border=True):
        c_avatar, c_info = st.columns([1, 5])
        with c_avatar:
            st.markdown("<h1 style='text-align: center;'>👤</h1>", unsafe_allow_html=True)
        with c_info:
            st.markdown(f"### {full_name}")
            st.markdown(f"**Username:** `{username}` &nbsp; | &nbsp; **Role:** `{role}`")
            st.caption("Contact IT Admin for role or name changes.")

    st.divider()

    # Security Module
    st.subheader("🔐 Security")
    
    with st.form("security_form"):
        st.write("**Change Password**")
        
        col_cur, col_new = st.columns(2)
        current_pw = col_cur.text_input("Current Password", type="password")
        
        new_pw = col_new.text_input("New Password", type="password", help="Min. 6 characters")
        confirm_pw = col_new.text_input("Confirm New Password", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.form_submit_button("Update Credentials", type="primary"):
            # Validaciones Frontend (Rápidas)
            if not current_pw or not new_pw:
                st.warning("All fields are required.")
                return

            if new_pw != confirm_pw:
                st.error("New passwords do not match.")
                return

            if len(new_pw) < 6:
                st.warning("Password too short (min 6 chars).")
                return

            # LLAMADA AL SERVICIO (Backend)
            conn = get_db_connection()
            success, message = auth_service.update_credentials(conn, username, current_pw, new_pw)
            
            if success:
                st.success(message)
                st.balloons()
                time.sleep(1.5)
                st.rerun()
            else:
                st.error(message)

if __name__ == "__main__":
    show()