import time
import bcrypt
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy import text

# --- Infrastructure ---

def init_connection():
    """
    Conexión a PostgreSQL Local (Docker).
    """
    try:
        return st.connection("local_db", type="sql")
    except Exception as e:
        st.error(f"Service unavailable (DB Connection): {e}")
        return None

# --- Auth Logic ---

def authenticate(username: str, password: str, cookie_manager):
    """
    Validates credentials against DB (SQL), checks bcrypt hash, and sets session/cookies.
    """
    conn = init_connection()
    if not conn: return

    try:
        # 1. Buscar usuario en la BD (Query SQL segura)
        # Usamos :u como parámetro para evitar inyección SQL
        query = 'SELECT * FROM "Users" WHERE username = :u'
        df = conn.query(query, params={"u": username}, ttl=0)
        
        # 2. Verificar si existe
        if df.empty:
            st.error("Invalid credentials.")
            return

        # Convertimos la primera fila a un diccionario para fácil acceso
        user_record = df.iloc[0].to_dict()

        # 3. Verificar estado de la cuenta
        if not user_record.get('active', True):
            st.warning("Account is disabled. Contact Admin.")
            return

        # 4. Verificar Contraseña (Bcrypt)
        # La contraseña en BD viene como string, bcrypt necesita bytes
        stored_hash = user_record['password'].encode('utf-8')
        input_pass = password.encode('utf-8')

        try:
            if bcrypt.checkpw(input_pass, stored_hash):
                # --- ÉXITO ---
                
                # A. Actualizar Session State (RAM)
                st.session_state.update({
                    "logged_in": True,
                    "user_id": int(user_record['id']),  # ID Relacional para logs
                    "username": user_record['username'],
                    "real_name": user_record['name'],
                    "role": user_record['role']
                })
                
                # B. Actualizar Cookie Persistente (1 Día)
                expiry = datetime.now() + timedelta(days=1)
                if cookie_manager:
                    cookie_manager.set('cordoba_user', user_record['username'], expires_at=expiry)
                
                st.toast("Login successful", icon="🔓")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid credentials.")
        except ValueError:
            st.error("Security error during hash verification.")
            
    except Exception as e:
        # Log error interno en consola, mostrar genérico al usuario
        print(f"[Auth Error] {e}")
        st.error("Authentication failed due to internal error.")

# --- UI Rendering ---

def show(cookie_manager):
    # CSS para centrar el login visualmente
    st.markdown("""
        <style>
            .block-container { padding-top: 3rem !important; }
        </style>
    """, unsafe_allow_html=True)

    # Layout centrado
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
            "🔒 Secure Connection (Local Network)</div>", 
            unsafe_allow_html=True
        )