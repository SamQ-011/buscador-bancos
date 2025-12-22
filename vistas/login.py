import streamlit as st
import time
import bcrypt
from datetime import datetime, timedelta
from supabase import create_client
# NO importamos stx aquí para no crear conflictos, lo recibimos como parámetro

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["URL"]
        key = st.secrets["connections"]["supabase"]["KEY"]
        return create_client(url, key)
    except:
        return None

# AHORA RECIBE EL MANAGER COMO ARGUMENTO
def show(cookie_manager):
    st.markdown("""<style>.block-container { padding-top: 50px !important; }</style>""", unsafe_allow_html=True)

    col_izq, col_centro, col_der = st.columns([3, 2, 3])

    with col_centro:
        st.markdown("<h1 style='text-align: center; font-size: 50px;'>🏦</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #0F52BA;'>Acceso</h2>", unsafe_allow_html=True)
            st.caption("Ingresa tus credenciales para continuar.")
            
            usuario = st.text_input("Usuario", placeholder="ej: jperez").strip()
            password = st.text_input("Contraseña", type="password").strip()
            st.write("") 
            
            if st.button("Entrar al Sistema", type="primary", use_container_width=True):
                if usuario and password:
                    autenticar_usuario(usuario, password, cookie_manager)
                else:
                    st.warning("⚠️ Faltan datos.")

        st.markdown("<div style='text-align: center; color: #888; font-size: 12px; margin-top: 10px;'>🔒 Conexión Segura</div>", unsafe_allow_html=True)

def autenticar_usuario(user_input, pass_input, cookie_manager):
    supabase = init_connection()
    if not supabase:
        st.error("🚨 Error de conexión.")
        return

    try:
        res = supabase.table("Users").select("*").eq("username", user_input).execute()
        
        if res.data:
            user_data = res.data[0]
            if not user_data.get('active', True):
                st.error("🚫 Cuenta desactivada.")
                return

            try:
                if bcrypt.checkpw(pass_input.encode('utf-8'), user_data['password'].encode('utf-8')):
                    # 1. Sesión en RAM
                    st.session_state.logged_in = True
                    st.session_state.username = user_data['username']
                    st.session_state.real_name = user_data['name']
                    st.session_state.role = user_data['role']
                    
                    # 2. Sesión en Cookie (1 DÍA)
                    expire = datetime.now() + timedelta(days=1)
                    cookie_manager.set('cordoba_user', user_data['username'], expires_at=expire)
                    
                    st.toast("✅ Acceso concedido.", icon="🔓")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
            except ValueError:
                st.error("⚠️ Error de seguridad.")
        else:
            st.error("❌ Usuario no encontrado.")
            
    except Exception as e:
        st.error(f"Error: {e}")