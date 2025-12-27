import os
import base64
import streamlit as st

def cargar_css():
    """
    Inyecta estilos CSS globales (overrides) y renderiza elementos de marca (logo)
    en el sidebar.
    """
    
    # --- Configuración de Assets ---
    logo_path = os.path.join("assets", "logo.png")
    sidebar_logo_html = ""
    
    # Carga de logo en base64 para inyección HTML directa
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            
            sidebar_logo_html = f"""
                <div style="text-align: center; margin-bottom: 2rem;">
                    <img src="data:image/png;base64,{data}" style="width: 180px; max-width: 100%;">
                </div>
            """
        except Exception as e:
            # Loguear error pero no detener ejecución
            print(f"Warning: No se pudo cargar el logo. {e}")

    # --- Inyección de CSS ---
    st.markdown("""
        <style>
            /* Streamlit UI Overrides */
            #MainMenu, footer, header {
                visibility: hidden;
            }
            
            /* Viewport Optimization */
            .block-container {
                padding-top: 2rem !important; 
                padding-bottom: 2rem !important;
            }
            
            /* Sidebar Layout */
            [data-testid="stSidebar"] > div:first-child {
                padding-top: 1rem;
            }
            
            /* Global Theme Colors */
            .stApp {
                background-color: #FAFAFA;
            }
            
            /* Components: Buttons & Inputs */
            div.stButton > button:first-child {
                border-radius: 4px;
                font-weight: 600;
                border: 1px solid #D1D5DB; /* Tailwind Gray-300 */
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            }
            
            div.stButton > button:first-child:hover {
                border-color: #9CA3AF;
            }
            
            .stTextInput > div > div > input {
                border-radius: 4px;
            }
        </style>
    """, unsafe_allow_html=True)

    # Renderizado condicional del logo
    if sidebar_logo_html:
        st.sidebar.markdown(sidebar_logo_html, unsafe_allow_html=True)
