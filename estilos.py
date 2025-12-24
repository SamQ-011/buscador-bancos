import streamlit as st
import base64
import os

def cargar_css():
    """
    Función para inyectar CSS personalizado y dar look corporativo.
    """
    
    # 1. Intentar cargar el logo (opcional)
    # Si tienes un archivo 'assets/logo.png', se usará.
    logo_path = os.path.join("assets", "logo.png")
    logo_html = ""
    
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        # HTML para poner el logo arriba en la sidebar
        logo_html = f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{data}" style="width: 180px; max-width: 100%;">
            </div>
        """

    # 2. El Bloque CSS
    st.markdown(f"""
        <style>
            /* --- 1. LIMPIEZA DE MARCA STREAMLIT --- */
            #MainMenu {{visibility: hidden;}} /* Ocultar hamburguesa */
            footer {{visibility: hidden;}}    /* Ocultar 'Made with Streamlit' */
            header {{visibility: hidden;}}    /* Ocultar barra de colores superior */
            
            /* --- 2. OPTIMIZACIÓN DE ESPACIO (REAL ESTATE) --- */
            
            /* Reducir el padding superior del cuerpo principal */
            .block-container {{
                padding-top: 2rem !important; 
                padding-bottom: 1rem !important;
            }}
            
            /* Compactar la Sidebar */
            [data-testid="stSidebar"] > div:first-child {{
                padding-top: 1rem;
            }}
            
            /* --- 3. ESTILOS CORPORATIVOS --- */
            
            /* Fondo de la app (Opcional: gris muy suave para descansar la vista) */
            .stApp {{
                background-color: #FAFAFA;
            }}
            
            /* Botones Primarios (Guardar/Login) con estilo más sólido */
            div.stButton > button:first-child {{
                border-radius: 6px;
                font-weight: 600;
            }}
            
            /* Inputs y Selectbox más limpios */
            .stTextInput > div > div > input {{
                border-radius: 4px;
            }}
        </style>
        
        <script>
            // Un pequeño hack JS para insertar el logo antes del menú de navegación si fuera necesario
            // (Por ahora lo manejamos con st.sidebar.markdown en el python principal si preferimos)
        </script>
    """, unsafe_allow_html=True)

    # Inyectar el logo visualmente en la sidebar usando componentes nativos
    # para asegurar que se vea siempre arriba
    if logo_html:
        st.sidebar.markdown(logo_html, unsafe_allow_html=True)
