import time
import streamlit as st
import extra_streamlit_components as stx

# --- 1. Importaciones y Manejo de Errores ---
try:
    import estilos 
    from conexion import get_db_connection
    import services.auth_service as auth_service
    
    # IMPORTAMOS TODAS LAS VISTAS (Ya no están comentadas)
    from vistas import login, buscador, updates, inicio, notas, perfil, admin_panel, lab_parser

except ImportError as e:
    st.error(f"Error cargando módulos: {e}")
    st.stop()

# --- 2. Configuración de Página ---
st.set_page_config(
    page_title="Cordoba Workspace", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar CSS
estilos.cargar_css()

# --- 3. Inicialización de Estado ---
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False, 
        "real_name": "", 
        "role": "", 
        "username": "", 
        "user_id": None
    })

cookie_manager = stx.CookieManager(key="cordoba_cookies")

# --- 4. Lógica de Reconexión ---
def intentar_reconexion():
    """Intenta reconectar usando cookies y auth_service."""
    if st.session_state.logged_in: return

    time.sleep(0.1)
    cookies = cookie_manager.get_all()
    
    if cookies and "cordoba_user" in cookies:
        user_cookie = cookies.get("cordoba_user")
        conn = get_db_connection()
        
        # Usamos el servicio para validar
        user = auth_service.get_user_by_username(conn, user_cookie)
        
        if user and user.get('active', True):
            st.session_state.update({
                "logged_in": True,
                "username": user['username'],
                "real_name": user['name'],
                "role": user['role'],
                "user_id": int(user['id'])
            })
            st.rerun()

# --- 5. Main Loop ---
def main():
    intentar_reconexion()

    # Si no está logueado, mostrar Login
    if not st.session_state.logged_in:
        login.show(cookie_manager)
        return

    # --- Sidebar y Menú ---
    with st.sidebar:
        st.write("")
        with st.container(border=True):
            # Icono dinámico según rol
            icono = "🛡️" if st.session_state.role == "Admin" else "👤"
            st.markdown(f"**{icono} {st.session_state.real_name}**")
            st.caption(f"Rol: {st.session_state.role}")
        
        st.markdown("---")
        
        # --- DEFINICIÓN DE RUTAS POR ROL ---
        # Aquí es donde recuperamos las vistas perdidas
        
        if st.session_state.role == "Admin":
            rutas = {
                "🎛️ Admin Panel": admin_panel,
                "🏠 Inicio": inicio,
                "🔍 Buscador": buscador,
                "📝 Notas": notas,
                "🔔 Novedades": updates,
                "⚙️ Perfil": perfil,
                "⚙️ Parser": lab_parser
            }
        else:
            # Vistas para Agentes / Usuarios normales
            rutas = {
                "🏠 Inicio": inicio,
                "🔍 Buscador": buscador,
                "📝 Notas": notas,
                "🔔 Novedades": updates,
                "⚙️ Perfil": perfil,
                "⚙️ Parser": lab_parser
            }
        
        # Selector de menú
        opcion = st.radio("Navegación:", list(rutas.keys()), label_visibility="collapsed")
        
        st.markdown("---")
        
        # Botón de Salir
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            cookie_manager.delete("cordoba_user")
            st.session_state.clear()
            st.rerun()

    # --- Renderizar Vista Seleccionada ---
    if opcion in rutas:
        # Doble verificación de seguridad para Admin
        if opcion == "🎛️ Admin Panel" and st.session_state.role != "Admin":
            st.error("⛔ Acceso Denegado: Se requieren permisos de Administrador.")
        else:
            rutas[opcion].show()

if __name__ == "__main__":

    main()

