import streamlit as st

# Configuración de página (Debe ser la primera línea de código siempre)
st.set_page_config(
    page_title="Secure Portal", 
    page_icon="🏦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- IMPORTAR VISTAS ---
# Importamos los archivos que creaste en la carpeta vistas
from vistas import login, inicio, buscador, notas, updates, perfil

# --- CSS GLOBAL (Estilo Corporativo & Limpieza) ---
st.markdown("""
    <style>
        /* Ocultar marcas de agua de Streamlit */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Fondo general gris suave profesional */
        .stApp {
            background-color: #F8F9FA;
        }
        
        /* Ajuste de la barra lateral */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E0E0E0;
        }
        /* --- AÑADIR ESTO AL FINAL DEL STYLE EN main.py --- */

/* Estilo de Tarjeta para las Métricas */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF; /* Fondo blanco */
            border: 1px solid #E0E0E0; /* Borde gris muy suave */
            border-radius: 10px;       /* Bordes redondeados */
            padding: 15px;             /* Espacio interno */
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); /* Sombra suave */
            transition: transform 0.2s; /* Efecto al pasar el mouse */
        }

        /* Efecto Hover (se levanta un poquito) */
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.1);
        }

        /* Títulos más bonitos */
        h1, h2, h3 {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #1f2937; /* Gris oscuro casi negro */
            letter-spacing: -0.5px;
        }    
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAR ESTADO DE SESIÓN ---
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
    # CASO 2: USUARIO LOGUEADO (DASHBOARD)
    # ==========================================
    
    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        # Logo o Ícono
        st.markdown("<h2 style='text-align: center;'>🏦 Portal</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Tarjeta de Usuario
        st.caption("CONECTADO COMO:")
        st.info(f"👤 **{st.session_state.real_name}**")
        
        st.markdown("---")
        
        # Menú de Navegación
        menu = st.radio(
            "Ir a:", 
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

    # --- CUERPO PRINCIPAL ---
    # Aquí llamamos a los archivos de la carpeta 'vistas' según el menú
    
    if menu == "🏠 Inicio":
        try:
            inicio.show()
        except:
            st.warning("⚠️ El módulo 'Inicio' aún no tiene código.")
            
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