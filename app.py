import streamlit as st
import pandas as pd
from datetime import datetime # Necesario para la métrica de fecha

# 1. CONFIGURACIÓN DE PÁGINA (Layout 'wide' para dashboard)
st.set_page_config(
    page_title="Creditor Search Pro", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CSS AVANZADO (Estilo Dark Mode Corporativo)
st.markdown("""
<style>
    /* Ocultar elementos nativos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilizar Inputs (Barra de búsqueda) */
    .stTextInput > div > div > input {
        background-color: #1E1E1E;
        color: white;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Estilizar Métricas (Tarjetas superiores) */
    div[data-testid="stMetric"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 3. FUNCIÓN DE CARGA ROBUSTA (Fix Windows Encoding)
@st.cache_data
def cargar_datos():
    try:
        # --- CAMBIO IMPORTANTE AQUÍ ---
        # 1. Agregamos encoding='latin1' para leer archivos guardados en Windows (tildes, ñ, etc)
        # 2. Probamos primero con comas (formato estándar)
        try:
            df = pd.read_csv("datos.csv", on_bad_lines='skip', dtype=str, encoding='latin1')
            
            # Si detecta solo 1 columna, probablemente era punto y coma
            if len(df.columns) < 2:
                raise ValueError("Posible error de separador")
                
        except:
            # Si falla, probamos con punto y coma (típico de Excel Latam)
            df = pd.read_csv("datos.csv", on_bad_lines='skip', dtype=str, encoding='latin1', sep=';')

        # Aseguramos nombres de columnas estándar
        if len(df.columns) >= 2:
            df.columns = ['Abreviacion', 'Nombre']
        
        # Limpieza básica
        df['Abreviacion'] = df['Abreviacion'].str.strip()
        df['Nombre'] = df['Nombre'].str.strip()
        
        # Eliminamos vacíos
        df = df.dropna(subset=['Abreviacion'])
        
        return df
    except Exception as e:
        # Si todo falla, devolvemos vacío para no romper la app
        return pd.DataFrame()

df = cargar_datos()

# 4. SIDEBAR PROFESIONAL
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9198/9198334.png", width=50)
    st.title("Panel de Agente")
    st.markdown("---")
    
    st.write("### ⚙️ Herramientas")
    modo = st.radio("Selecciona modo:", ["🔍 Buscador Rápido", "📊 Estadísticas", "🛠️ Reportar Error"])
    
    st.markdown("---")
    st.success("⚡ Sistema Online") 
    st.caption("v3.1 - Win Fix")

# 5. ZONA PRINCIPAL (MAIN AREA)

# Cabecera con Métricas
if not df.empty:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Total Acreedores", value=len(df), delta="Base de Datos Activa")
    with c2:
        st.metric(label="Estado del Sistema", value="Online", delta_color="normal")
    with c3:
        st.metric(label="Fecha", value=datetime.now().strftime("%d/%m/%Y"))

st.markdown("<br>", unsafe_allow_html=True) # Espacio

# Título y Buscador
st.markdown("## 🔍 Búsqueda de Alias Bancarios")
busqueda = st.text_input("", placeholder="Escribe la abreviación aquí (ej: TBOM, AMEX)...", label_visibility="collapsed").strip()

# 6. LÓGICA DE BÚSQUEDA
if busqueda:
    # Filtro
    resultados = df[df['Abreviacion'].str.contains(busqueda, case=False, na=False)]
    
    st.markdown("---")
    
    if not resultados.empty:
        st.success(f"✅ Se encontraron **{len(resultados)}** coincidencias.")
        
        # TABLA ESTILIZADA
        st.dataframe(
            resultados,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Abreviacion": st.column_config.TextColumn(
                    "Código / Alias",
                    width="medium"
                ),
                "Nombre": st.column_config.TextColumn(
                    "Nombre Oficial del Acreedor",
                    width="large"
                )
            }
        )
    else:
        # Estado "No encontrado"
        c_vacia1, c_vacia2 = st.columns([1,2])
        with c_vacia1:
             st.warning(f"Sin resultados para: **{busqueda}**")
        with c_vacia2:
            st.markdown("👉 **Sugerencias:**\n* Revisa la ortografía.\n* Intenta escribir menos letras.\n* Reporta si falta un banco nuevo.")

# 7. ESTADO DE ERROR (Si no encuentra el CSV)
elif df.empty:
    st.error("⚠️ Error Crítico: No se pudo cargar 'datos.csv'. Revisa que el archivo esté en GitHub.")
else:
    st.info("👋 **Hola Agente.** Escribe arriba para comenzar.")

