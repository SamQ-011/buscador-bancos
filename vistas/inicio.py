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
        url = st.secrets["connections"]["supabase"]["URL"]
        key = st.secrets["connections"]["supabase"]["KEY"]
        return create_client(url, key)
    except:
        return None

# --- 2. LÓGICA DE FECHAS (ALGORITMO CORREGIDO) ---

FERIADOS_US_2025 = [
    (1, 1),   # New Year's Day
    (1, 20),  # MLK Jr. Day
    (2, 17),  # Washington's Birthday
    (5, 26),  # Memorial Day
    (6, 19),  # Juneteenth
    (7, 4),   # Independence Day
    (9, 1),   # Labor Day
    (10, 13), # Columbus Day
    (11, 11), # Veterans Day
    (11, 27), # Thanksgiving Day
    (12, 25)  # Christmas Day 🎄
]

def es_feriado(fecha):
    return (fecha.month, fecha.day) in FERIADOS_US_2025

def get_fechas_clave():
    zona_et = pytz.timezone('US/Eastern')
    ahora = datetime.now(zona_et)
    hoy = ahora.date()
    # Inicio de Semana (Lunes) y Mes
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)
    return zona_et, ahora, hoy, inicio_semana, inicio_mes

def calcular_fecha_pago(fecha_inicio, dias_objetivo):
    """
    Algoritmo de Conteo Inclusivo:
    - Si HOY es hábil, HOY cuenta como Día 1.
    - Si HOY NO es hábil, buscamos el siguiente.
    """
    fecha_cursor = fecha_inicio
    dias_contados = 0
    
    # Bucle infinito hasta completar los días requeridos (3 o 5)
    while dias_contados < dias_objetivo:
        # 1. Analizar el día donde está el cursor
        es_fin_semana = fecha_cursor.weekday() >= 5 # 5=Sab, 6=Dom
        es_holidays = es_feriado(fecha_cursor)
        
        # 2. Si es un día válido, lo contamos
        if not es_fin_semana and not es_holidays:
            dias_contados += 1
            
            # Si ya llegamos a la meta (ej: día 3), ESTA es la fecha. Paramos aquí.
            if dias_contados == dias_objetivo:
                return fecha_cursor
        
        # 3. Si no hemos terminado (o el día actual no valía), pasamos a mañana
        fecha_cursor += timedelta(days=1)
            
    return fecha_cursor

# --- 3. CARGA DE DATOS ---
def cargar_noticias_activas(supabase):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table("Updates").select("*")\
            .eq("active", True)\
            .order("date", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def cargar_logs_del_mes(supabase, nombre_agente, fecha_inicio_mes_et):
    if not supabase: return pd.DataFrame()
    try:
        inicio_utc = fecha_inicio_mes_et.astimezone(pytz.utc).isoformat()
        res = supabase.table("Logs").select("*")\
            .eq("agent", nombre_agente)\
            .gte("created_at", inicio_utc)\
            .order("created_at", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- 4. COMPONENTE UI ---
def tarjeta_progreso(titulo, valor, meta):
    progreso = min(valor / meta, 1.0) if meta > 0 else 0
    porcentaje = int(progreso * 100)
    color_texto = "#ff4444" 
    if porcentaje >= 50: color_texto = "#ffbb33"
    if porcentaje >= 100: color_texto = "#00C851"
    
    with st.container(border=True):
        st.caption(titulo)
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"<h2 style='margin:0;'>{valor} <small style='color:gray; font-size:14px'>/ {meta}</small></h2>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<h3 style='text-align:right; color:{color_texto}; margin:0;'>{porcentaje}%</h3>", unsafe_allow_html=True)
        st.progress(progreso)

# --- 5. VISTA PRINCIPAL ---
def show():
    supabase = init_connection()

    # A. TIEMPO
    zona_et, ahora_et, hoy, inicio_semana, inicio_mes_dt = get_fechas_clave()
    inicio_mes_full = datetime.combine(inicio_mes_dt, datetime.min.time()).replace(tzinfo=zona_et)
    nombre = st.session_state.get("real_name", "Agente")
    
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f"### 🚀 Hola, {nombre}")
    with h2:
        st.markdown(f"<div style='text-align: right; font-weight: bold; color: #555;'>🕒 {ahora_et.strftime('%I:%M %p')} ET</div>", unsafe_allow_html=True)
    
    st.markdown("---")

    # B. CALCULADORA DE FECHAS (ALGORITMO NUEVO)
    st.subheader("📅 Fechas de Pago")
    
    # Usamos la nueva función con 3 y 5 días
    f_std = calcular_fecha_pago(ahora_et, 3) 
    f_ca = calcular_fecha_pago(ahora_et, 5)  
    f_max = ahora_et + timedelta(days=35)    # Max Date sigue siendo calendario

    col_d1, col_d2, col_d3 = st.columns(3)
    css_fecha = "margin: 0; font-size: 1.6rem; font-weight: 700; color: #2C3E50;"
    css_sub = "margin: 0; color: #7F8C8D; font-size: 0.85rem;"

    with col_d1:
        with st.container(border=True):
            st.markdown(f"<p style='{css_sub}'>Standard (3 Business Days)</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{css_fecha}'>{f_std.strftime('%b %d')}</p>", unsafe_allow_html=True)
    
    with col_d2:
        with st.container(border=True):
            st.markdown(f"<p style='{css_sub}'>California (5 Business Days)</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{css_fecha}'>{f_ca.strftime('%b %d')}</p>", unsafe_allow_html=True)

    with col_d3:
        with st.container(border=True):
            st.markdown(f"<p style='{css_sub}'>⛔ Max Date (35 Days)</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{css_fecha}'>{f_max.strftime('%m/%d/%Y')}</p>", unsafe_allow_html=True)

    st.write("") 

    # C. DASHBOARD
    agente_filtro = st.session_state.get("real_name", "")
    df_raw = cargar_logs_del_mes(supabase, agente_filtro, inicio_mes_full)
    
    if not df_raw.empty and 'created_at' in df_raw.columns:
        df_raw['created_at'] = pd.to_datetime(df_raw['created_at'])
        df_raw['fecha_et'] = df_raw['created_at'].apply(
            lambda x: x.tz_convert(zona_et) if x.tzinfo else x.tz_localize('UTC').tz_convert(zona_et)
        )
        df_raw['fecha_date'] = df_raw['fecha_et'].dt.date

    st.subheader("📊 Tu Rendimiento")
    tab_hoy, tab_semana, tab_mes = st.tabs(["📅 Hoy", "🗓️ Esta Semana", "🏆 Este Mes"])

    def render_tab_content(fecha_filtro, meta_ventas, tag):
        if df_raw.empty:
            df_filtered = pd.DataFrame(columns=['result'])
        else:
            df_filtered = df_raw[df_raw['fecha_date'] >= fecha_filtro]
        
        total = len(df_filtered)
        ventas = len(df_filtered[df_filtered['result'].str.contains('Completed', case=False, na=False)]) if total > 0 else 0
        conversion = (ventas / total * 100) if total > 0 else 0

        c_metrics, c_chart = st.columns([1, 2])
        
        with c_metrics:
            tarjeta_progreso("Ventas", ventas, meta_ventas)
            st.write("")
            m1, m2 = st.columns(2)
            m1.metric("Notas", total)
            m2.metric("Conv.", f"{conversion:.0f}%")
        
        with c_chart:
            if total > 0:
                data_chart = df_filtered['result'].value_counts().reset_index()
                data_chart.columns = ['Resultado', 'Cantidad']
                chart = alt.Chart(data_chart).mark_bar(cornerRadius=4).encode(
                    x=alt.X('Cantidad', title=None),
                    y=alt.Y('Resultado', sort='-x', title=None),
                    color=alt.Color('Resultado', legend=None, scale=alt.Scale(scheme='blues')),
                    tooltip=['Resultado', 'Cantidad']
                ).properties(height=180)
                st.altair_chart(chart + chart.mark_text(dx=5, align='left').encode(text='Cantidad'), use_container_width=True)
            else:
                st.info(f"Sin actividad: {tag}")

    with tab_hoy: render_tab_content(hoy, 5, "Hoy") 
    with tab_semana: render_tab_content(inicio_semana, 25, "Semana") 
    with tab_mes: render_tab_content(inicio_mes_dt, 100, "Mes") 

    # D. NOTICIAS
    st.markdown("---")
    st.subheader("🔔 Noticias Corporativas")
    df_news = cargar_noticias_activas(supabase)
    if not df_news.empty:
        for _, row in df_news.iterrows():
            cat = str(row.get('category', 'INFO')).upper()
            title, msg, date = row.get('title', ''), row.get('message', ''), row.get('date', '')
            color_map = {'CRITICAL': ('#FFEBEE', '#D32F2F', '🚨'), 'WARNING': ('#FFF8E1', '#FFA000', '⚠️'), 'INFO': ('#E3F2FD', '#1976D2', 'ℹ️')}
            bg, border, icon = color_map.get(cat, color_map['INFO'])
            st.markdown(f"<div style='background-color: {bg}; border-left: 4px solid {border}; padding: 12px; border-radius: 4px; margin-bottom: 10px;'><div style='color: #666; font-size: 12px; margin-bottom: 4px;'>{date}</div><div style='font-weight: bold; color: #333; margin-bottom: 4px;'>{icon} {title}</div><div style='color: #444; font-size: 14px;'>{msg}</div></div>", unsafe_allow_html=True)
    else:
        st.info("✅ No hay noticias nuevas.")