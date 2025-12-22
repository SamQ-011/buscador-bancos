import streamlit as st
import extra_streamlit_components as stx
import time
from supabase import create_client

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Cordoba Workspace", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS GLOBAL ---
st.markdown("""
    <style>
        html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        .stApp { background-color: #F8F9FA; }
        section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E7EB; }
        div[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["URL"]
        key = st.secrets["connections"]["supabase"]["KEY"]
        return create_client(url, key)
    except:
        return None

# --- GESTIÓN DE ESTADO ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "real_name" not in st.session_state: st.session_state.real_name = ""
if "role" not in st.session_state: st.session_state.role = "" 

# --- IMPORTADOR ---
try:
    from vistas import login, inicio, buscador, notas, updates, perfil, admin_panel
except ImportError as e:
    st.error(f"🚨 Error Crítico: {e}")
    st.stop()

# ==========================================
# 🍪 GESTIÓN DE COOKIES (SOLUCIÓN F5)
# ==========================================
# Instanciamos el manager AQUÍ con una clave única
cookie_manager = stx.CookieManager(key="cordoba_cookies")

def intentar_reconexion():
    # Solo intentamos si no estamos logueados en RAM
    if not st.session_state.logged_in:
        
        # TRUCO: A veces la cookie tarda un milisegundo en leerse tras F5
        # Intentamos obtener todas las cookies primero para "despertar" al componente
        cookies = cookie_manager.get_all()
        cookie_user = cookies.get("cordoba_user") if cookies else None
        
        if cookie_user:
            supabase = init_connection()
            try:
                res = supabase.table("Users").select("*").eq("username", cookie_user).execute()
                if res.data:
                    user_data = res.data[0]
                    if user_data.get('active', True):
                        st.session_state.logged_in = True
                        st.session_state.username = user_data['username']
                        st.session_state.real_name = user_data['name']
                        st.session_state.role = user_data['role']
                        # Si encontramos la cookie y validamos, forzamos recarga visual inmediata
                        st.rerun()
            except Exception as e:
                print(f"Error reconexión: {e}")

# ==========================================
# APP PRINCIPAL
# ==========================================
def main():
    # 1. Intentar revivir sesión
    intentar_reconexion()

    # 2. Si falló la reconexión -> Mostrar Login
    # IMPORTANTE: Le pasamos el 'cookie_manager' existente a login.show
    if not st.session_state.logged_in:
        login.show(cookie_manager)
        return

    # 3. Si estamos logueados -> Mostrar App
    with st.sidebar:
        st.write("") 
        with st.container(border=True):
            icono = "🛡️" if st.session_state.role == "Admin" else "👤"
            st.markdown(f"**{icono} {st.session_state.real_name}**")
            st.caption(f"Perfil: {st.session_state.role}")
        st.markdown("---")
        
        if st.session_state.role == "Admin":
            opciones = ["🎛️ Panel Admin", "🏠 Dashboard Personal", "📝 Generador Notas", "🔍 Buscar Bancos", "⚙️ Mi Perfil"]
        else:
            opciones = ["🏠 Inicio", "📝 Generador Notas", "🔍 Buscar Bancos", "🔔 Noticias", "⚙️ Mi Perfil"]

        selection = st.radio("Ir a:", opciones, label_visibility="collapsed")
        st.markdown("---")
        
        # LOGOUT
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            cookie_manager.delete("cordoba_user")
            st.session_state.logged_in = False
            st.session_state.real_name = ""
            st.session_state.role = ""
            st.rerun()

    # ROUTER
    if selection == "🎛️ Panel Admin":
        if st.session_state.role == "Admin": admin_panel.show()
        else: st.error("⛔ Acceso Restringido")
    elif selection in ["🏠 Inicio", "🏠 Dashboard Personal"]:
        inicio.show()
    elif selection == "📝 Generador Notas":
        notas.show()
    elif selection == "🔍 Buscar Bancos":
        buscador.show()
    elif selection == "🔔 Noticias":
        updates.show()
    elif selection == "⚙️ Mi Perfil":
        perfil.show()

if __name__ == "__main__":
    main()