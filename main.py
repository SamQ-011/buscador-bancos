import time
import streamlit as st
import extra_streamlit_components as stx

# Módulos internos
import estilos
# Importamos la conexión centralizada
from conexion import get_db_connection 

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

# --- Gestión de Estado y Sesión ---

def init_session_state():
    """Inicializa las variables de sesión requeridas."""
    defaults = {
        "logged_in": False,
        "real_name": "",
        "role": "",
        "username": "",
        "user_id": None
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
    conectando a la BD a través del gestor centralizado.
    """
    if st.session_state.logged_in:
        return

    time.sleep(0.1)
    
    cookies = cookie_manager.get_all()
    if not cookies or "cordoba_user" not in cookies:
        return

    user_cookie = cookies.get("cordoba_user")
    
    # USAMOS LA CONEXIÓN CENTRALIZADA
    conn = get_db_connection()
    
    if conn:
        try:
            # Consulta SQL simple (string) para evitar problemas de hash
            query = 'SELECT * FROM "Users" WHERE username = :u'
            df = conn.query(query, params={"u": user_cookie}, ttl=0)
            
            if not df.empty:
                user = df.iloc[0].to_dict()
                
                if user.get('active', True):
                    st.session_state.update({
                        "logged_in": True,
                        "username": user['username'],
                        "real_name": user['name'],
                        "role": user['role'],
                        "user_id": user['id']
                    })
                    st.rerun()
        except Exception as e:
            print(f"Reconnection error: {e}")
            pass 

# --- Lógica Principal ---

def main():
    intentar_reconexion()

    # Router de autenticación
    if not st.session_state.logged_in:
        login.show(cookie_manager)
        return

    # Sidebar y Navegación
    with st.sidebar:
        st.write("") 
        
        with st.container(border=True):
            icono = "🛡️" if st.session_state.role == "Admin" else "👤"
            st.markdown(f"**{icono} {st.session_state.real_name}**")
            st.caption(f"Profile: {st.session_state.role}")
        
        st.markdown("---")
        
        # Definición de rutas según permisos
        if st.session_state.role == "Admin":
            rutas = {
                "🎛️ Admin Panel": admin_panel,
                "🏠 Personal Dashboard": inicio,
                "📝 Notes": notas,
                "🔍 Search Creditor": buscador,
                "⚙️ My profile": perfil
            }
        else:
            rutas = {
                "🏠 Home": inicio,
                "📝 Notes": notas,
                "🔍 Search Creditor": buscador,
                "🔔 Updates": updates,
                "⚙️ My profile": perfil
            }

        opcion = st.radio("Navegación:", list(rutas.keys()), label_visibility="collapsed")
        st.markdown("---")
        
        if st.button("🚪 Log out", use_container_width=True):
            cookie_manager.delete("cordoba_user")
            for key in ["logged_in", "role", "real_name", "username", "user_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            
            time.sleep(0.5) 
            st.rerun()

    # Renderizado de vista seleccionada
    if opcion in rutas:
        if opcion == "🎛️ Admin Panel" and st.session_state.role != "Admin":
            st.error("Acceso denegado.")
        else:
            rutas[opcion].show()

if __name__ == "__main__":
    main()