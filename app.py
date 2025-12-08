import streamlit as st
import pandas as pd
import time # Para simular carga y dar sensación de proceso

# 1. CONFIGURACIÓN DE PÁGINA (Layout 'wide' para que parezca dashboard)
st.set_page_config(
    page_title="Creditor Search Pro", 
    page_icon="🏢", 
    layout="wide", # Usamos todo el ancho de la pantalla
    initial_sidebar_state="expanded"
)

# 2. CSS AVANZADO (Estilo Dark Mode Corporativo)
st.markdown("""
<style>
    /* Ocultar elementos nativos */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Personalizar Inputs */
    .stTextInput > div > div > input {
        background-color: #1E1E1E;
        color: white;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Estilo para las métricas (Tarjetas de arriba) */
    div[data-testid="stMetric"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 3. FUNCIÓN DE CARGA (Igual que antes, pero con manejo de caché optimizado)
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("datos.xlsx") # Asegúrate que el nombre sea correcto
        if len(df.columns) >= 2:
            df.columns = ['Abreviacion', 'Nombre']
        
        # Limpieza rápida
        df['Abreviacion'] = df['Abreviacion'].astype(str).str.split('\n')
        df['Nombre'] = df['Nombre'].astype(str).str.split('\n')
        df = df.explode(['Abreviacion', 'Nombre'])
        df['Abreviacion'] = df['Abreviacion'].str.strip()
        df['Nombre'] = df['Nombre'].str.strip()
        df = df[df['Abreviacion'] != 'nan']
        return df.drop_duplicates() # Eliminamos duplicados por si acaso
    except Exception as e:
        return pd.DataFrame()

df = cargar_datos()

# 4. SIDEBAR (LA BARRA LATERAL PROFESIONAL)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9198/9198334.png", width=50) # Logo genérico o de tu empresa
    st.title("Panel de Agente")
    st.markdown("---")
    
    st.write("### ⚙️ Herramientas")
    modo = st.radio("Selecciona modo:", ["🔍 Buscador Rápido", "📊 Estadísticas", "🛠️ Reportar Error"])
    
    st.markdown("---")
    st.info("💡 **Tip Pro:** Usa `Ctrl+F` en tu navegador si la lista es muy larga.")
    st.caption("v2.1.0 - Enterprise Edition")

# 5. ZONA PRINCIPAL (MAIN AREA)

# Cabecera con Métricas (Esto da el toque "Dashboard")
if not df.empty:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Total Acreedores", value=len(df), delta="Base de Datos Activa")
    with c2:
        st.metric(label="Estado del Sistema", value="Online", delta_color="normal")
    with c3:
        # Un reloj o fecha da sensación de tiempo real
        from datetime import datetime
        st.metric(label="Fecha", value=datetime.now().strftime("%d/%m/%Y"))

st.markdown("<br>", unsafe_allow_html=True) # Espacio

# Título Principal
st.markdown("## 🔍 Búsqueda de Alias Bancarios")

# Input de Búsqueda (Grande y claro)
busqueda = st.text_input("", placeholder="Escribe la abreviación aquí (ej: TBOM, AMEX)...", label_visibility="collapsed")

# 6. LÓGICA Y RESULTADOS CON ESTILO
if busqueda:
    # Filtro
    resultados = df[df['Abreviacion'].str.contains(busqueda, case=False, na=False)]
    
    st.markdown("---") # Línea divisoria elegante
    
    if not resultados.empty:
        st.success(f"✅ Se encontraron **{len(resultados)}** coincidencias.")
        
        # TABLA PROFESIONAL (Usando column_config)
        st.dataframe(
            resultados,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Abreviacion": st.column_config.TextColumn(
                    "Código / Alias",
                    help="Abreviación encontrada en el reporte de crédito",
                    width="medium"
                ),
                "Nombre": st.column_config.TextColumn(
                    "Nombre Oficial del Acreedor",
                    help="Nombre completo para el script",
                    width="large"
                )
            }
        )
    else:
        # Estado vacío "amigable"
        col_vacia1, col_vacia2 = st.columns([1,2])
        with col_vacia1:
             st.warning(f"No hay resultados para: **{busqueda}**")
        with col_vacia2:
            st.markdown("👉 **Sugerencias:**\n* Revisa si escribiste bien la abreviación.\n* Intenta escribir solo las primeras 3 letras.\n* Si es un banco nuevo, repórtalo en el menú lateral.")

# 7. ESTADO INICIAL (Cuando no han buscado nada)
elif df.empty:
    st.error("⚠️ No se pudo cargar la base de datos 'datos.xlsx'.")
else:
    # Un mensaje de bienvenida limpio cuando entran
    st.info("👋 **Hola Agente.** Escribe en la barra de arriba para comenzar a buscar.")