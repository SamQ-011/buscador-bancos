import streamlit as st
import pandas as pd
from datetime import datetime

# IMPORTAMOS TUS PÁGINAS COMO SI FUERAN LIBRERÍAS
# (Asegúrate de que la carpeta se llame 'vistas' y los archivos tengan estos nombres)
# Nota: Python no ama los emojis en nombres de archivo al importar, 
# si te da error, renombra los archivos a 'notas.py' y 'updates.py' en la carpeta.
from vistas import notas, updates 

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Panel Agente", page_icon="🏢", layout="wide")

# 2. CSS (Tu estilo oscuro corregido)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* header {visibility: hidden;} <--- LO DEJAMOS VISIBLE PARA PODER ABRIR EL MENU */
    
    .stTextInput > div > div > input {
        background-color: #1E1E1E; color: white; border: 1px solid #333; border-radius: 10px; padding: 10px;
    }
    div[data-testid="stMetric"] {
        background-color: #1E1E1E; border: 1px solid #333; border-radius: 10px; color: white;
    }
</style>
""", unsafe_allow_html=True)

# 3. CARGA DE DATOS (Solo necesaria para el buscador)
@st.cache_data
def cargar_datos():
    try:
        try:
            df = pd.read_csv("datos.csv", on_bad_lines='skip', dtype=str, encoding='latin1')
            if len(df.columns) < 2: raise ValueError
        except:
            df = pd.read_csv("datos.csv", on_bad_lines='skip', dtype=str, encoding='latin1', sep=';')

        if len(df.columns) >= 2:
            df.columns = ['Abreviacion', 'Nombre']
        
        df['Abreviacion'] = df['Abreviacion'].str.strip()
        df['Nombre'] = df['Nombre'].str.strip()
        df = df.dropna(subset=['Abreviacion'])
        return df
    except Exception:
        return pd.DataFrame()

df = cargar_datos()

# ============================================
# 4. LA BARRA LATERAL (TU MENÚ FAVORITO)
# ============================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9198/9198334.png", width=50)
    st.title("Menú Principal")
    
    # ¡AQUÍ ESTÁ EL RADIO BUTTON QUE TE GUSTA!
    seleccion = st.radio(
        "Ir a:", 
        ["🔍 Buscador", "📝 Notas CRM", "🔔 Noticias"],
        index=0 # Por defecto arranca en el primero
    )
    
    st.markdown("---")
    st.caption("v5.0 - Custom UI")

# ============================================
# 5. EL CEREBRO (MUESTRA LO QUE ELIGIERON)
# ============================================

if seleccion == "🔍 Buscador":
    # --- CÓDIGO DEL BUSCADOR DIRECTO AQUÍ ---
    st.title("🔍 Buscador de Acreedores")

    if not df.empty:
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total Acreedores", len(df))
        with c2: st.metric("Sistema", "Online", delta_color="normal")
        with c3: st.metric("Fecha", datetime.now().strftime("%d/%m/%Y"))

    st.markdown("---")

    busqueda = st.text_input("", placeholder="Escribe la abreviación aquí...", label_visibility="collapsed").strip()

    if busqueda:
        resultados = df[df['Abreviacion'].str.contains(busqueda, case=False, na=False)]
        if not resultados.empty:
            st.success(f"✅ {len(resultados)} encontrados.")
            st.dataframe(
                resultados, use_container_width=True, hide_index=True,
                column_config={"Abreviacion": st.column_config.TextColumn("Código", width="medium"), "Nombre": st.column_config.TextColumn("Nombre Oficial", width="large")}
            )
        else:
            st.warning(f"Sin resultados para: **'{busqueda}'**")

elif seleccion == "📝 Notas CRM":
    # LLAMAMOS AL ARCHIVO DE NOTAS
    notas.show()

elif seleccion == "🔔 Noticias":
    # LLAMAMOS AL ARCHIVO DE UPDATES
    updates.show()