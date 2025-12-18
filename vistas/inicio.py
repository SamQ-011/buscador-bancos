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

# --- 2. FUNCIONES DE FECHA ---
def get_fechas_clave():
    """Calcula rangos de fechas en Eastern Time"""
    zona_et = pytz.timezone('US/Eastern')
    ahora = datetime.now(zona_et)
    hoy = ahora.date()
    
    # Inicio de Semana (Lunes)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    # Inicio de Mes
    inicio_mes = hoy.replace(day=1)
    
    return zona_et, ahora, hoy, inicio_semana, inicio_mes

def sumar_dias_habiles(fecha_inicio, dias_a_sumar):
    dias_agregados = 0
    fecha_actual = fecha_inicio
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

def cargar_logs_del_mes(nombre_agente, fecha_inicio_mes_iso):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table("Logs").select("*")\
            .eq("agent", nombre_agente)\
            .gte("created_at", fecha_inicio_mes_iso)\
            .order("created_at", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

# --- 4. COMPONENTE TARJETA PROGRESO (MÉTRICAS) ---
def tarjeta_progreso(titulo, valor, meta):
    progreso = min(valor / meta, 1.0) if meta > 0 else 0
    porcentaje = int(progreso * 100)
    
    color_texto = "blue"
    if porcentaje >= 100: color_texto = "#00C851"
    elif porcentaje >= 50: color_texto = "#ffbb33"
    else: color_texto = "#ff4444"
    
    with st.container(border=True):
        st.caption(titulo)
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"<h2 style='margin:0; padding:0;'>{valor} <span style='font-size: 14px; color:gray;'>/ {meta}</span></h2>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<h3 style='text-align:right; color:{color_texto}; margin:0;'>{porcentaje}%</h3>", unsafe_allow_html=True)
        st.progress(progreso)

# --- 5. VISTA PRINCIPAL ---
def show():
    # A. INIT TIEMPO
    zona_et, ahora_et, hoy, inicio_semana, inicio_mes = get_fechas_clave()

    # B. HEADER
    nombre = st.session_state.get("real_name", "Agente")
    h1, h2 = st.columns([3, 1])
    with h1:
        st.title(f"🚀 Dashboard: {nombre}")
    with h2:
        st.markdown(f"<div style='text-align: right; color: gray; padding-top: 20px;'>{ahora_et.strftime('%I:%M %p ET')}</div>", unsafe_allow_html=True)
    
    st.markdown("---")

    # C. SECCIÓN 1: FECHAS DE PAGO (DISEÑO LIMPIO)
    st.subheader("📅 Fechas de Pago Calculadas")
    
    f_std = sumar_dias_habiles(ahora_et, 2) 
    f_ca = sumar_dias_habiles(ahora_et, 4)  
    f_max = ahora_et + timedelta(days=35)

    col_d1, col_d2, col_d3 = st.columns(3)

    # Estilo CSS para fecha grande sin márgenes molestos
    estilo_fecha = "margin: 0; font-size: 1.8rem; font-weight: 600; color: #31333F;"
    estilo_titulo = "margin: 0; color: gray; font-size: 0.9rem;"

    with col_d1:
        with st.container(border=True):
            st.markdown(f"<p style='{estilo_titulo}'>Standard (3 Days)</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{estilo_fecha}'>{f_std.strftime('%b %d')}</p>", unsafe_allow_html=True)
    
    with col_d2:
        with st.container(border=True):
            st.markdown(f"<p style='{estilo_titulo}'>California (5 Days)</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{estilo_fecha}'>{f_ca.strftime('%b %d')}</p>", unsafe_allow_html=True)

    with col_d3:
        with st.container(border=True):
            st.markdown(f"<p style='{estilo_titulo}'>⛔ Max Date</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='{estilo_fecha}'>{f_max.strftime('%m/%d/%Y')}</p>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # D. SECCIÓN 2: METRICAS POR PESTAÑA
    inicio_mes_str = inicio_mes.strftime("%Y-%m-%dT00:00:00")
    usuario_busqueda = st.session_state.get("real_name", st.session_state.get("username"))
    df_raw = cargar_logs_del_mes(usuario_busqueda, inicio_mes_str)
    
    if not df_raw.empty and 'created_at' in df_raw.columns:
        df_raw['created_at'] = pd.to_datetime(df_raw['created_at'])
        try:
            df_raw['fecha_et'] = df_raw['created_at'].dt.tz_convert(zona_et)
        except TypeError:
            df_raw['fecha_et'] = df_raw['created_at'].dt.tz_localize('UTC').dt.tz_convert(zona_et)
        df_raw['fecha_date'] = df_raw['fecha_et'].dt.date

    st.subheader("📊 Rendimiento")
    tab_hoy, tab_semana, tab_mes = st.tabs(["📅 Hoy", "🗓️ Esta Semana", "🏆 Este Mes"])

    def render_stats(dataframe, fecha_filtro, meta, label_grafico):
        if dataframe.empty:
            df_f = pd.DataFrame(columns=['result', 'fecha_date'])
        else:
            df_f = dataframe[dataframe['fecha_date'] >= fecha_filtro]
        
        total = len(df_f)
        ventas = len(df_f[df_f['result'].str.contains('Completed', case=False, na=False)]) if total > 0 else 0
        conversion = (ventas / total * 100) if total > 0 else 0.0

        c_izq, c_der = st.columns([1, 2])
        
        with c_izq:
            tarjeta_progreso("Ventas Acumuladas", ventas, meta)
            st.markdown("<br>", unsafe_allow_html=True)
            mm1, mm2 = st.columns(2)
            mm1.metric("Llamadas", total)
            mm2.metric("Efec.", f"{conversion:.0f}%")

        with c_der:
            if total > 0:
                chart_data = df_f['result'].value_counts().reset_index()
                chart_data.columns = ['Resultado', 'Cantidad']
                
                grafico = alt.Chart(chart_data).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Cantidad', title=None, axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y('Resultado', sort='-x', title=None),
                    color=alt.Color('Resultado', legend=None, scale=alt.Scale(scheme='blues')),
                    tooltip=['Resultado', 'Cantidad']
                ).properties(height=200)
                
                text = grafico.mark_text(dx=3, align='left').encode(text='Cantidad')
                st.altair_chart(grafico + text, use_container_width=True)
            else:
                st.info(f"No hay actividad registrada: {label_grafico}", icon="💤")

    with tab_hoy:
        render_stats(df_raw, hoy, 10, "Hoy")
    with tab_semana:
        render_stats(df_raw, inicio_semana, 50, "Esta Semana")
    with tab_mes:
        render_stats(df_raw, inicio_mes, 220, "Este Mes")

    # E. SECCIÓN 3: NOTICIAS
    st.markdown("---")
    st.subheader("📢 Updates")
    
    df_news = cargar_noticias_activas()
    if not df_news.empty:
        for index, row in df_news.iterrows():
            cat = str(row.get('category', 'INFO')).strip().upper()
            titulo = row.get('title', 'Update')
            mensaje = row.get('message', '')
            fecha = row.get('date', '')

            colors = {
                'CRITICAL': ("🔴", "rgba(255, 75, 75, 0.1)"),
                'WARNING': ("🟡", "rgba(255, 235, 59, 0.1)"),
                'INFO': ("🔵", "rgba(33, 150, 243, 0.05)")
            }
            icon, bg = colors.get(cat, colors['INFO'])

            st.markdown(
                f"""
                <div style="background-color: {bg}; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid gray;">
                    <small style="color:gray;">{fecha}</small><br>
                    <strong>{icon} {titulo}</strong><br>
                    <span style="color: #333;">{mensaje}</span>
                </div>
                """, unsafe_allow_html=True
            )
    else:
        st.caption("No hay anuncios activos.")

if __name__ == "__main__":
    show()