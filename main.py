import time
import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client

# Módulos internos
import estilos
# Manejo de errores en imports para evitar crash si faltan archivos
try:
    from vistas import login, inicio, buscador, notas, updates, perfil, admin_panel
except ImportError as e:
    st.error(f"Error cargando módulos de vista: {e}")
    st.stop()

# Configuración inicial de la página
st.set_page_config(
    page_title="Cordoba Workspace", 
    page_icon="🏢", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Carga de estilos CSS globales
estilos.cargar_css()

# --- Configuración y Conexión ---

@st.cache_resource
def init_connection():
    """Establece la conexión con Supabase usando secretos."""
    try:
        # Soporte dual para entorno local (secrets.toml) y despliegue
        creds = st.secrets["connections"]["supabase"] if "connections" in st.secrets else st.secrets
        return create_client(creds["URL"], creds["KEY"])
    except Exception as e:
        # En producción, esto debería loguearse en un archivo
        return None

def init_session_state():
    """Inicializa las variables de sesión requeridas."""
    defaults = {
        "logged_in": False,
        "real_name": "",
        "role": "",
        "username": ""
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Inicializamos estado
init_session_state()

# Gestor de Cookies
cookie_manager = stx.CookieManager(key="cordoba_cookies")

def intentar_reconexion():
    """
    Intenta recuperar la sesión usando la cookie almacenada 
    si el usuario no está logueado en memoria.
    """
    if st.session_state.logged_in:
        return

    # Pequeño delay para asegurar montaje del componente de cookies
    time.sleep(0.1)
    
    cookies = cookie_manager.get_all()
    if not cookies or "cordoba_user" not in cookies:
        return

    user_cookie = cookies.get("cordoba_user")
    supabase = init_connection()
    
    if supabase:
        try:
            res = supabase.table("Users").select("*").eq("username", user_cookie).execute()
            if res.data:
                user = res.data[0]
                if user.get('active', True):
                    st.session_state.update({
                        "logged_in": True,
                        "username": user['username'],
                        "real_name": user['name'],
                        "role": user['role']
                    })
                    st.rerun()
        except Exception:
            pass # Fallo silencioso en reconexión

# --- Lógica Principal ---

def main():
    intentar_reconexion()

    # Router de autenticación
    if not st.session_state.logged_in:
        login.show(cookie_manager)
        return

    # Sidebar y Navegación
    with st.sidebar:
        # Espaciador para logo (inyectado por CSS/Estilos)
        st.write("") 
        
        with st.container(border=True):
            icono = "🛡️" if st.session_state.role == "Admin" else "👤"
            st.markdown(f"**{icono} {st.session_state.real_name}**")
            st.caption(f"Perfil: {st.session_state.role}")
        
        st.markdown("---")
        
        # Definición de rutas según permisos
        if st.session_state.role == "Admin":
            rutas = {
                "🎛️ Panel Admin": admin_panel,
                "🏠 Dashboard Personal": inicio,
                "📝 Generador Notas": notas,
                "🔍 Buscar Bancos": buscador,
                "⚙️ Mi Perfil": perfil
            }
        else:
            rutas = {
                "🏠 Inicio": inicio,
                "📝 Generador Notas": notas,
                "🔍 Buscar Bancos": buscador,
                "🔔 Noticias": updates,
                "⚙️ Mi Perfil": perfil
            }

        opcion = st.radio("Navegación:", list(rutas.keys()), label_visibility="collapsed")
        st.markdown("---")
        
        # Logout logic
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            cookie_manager.delete("cordoba_user")
            # Reset de sesión manual
            for key in ["logged_in", "role", "real_name", "username"]:
                if key in st.session_state:
                    del st.session_state[key]
            
            time.sleep(0.5) 
            st.rerun()

    # Renderizado de vista seleccionada
    if opcion in rutas:
        if opcion == "🎛️ Panel Admin" and st.session_state.role != "Admin":
            st.error("Acceso denegado.")
        else:
            rutas[opcion].show()

if __name__ == "__main__":
    main()
