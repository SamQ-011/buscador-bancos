import time
import bcrypt
import streamlit as st
from datetime import datetime, timedelta

# --- IMPORTACIÓN DE CONEXIÓN ---
# Intentamos importar desde la raíz
try:
    from conexion import get_db_connection
except ImportError:
    # Fallback por si la estructura cambia
    from conexion import get_db_connection

# --- Backend Logic ---

def login_user(username, password):
    """
    Validates credentials against PostgreSQL using bcrypt.
    """
    # USAMOS LA CONEXIÓN CENTRALIZADA
    conn = get_db_connection()
    if not conn:
        return None

    try:
        # Consulta SQL simple (sin text())
        query = 'SELECT * FROM "Users" WHERE username = :u'
        
        # Ejecutamos la consulta
        df = conn.query(query, params={"u": username}, ttl=0)
        
        if df.empty:
            return None

        user = df.iloc[0]
        stored_hash = user['password']

        # Verificar contraseña con bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return user
        return None

    except Exception as e:
        st.error(f"Login Error: {e}")
        return None

# --- UI Rendering ---

def show(cookie_manager):
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center;'>🏦</h1>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>Workspace Access</h2>", unsafe_allow_html=True)
            st.caption("Please enter your credentials.")
            
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Sign In", use_container_width=True, type="primary"):
                if username and password:
                    user = login_user(username, password)
                    
                    if user is not None:
                        if user['active']:
                            # Guardar cookie (válida por 7 días)
                            cookie_manager.set("cordoba_user", username, key="set_cookie", expires_at=datetime.now() + timedelta(days=7))
                            
                            # Actualizar estado de sesión
                            st.session_state.update({
                                "logged_in": True,
                                "username": user['username'],
                                "real_name": user['name'],
                                "role": user['role'],
                                "user_id": int(user['id'])
                            })
                            
                            st.success(f"Welcome back, {user['name']}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Account suspended. Contact Admin.")
                    else:
                        st.error("Invalid username or password.")
                else:

                    st.warning("Please fill in all fields.")
