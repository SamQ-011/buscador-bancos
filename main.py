import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Secure Portal", 
    page_icon="🏦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- IMPORTAR VISTAS ---
# Asegúrate de que admin_panel exista en la carpeta vistas
from vistas import login, inicio, buscador, notas, updates, perfil, admin_panel

# --- CSS GLOBAL ---
st.markdown("""
    <style>
        /* Ocultar menú hamburguesa y footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        
        /* Fondo general */
        .stApp {
            background-color: #F8F9FA;
        }
        
        /* Ajuste de la barra lateral */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E0E0E0;
        }

        /* Estilo de Tarjeta para las Métricas */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s;
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.1);
        }

        h1, h2, h3 {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #1f2937;
            letter-spacing: -0.5px;
        }    
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAR ESTADO ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "real_name" not in st.session_state:
    st.session_state.real_name = ""
if "role" not in st.session_state:
    st.session_state.role = "" # Puede ser "admin" o "agent"

def main():
    # ==========================================
    # CASO 1: USUARIO NO LOGUEADO
    # ==========================================
    if not st.session_state.logged_in:
        login.show()
        return

    # ==========================================
    # CASO 2: USUARIO LOGUEADO
    # ==========================================

    # --- 1. ENCABEZADO SUPERIOR ---
    

    # --- 2. BARRA LATERAL (SIDEBAR) INTELIGENTE ---
    with st.sidebar:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        # Tarjeta de Usuario con Badge de Rol
        st.caption("CONECTADO COMO:")
        
        # Mostramos un icono diferente si es admin
        icono_user = "👮‍♂️" if st.session_state.role == "Admin" else "👤"
        st.info(f"{icono_user} **{st.session_state.real_name}**")
        
        st.markdown("---")
        
        # --- LÓGICA DE MENÚ SEGÚN ROL ---
        # Aquí definimos qué opciones ve cada quién
        if st.session_state.role == "Admin":
            opciones_menu = [
                "🎛️ Panel Admin",     # <--- Home exclusiva de Admin
                "📝 Generador Notas",
                "🔍 Buscar Bancos",
                # El admin gestiona noticias en el panel, no necesita leerlas aquí
                "⚙️ Mi Perfil"
            ]
        else:
            # Menú estándar para Agentes
            opciones_menu = [
                "🏠 Inicio", 
                "📝 Generador Notas", 
                "🔍 Buscar Bancos", 
                "🔔 Noticias",
                "⚙️ Mi Perfil" 
            ]

        # Renderizar el menú
        menu = st.radio(
            "Navegación", 
            opciones_menu,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Botón Salir
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.real_name = ""
            st.session_state.role = ""
            st.rerun()

    # --- 3. RUTEO DE VISTAS ---
    
    # Vista Exclusiva Admin
    if menu == "🎛️ Panel Admin":
        # Verificación extra de seguridad por si alguien fuerza la variable menu
        if st.session_state.role == "Admin":
            admin_panel.show()
        else:
            st.error("⛔ Acceso Denegado")

    # Vistas Comunes / Agente
    elif menu == "🏠 Inicio":
        inicio.show()
        
    elif menu == "📝 Generador Notas":
        notas.show()
        
    elif menu == "🔍 Buscar Bancos":
        buscador.show()
        
    elif menu == "🔔 Noticias":
        updates.show()
    
    elif menu == "⚙️ Mi Perfil":
        perfil.show()

if __name__ == "__main__":
    main()