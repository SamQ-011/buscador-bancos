# vistas/login.py
import time
import streamlit as st
from datetime import datetime, timedelta

# --- IMPORTACIONES ---
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

# Importamos el nuevo servicio
import services.auth_service as auth_service

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
                    # Obtenemos conexión para pasarla al servicio
                    conn = get_db_connection()
                    
                    # LLAMADA AL SERVICIO (Lógica separada)
                    user = auth_service.login_user(conn, username, password)
                    
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