import time
import streamlit as st
import extra_streamlit_components as stx

# --- 1. Importaciones y Manejo de Errores ---
try:
    import estilos 
    from conexion import get_db_connection
    import services.auth_service as auth_service
    # NUEVO: Importamos el servicio de updates para la alarma
    import services.updates_service as updates_service
    
    # VISTAS
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

# Estado para controlar que la alarma suene solo una vez por sesión
if "global_alarm_shown" not in st.session_state:
    st.session_state.global_alarm_shown = False

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

    # =======================================================
    # 🚨 SISTEMA DE ALARMA GLOBAL (INYECCIÓN)
    # =======================================================
    try:
        conn = get_db_connection()
        # 1. Traer noticias y leídos
        df_upd = updates_service.fetch_updates(conn)
        reads = updates_service.fetch_read_ids(conn, st.session_state.username)
        
        # 2. Filtrar CUALQUIER mensaje no leído
        if not df_upd.empty:
            # Obtenemos todos los que NO están en la lista de leídos
            unread = df_upd[~df_upd['id'].isin(reads)]
            
            if not unread.empty:
                count = len(unread)
                
                # 3. Detectar gravedad para elegir el color
                # Convertimos a mayúsculas para asegurar coincidencia
                cats = unread['category'].str.strip().str.upper().values
                
                if 'CRITICAL' in cats:
                    # Si hay AL MENOS UN crítico, ponemos alerta ROJA
                    st.sidebar.error(
                        f"🔥 **ATENCIÓN**\nTienes {count} avisos pendientes."
                    )
                elif 'WARNING' in cats:
                    # Si hay advertencias, ponemos alerta AMARILLA
                    st.sidebar.warning(
                        f"⚠️ **Pendientes**\nTienes {count} avisos sin leer."
                    )
                else:
                    # Si todo es tranquilo (Info/Success), ponemos alerta AZUL
                    st.sidebar.info(
                        f"📢 **Novedades**\nTienes {count} mensajes nuevos."
                    )

    except Exception as e:
        print(f"Error en alarma global: {e}")
    # =======================================================

    # --- Sidebar y Menú ---
    with st.sidebar:
        st.write("")
        with st.container(border=True):
            icono = "🛡️" if st.session_state.role == "Admin" else "👤"
            st.markdown(f"**{icono} {st.session_state.real_name}**")
            st.caption(f"Rol: {st.session_state.role}")
        
        st.markdown("---")
        
        # Rutas
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
            rutas = {
                "🏠 Inicio": inicio,
                "🔍 Buscador": buscador,
                "📝 Notas": notas,
                "🔔 Novedades": updates,
                "⚙️ Perfil": perfil,
                "⚙️ Parser": lab_parser
            }
        
        opcion = st.radio("Navegación:", list(rutas.keys()), label_visibility="collapsed")
        
        st.markdown("---")
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            cookie_manager.delete("cordoba_user")
            st.session_state.clear()
            st.rerun()

    # --- Renderizar Vista ---
    if opcion in rutas:
        if opcion == "🎛️ Admin Panel" and st.session_state.role != "Admin":
            st.error("⛔ Acceso Denegado.")
        else:
            rutas[opcion].show()

if __name__ == "__main__":
    main()