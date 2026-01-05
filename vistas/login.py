import time
import streamlit as st
from datetime import datetime, timedelta
from conexion import get_db_connection
import services.auth_service as auth_service

def show(cookie_manager):
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        with st.container(border=True):
            st.markdown("<h1 style='text-align: center;'>🏦</h1>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>Workspace Access</h2>", unsafe_allow_html=True)
            
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Sign In", use_container_width=True, type="primary"):
                if username and password:
                    conn = get_db_connection()
                    user = auth_service.login_user(conn, username, password)
                    
                    if user:
                        if user.get('active', True):
                            # Guardar cookie (7 días)
                            cookie_manager.set("cordoba_user", username, key="set_cookie", expires_at=datetime.now() + timedelta(days=7))
                            
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
                            st.error("Cuenta suspendida.")
                    else:
                        st.error("Credenciales inválidas.")
                else:
                    st.warning("Completa todos los campos.")