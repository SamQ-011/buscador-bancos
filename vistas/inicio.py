import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from supabase import create_client

# --- 1. CONEXIÓN A SUPABASE (Igual que Admin Panel) ---
@st.cache_resource
def init_connection():
    try:
        # Intento 1: Buscar dentro de [connections.supabase]
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            url = st.secrets["connections"]["supabase"]["URL"]
            key = st.secrets["connections"]["supabase"]["KEY"]
        # Intento 2: Buscar en la raíz
        else:
            url = st.secrets["URL"]
            key = st.secrets["KEY"]
            
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_connection()

# --- 2. FUNCIONES DE LÓGICA (Fechas) ---
def sumar_dias_habiles(fecha_inicio, dias_a_sumar):
    dias_agregados = 0
    fecha_actual = fecha_inicio
    if dias_a_sumar <= 0: return fecha_actual
    
    while dias_agregados < dias_a_sumar:
        fecha_actual += timedelta(days=1)
        if fecha_actual.weekday() < 5: 
            dias_agregados += 1
    return fecha_actual

# --- 3. CARGA DE DATOS (Backend) ---
def cargar_noticias_activas():
    """Descarga las alertas activas publicadas por el Admin"""
    if not supabase: return pd.DataFrame()
    try:
        # Tabla "Updates", activas=True, ordenadas por fecha
        res = supabase.table("Updates").select("*")\
            .eq("active", True)\
            .order("date", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

def cargar_metricas_usuario(username):
    """Descarga los logs del agente actual"""
    if not supabase: return pd.DataFrame()
    try:
        # Tabla "Logs", filtramos por usuario y traemos los últimos 100
        res = supabase.table("Logs").select("*")\
            .eq("agent", username)\
            .order("created_at", desc=True)\
            .limit(100)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

# --- 4. VISTA PRINCIPAL ---
def show():
    # A. SECCIÓN DE ALERTAS (Lo primero que ven)
    df_news = cargar_noticias_activas()
    
    if not df_news.empty:
        for index, row in df_news.iterrows():
            # Limpieza de datos
            cat = str(row.get('category', 'INFO')).strip().upper()
            titulo = row.get('title', 'Aviso')
            mensaje = row.get('message', '')
            
            # Renderizado según prioridad
            if cat == 'CRITICAL':
                st.error(f"🚨 **{titulo}**: {mensaje}", icon="🚨")
            elif cat == 'WARNING':
                st.warning(f"⚠️ **{titulo}**: {mensaje}", icon="⚠️")
            else:
                st.info(f"ℹ️ **{titulo}**: {mensaje}", icon="ℹ️")
        
        st.write("") # Espacio visual

    # B. ENCABEZADO
    nombre = st.session_state.real_name
    st.title(f"👋 Hola, {nombre}")
    st.caption("Resumen de actividad y herramientas.")
    st.markdown("---")

    # C. FECHAS CLAVE
    hoy = datetime.now()
    f_min_std = sumar_dias_habiles(hoy, 2) 
    f_min_ca = sumar_dias_habiles(hoy, 4)  
    f_max = hoy + timedelta(days=35)        

    c_d1, c_d2, c_d3 = st.columns(3)
    c_d1.metric("💰 1st Payment Date", f_min_std.strftime('%d/%m/%Y'), "Min 3 días hábiles")
    c_d2.metric("💰 1st Pay (CA Clients)", f_min_ca.strftime('%d/%m/%Y'), "Min 5 días hábiles")
    c_d3.metric("⛔ Fecha Límite", f_max.strftime('%d/%m/%Y'), "Max 35 días", delta_color="inverse")

    # D. KPIS Y RENDIMIENTO
    st.subheader("📊 Tu Rendimiento Hoy")
    
    # Fallback por si username no está en session_state (usa real_name)
    usuario_actual = st.session_state.get("username", st.session_state.real_name)
    df_logs = cargar_metricas_usuario(usuario_actual)

    if not df_logs.empty:
        # Procesamiento de fechas
        if 'created_at' in df_logs.columns:
            df_logs['created_at'] = pd.to_datetime(df_logs['created_at'])
            # Filtrar HOY (Manejo de Timezone seguro)
            try:
                hoy_fecha = pd.Timestamp.now(tz=df_logs['created_at'].dt.tz).date()
                df_hoy = df_logs[df_logs['created_at'].dt.date == hoy_fecha]
            except:
                # Si falla la zona horaria, usamos fecha string simple
                hoy_str = datetime.now().strftime('%Y-%m-%d')
                df_hoy = df_logs[df_logs['created_at'].astype(str).str.startswith(hoy_str)]
        else:
            df_hoy = df_logs

        # Cálculos
        total_hoy = len(df_hoy)
        ventas_hoy = len(df_hoy[df_hoy['result'].str.contains('Completed', case=False, na=False)])
        conversion = (ventas_hoy / total_hoy * 100) if total_hoy > 0 else 0

        # Tarjetas de KPI
        k1, k2, k3 = st.columns(3)
        k1.metric("🏆 Completed Hoy", ventas_hoy, delta="Objetivo: 10")
        k2.metric("📞 Llamadas Totales", total_hoy)
        k3.metric("📈 Efectividad", f"{conversion:.1f}%")

        # Gráfico
        if total_hoy > 0:
            st.markdown("##### 📅 Distribución de Resultados")
            chart_data = df_hoy['result'].value_counts().reset_index()
            chart_data.columns = ['Resultado', 'Cantidad']
            
            grafico = alt.Chart(chart_data).mark_bar(
                cornerRadius=5,
                color='#0F52BA' # Azul corporativo
            ).encode(
                x=alt.X('Cantidad', axis=None),
                y=alt.Y('Resultado', sort='-x', title=None),
                tooltip=['Resultado', 'Cantidad']
            ).properties(height=200)
            
            text = grafico.mark_text(dx=3, align='left').encode(text='Cantidad')
            
            st.altair_chart(grafico + text, use_container_width=True)
    else:
        st.info("👋 Aún no tienes actividad registrada. ¡Ve al Generador de Notas!")

if __name__ == "__main__":
    show()
