import streamlit as st

def show():
    st.set_page_config(page_title="Updates", page_icon="🔔", layout="wide")
    
    st.markdown("""
    <style>
        /* Ocultamos menú derecha y pie de página */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* ⚠️ AQUÍ YA NO ESTÁ LA LÍNEA 'header {visibility: hidden;}' */
    
        /* Tus estilos oscuros */
        .stTextInput > div > div > input {
            background-color: #1E1E1E; color: white; border: 1px solid #333; border-radius: 10px; padding: 10px;
        }
        div[data-testid="stMetric"] {
            background-color: #1E1E1E; border: 1px solid #333; border-radius: 10px; color: white;
        }
        .stTextArea > div > div > textarea {
            background-color: #1E1E1E; color: white; border: 1px solid #333; border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/9198/9198334.png", width=50)
        st.markdown("### 🔔 Noticias")
    
    st.title("🔔 Central de Noticias")
    
    st.info("👋 **¡Bienvenido a la nueva App Modular!**")
    st.write("Ahora cada herramienta tiene su propia página. Navega usando el menú de la izquierda.")
    
    st.markdown("---")
    
    st.error("🚨 **Aviso Importante**")
    st.write("Recuerden verificar el Script de Bienvenida actualizado.")