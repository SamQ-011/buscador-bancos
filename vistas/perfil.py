import time
import bcrypt
import streamlit as st
from sqlalchemy import text

# --- Infrastructure ---

def init_connection():
    """
    Conexión a PostgreSQL Local (Docker).
    """
    try:
        return st.connection("local_db", type="sql")
    except Exception as e:
        st.error(f"Service unavailable: {e}")
        return None

# --- Backend Logic ---

def update_credentials(username: str, current_pass: str, new_pass: str) -> bool:
    """
    Verifies current password hash and updates DB with new bcrypt hash (SQL).
    """
    conn = init_connection()
    if not conn: return False

    try:
        # 1. Obtener hash actual
        query = text('SELECT password FROM "Users" WHERE username = :u')
        df = conn.query(query, params={"u": username}, ttl=0)
        
        if df.empty:
            st.error("User record not found.")
            return False
            
        stored_hash = df.iloc[0]['password']

        # 2. Verificar contraseña actual
        if not bcrypt.checkpw(current_pass.encode('utf-8'), stored_hash.encode('utf-8')):
            st.error("Current password incorrect.")
            return False

        # 3. Generar nuevo hash y actualizar
        new_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        update_sql = text('UPDATE "Users" SET password = :p WHERE username = :u')
        
        with conn.session as s:
            s.execute(update_sql, {"p": new_hash, "u": username})
            s.commit()
            
        return True

    except Exception as e:
        st.error(f"Update failed: {e}")
        return False

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
            # Frontend Validation
            if not current_pw or not new_pw:
                st.warning("All fields are required.")
                return

            if new_pw != confirm_pw:
                st.error("New passwords do not match.")
                return

            if len(new_pw) < 6:
                st.warning("Password too short (min 6 chars).")
                return

            # Backend Call
            if update_credentials(username, current_pw, new_pw):
                st.success("Password updated successfully.")
                st.balloons()
                time.sleep(1.5)
                st.rerun()

if __name__ == "__main__":
    show()