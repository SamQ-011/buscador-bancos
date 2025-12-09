import streamlit as st
import pandas as pd
from datetime import datetime, timedelta 

# IMPORTAMOS TUS PÁGINAS
from vistas import notas, updates 

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Panel Agente", page_icon="🏢", layout="wide")

# 2. CSS (AQUÍ ESTÁ EL CAMBIO DE COLOR)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* MODIFICADO: Color #262730 para que coincida con la Barra Lateral */
    .stTextInput > div > div > input {
        background-color: #262730; 
        color: white; 
        border: 1px solid #464B5C; /* Borde sutil para resaltar */
        border-radius: 10px; 
        padding: 10px;
    }
    
    /* MODIFICADO: Color #262730 para las Tarjetas de Arriba */
    div[data-testid="stMetric"] {
        background-color: #262730; 
        border: 1px solid #464B5C; 
        border-radius: 10px; 
        color: white;
        text-align: center;
        padding: 10px;
    }
    
    /* Centrar etiqueta pequeña */
    div[data-testid="stMetricLabel"] > div {
        justify-content: center;
        color: #A0A0A0; /* Texto un poco más claro */
    }
</style>
""", unsafe_allow_html=True)

# 3. FUNCIONES
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

def sumar_dias_habiles(fecha_inicio, dias_a_sumar):
    dias_agregados = 0
    fecha_actual = fecha_inicio
    if dias_a_sumar <= 0: return fecha_actual
    
    while dias_agregados < dias_a_sumar:
        fecha_actual += timedelta(days=1)
        if fecha_actual.weekday() < 5: 
            dias_agregados += 1
    return fecha_actual

df = cargar_datos()

# ============================================
# 4. LA BARRA LATERAL
# ============================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9198/9198334.png", width=50)
    st.title("Menú Principal")
    
    seleccion = st.radio(
        "Ir a:", 
        ["🔍 Buscador", "📝 Notas CRM", "🔔 Noticias"],
        index=0 
    )
    
    st.markdown("---")
    st.caption("v5.2 - Color Match")

# ============================================
# 5. LÓGICA PRINCIPAL
# ============================================

if seleccion == "🔍 Buscador":
    st.title("🔍 Buscador de Acreedores")

    # CÁLCULOS
    hoy = datetime.now()
    f_min_std = sumar_dias_habiles(hoy, 3) 
    f_min_ca = sumar_dias_habiles(hoy, 5)  
    f_max = hoy + timedelta(days=35)       

    # TARJETAS (Ahora combinarán con el sidebar)
    c1, c2, c3 = st.columns(3)
    
    with c1: 
        if not df.empty:
            st.metric("Total Acreedores", len(df), "Base Activa")
        else:
            st.metric("Total Acreedores", 0)
            
    with c2: 
        st.metric(
            label="📅 1er Pago Mínimo (3 Business Days)", 
            value=f_min_std.strftime("%m/%d/%Y"), 
            delta=f"California (5 Business Days): {f_min_ca.strftime('%m/%d/%Y')}",
            delta_color="off"
        )
        
    with c3: 
        st.metric(
            label="⛔ Fecha Límite 1er Pago (Max 35 Días)", 
            value=f_max.strftime("%m/%d/%Y"), 
            delta="Días Calendario",
            delta_color="inverse"
        )

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
    notas.show()

elif seleccion == "🔔 Noticias":
    updates.show()
