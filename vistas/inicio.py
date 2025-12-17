import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from supabase import create_client
import pytz 

# --- 1. CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            url = st.secrets["connections"]["supabase"]["URL"]
            key = st.secrets["connections"]["supabase"]["KEY"]
        else:
            url = st.secrets["URL"]
            key = st.secrets["KEY"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_connection()

# --- 2. FUNCIONES DE LÓGICA ---
def sumar_dias_habiles(fecha_inicio, dias_a_sumar):
    dias_agregados = 0
    fecha_actual = fecha_inicio
    if dias_a_sumar <= 0: return fecha_actual
    
    while dias_agregados < dias_a_sumar:
        fecha_actual += timedelta(days=1)
        if fecha_actual.weekday() < 5: 
            dias_agregados += 1
    return fecha_actual

# --- 3. CARGA DE DATOS ---
def cargar_noticias_activas():
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table("Updates").select("*")\
            .eq("active", True)\
            .order("date", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

def cargar_metricas_usuario(nombre_agente):
    if not supabase: return pd.DataFrame()
    try:
        # CORRECCIÓN: Buscamos por 'agent' que ahora guarda el real_name
        res = supabase.table("Logs").select("*")\
            .eq("agent", nombre_agente)\
            .order("created_at", desc=True)\
            .limit(100)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

# --- 4. VISTA PRINCIPAL ---
def show():
    # A. CONFIGURACIÓN DE TIEMPO (Eastern Time)
    zona_et = pytz.timezone('US/Eastern')
    ahora_et = datetime.now(zona_et)
    fecha_hoy_et = ahora_et.date()

    # B. ENCABEZADO
    nombre = st.session_state.get("real_name", "Agente")
    
    h1, h2 = st.columns([3, 1])
    with h1:
        st.title(f"👋 Welcome back, {nombre}")
    with h2:
        st.markdown(f"<div style='text-align: right; color: gray; padding-top: 20px;'>{ahora_et.strftime('%I:%M %p ET')}</div>", unsafe_allow_html=True)
    
    st.markdown("---")

    # C. PROCESAMIENTO DE DATOS (KPIs)
    # CORRECCIÓN: Usamos real_name para que coincida con lo que guarda notas.py
    usuario_para_busqueda = st.session_state.get("real_name", st.session_state.get("username"))
    df_logs = cargar_metricas_usuario(usuario_para_busqueda)

    total_hoy = 0
    ventas_hoy = 0
    conversion = 0
    df_hoy = pd.DataFrame()

    if not df_logs.empty:
        if 'created_at' in df_logs.columns:
            # 1. Convertir a datetime
            df_logs['created_at'] = pd.to_datetime(df_logs['created_at'])
            
            # 2. Convertir a ET
            try:
                df_logs['fecha_et'] = df_logs['created_at'].dt.tz_convert(zona_et)
            except TypeError:
                df_logs['fecha_et'] = df_logs['created_at'].dt.tz_localize('UTC').dt.tz_convert(zona_et)

            # 3. Filtrar registros de HOY
            df_hoy = df_logs[df_logs['fecha_et'].dt.date == fecha_hoy_et]
            
            # 4. Calcular Métricas
            total_hoy = len(df_hoy)
            ventas_hoy = len(df_hoy[df_hoy['result'].str.contains('Completed', case=False, na=False)])
            conversion = (ventas_hoy / total_hoy * 100) if total_hoy > 0 else 0

    # D. SECCIÓN SUPERIOR: KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🏆 Sales Today", ventas_hoy, delta="Target: 10")
    k2.metric("📞 Total Calls", total_hoy)
    k3.metric("📈 Conversion Rate", f"{conversion:.1f}%")
    
    racha = "🔥 On Fire" if ventas_hoy >= 5 else "💪 Keep Pushing"
    k4.metric("Status", racha)

    st.markdown("<br>", unsafe_allow_html=True)

    # E. SECCIÓN MEDIA: GRÁFICO (Izq) + FECHAS DE PAGO (Der)
    col_main, col_side = st.columns([2, 1])

    # --- COLUMNA IZQUIERDA: GRÁFICO ---
    with col_main:
        st.subheader("📊 Activity Overview")
        if total_hoy > 0:
            chart_data = df_hoy['result'].value_counts().reset_index()
            chart_data.columns = ['Resultado', 'Cantidad']
            
            grafico = alt.Chart(chart_data).mark_bar(cornerRadius=3).encode(
                x=alt.X('Cantidad', title=None, axis=alt.Axis(tickMinStep=1)), # Asegura enteros
                y=alt.Y('Resultado', sort='-x', title=None),
                color=alt.Color('Resultado', legend=None, scale=alt.Scale(scheme='blues')),
                tooltip=['Resultado', 'Cantidad']
            ).properties(height=250)
            
            text = grafico.mark_text(dx=3, align='left').encode(text='Cantidad')
            st.altair_chart(grafico + text, use_container_width=True)
        else:
            st.info("Waiting for data... Go to 'Generador de Notas' to start.", icon="⏳")

    # --- COLUMNA DERECHA: FECHAS DE PAGO (3 RECUADROS) ---
    with col_side:
        st.subheader("📅 Pay Dates Calculator")
        
        f_min_std = sumar_dias_habiles(ahora_et, 2) 
        f_min_ca = sumar_dias_habiles(ahora_et, 4)  
        f_max = ahora_et + timedelta(days=35) 

        # Recuadro 1: Standard
        with st.container(border=True):
            st.metric("Standard (3 days)", f_min_std.strftime('%b %d'))
        
        # Recuadro 2: California
        with st.container(border=True):
            st.metric("California (5 days)", f_min_ca.strftime('%b %d'))
            
        # Recuadro 3: Max Date (Fecha Límite)
        with st.container(border=True):
            st.metric("⛔ Max Date (35 days)", f_max.strftime('%m/%d/%Y'))

    # F. SECCIÓN INFERIOR: NOTICIAS
    st.markdown("---")
    st.subheader("📢 Company Updates")
    
    df_news = cargar_noticias_activas()
    
    if not df_news.empty:
        with st.container():
            for index, row in df_news.iterrows():
                cat = str(row.get('category', 'INFO')).strip().upper()
                titulo = row.get('title', 'Update')
                mensaje = row.get('message', '')
                fecha = row.get('date', '')

                if cat == 'CRITICAL': 
                    icon = "🔴"
                    bg_color = "rgba(255, 75, 75, 0.1)"
                elif cat == 'WARNING': 
                    icon = "🟡"
                    bg_color = "rgba(255, 235, 59, 0.1)"
                else: 
                    icon = "🔵"
                    bg_color = "rgba(33, 150, 243, 0.05)"

                st.markdown(
                    f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 3px solid gray;">
                        <small>{fecha}</small><br>
                        <strong>{icon} {titulo}</strong><br>
                        <span style="color: #333;">{mensaje}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
    else:
        st.caption("No active announcements at this time.")

if __name__ == "__main__":
    show()