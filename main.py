import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="Secure Portal", 
    page_icon="🏦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- IMPORTAR VISTAS ---
from vistas import login, inicio, buscador, notas, updates, perfil

# --- CSS GLOBAL CORREGIDO ---
st.markdown("""
    <style>
        /* Ocultar menú hamburguesa y footer, pero DEJAR LA BARRA SUPERIOR para que funcione la flecha */
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
    st.session_state.role = ""

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

    # --- 1. ENCABEZADO SUPERIOR (Siempre visible) ---
    # Esto va FUERA de la sidebar para que se vea siempre
    col_h1, col_h2 = st.columns([0.5, 9.5])
    with col_h1:
        # Puedes poner un st.image("logo.png") aquí si tienes uno
        st.write("🏦") 
    with col_h2:
        st.markdown("### Secure Portal")
    
    st.divider() # Línea separadora

    # --- 2. BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        # Tarjeta de Usuario
        st.caption("CONECTADO COMO:")
        st.info(f"👤 **{st.session_state.real_name}**")
        
        st.markdown("---")
        
        # Menú de Navegación
        menu = st.radio(
            "Navegación", 
            [
                "🏠 Inicio", 
                "📝 Generador Notas", 
                "🔍 Buscar Bancos", 
                "🔔 Noticias",
                "⚙️ Mi Perfil" 
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Botón Salir
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.real_name = ""
            st.rerun()

    # --- 3. CONTENIDO PRINCIPAL ---
    if menu == "🏠 Inicio":
        try:
            inicio.show()
        except:
            st.info("👋 Bienvenido al Dashboard principal")
            
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
    elif menu == "⚙️ Mi Perfil":
        perfil.show()

if __name__ == "__main__":

    main()
