import streamlit as st
import bcrypt
import time
from supabase import create_client

# --- 1. CONEXIÓN SEGURA (Patrón Unificado) ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["URL"]
        key = st.secrets["connections"]["supabase"]["KEY"]
        return create_client(url, key)
    except:
        return None

# --- 2. LÓGICA DE SEGURIDAD ---
def validar_y_actualizar(username, pass_actual, pass_nueva):
    supabase = init_connection()
    if not supabase:
        st.error("🔌 Error de conexión con la base de datos.")
        return False

    try:
        # A. Traer el hash actual del usuario
        response = supabase.table("Users").select("password").eq("username", username).execute()
        
        if not response.data:
            st.error("❌ Usuario no encontrado.")
            return False
            
        hash_db = response.data[0]['password']

        # B. Verificar que la contraseña actual sea correcta
        if not bcrypt.checkpw(pass_actual.encode('utf-8'), hash_db.encode('utf-8')):
            st.error("❌ La contraseña actual es incorrecta.")
            return False

        # C. Encriptar la NUEVA contraseña
        nuevo_hash = bcrypt.hashpw(pass_nueva.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # D. Actualizar en Supabase
        supabase.table("Users").update({"password": nuevo_hash}).eq("username", username).execute()
        
        return True

    except Exception as e:
        st.error(f"⚠️ Error técnico: {e}")
        return False

# --- 3. INTERFAZ (VISTA) ---
def show():
    st.title("⚙️ Mi Perfil")
    st.caption("Gestión de cuenta y seguridad.")
    
    # Datos de Sesión
    usuario = st.session_state.get("username", "N/A")
    nombre = st.session_state.get("real_name", "Usuario")
    rol = st.session_state.get("role", "N/A")

    # --- TARJETA DE INFORMACIÓN ---
    with st.container(border=True):
        c1, c2 = st.columns([1, 4])
        with c1:
            st.markdown("# 👤") # Avatar simple
        with c2:
            st.markdown(f"### {nombre}")
            st.markdown(f"**Usuario:** `{usuario}` &nbsp; | &nbsp; **Rol:** `{rol}`")
            st.caption("Para cambiar tu nombre o rol, contacta a un Administrador.")

    st.markdown("---")

    # --- FORMULARIO DE CAMBIO DE CLAVE ---
    st.subheader("🔐 Seguridad")
    
    with st.form("form_cambio_clave"):
        st.write("Cambiar Contraseña")
        
        p_actual = st.text_input("Contraseña Actual", type="password")
        p_nueva = st.text_input("Nueva Contraseña", type="password", help="Mínimo 6 caracteres")
        p_confirm = st.text_input("Confirmar Nueva Contraseña", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.form_submit_button("Actualizar Credenciales", type="primary"):
            # Validaciones Frontend
            if not p_actual or not p_nueva:
                st.warning("⚠️ Debes llenar todos los campos.")
            elif p_nueva != p_confirm:
                st.error("❌ Las nuevas contraseñas no coinciden.")
            elif len(p_nueva) < 6:
                st.warning("⚠️ La contraseña nueva es muy corta (mínimo 6).")
            else:
                # Lógica de Backend
                exito = validar_y_actualizar(usuario, p_actual, p_nueva)
                
                if exito:
                    st.success("✅ ¡Contraseña actualizada correctamente!")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()

if __name__ == "__main__":
    show()