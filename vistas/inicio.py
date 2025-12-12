import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt 

# --- 1. FUNCIONES UTILITARIAS (Fechas) ---
def sumar_dias_habiles(fecha_inicio, dias_a_sumar):
    dias_agregados = 0
    fecha_actual = fecha_inicio
    if dias_a_sumar <= 0: return fecha_actual
    
    while dias_agregados < dias_a_sumar:
        fecha_actual += timedelta(days=1)
        if fecha_actual.weekday() < 5: 
            dias_agregados += 1
    return fecha_actual

# --- 2. CARGA DE DATOS (Supabase) ---
def cargar_metricas_usuario(username):
    try:
        conn = st.connection("supabase", type="sql")
        
        # OJO: Usamos "Logs" con comillas porque tu tabla empieza con Mayúscula
        query = """
            SELECT * FROM "Logs" 
            WHERE agent = :user 
            ORDER BY created_at DESC 
            LIMIT 100
        """
        # ttl=60 significa que actualiza los datos cada minuto
        df = conn.query(query, params={"user": username}, ttl=60) 
        return df
    except Exception as e:
        # Si falla (ej: tabla vacía), devolvemos dataframe vacío y mostramos error en consola
        print(f"Error Logs: {e}") 
        return pd.DataFrame()

def show():
    # --- ENCABEZADO ---
    nombre = st.session_state.real_name
    st.title(f"👋 Hola, {nombre}")
    st.caption("Resumen de actividad y herramientas.")
    st.markdown("---")

    # ========================================================
    # SECCIÓN 1: FECHAS CLAVE (Siempre visible)
    # ========================================================
    hoy = datetime.now()
    f_min_std = sumar_dias_habiles(hoy, 2) 
    f_min_ca = sumar_dias_habiles(hoy, 4)  
    f_max = hoy + timedelta(days=35)       

    # Usamos st.metric en lugar de st.info/success/warning
    # Se verán como tarjetas gracias al CSS de main.py
    col_dates_1, col_dates_2, col_dates_3 = st.columns(3)
    
    with col_dates_1:
         st.metric(
            label="💰 1st Payment Date", 
            value=f_min_std.strftime('%d/%m/%Y'), 
            delta=f"At least three business days"
        )
        
    with col_dates_2:
        st.metric(
            label="💰 1st Payment Date, CA clients", 
            value=f_min_ca.strftime('%d/%m/%Y'), 
            delta=f"At least five business days"
        )
        
    with col_dates_3:
        st.metric(
            label="⛔ Fecha Límite", 
            value=f_max.strftime('%d/%m/%Y'), 
            delta="Máx 35 days", 
            delta_color="inverse"
        )

    # ========================================================
    # SECCIÓN 2: TUS MÉTRICAS (KPIs)
    # ========================================================
    st.subheader("📊 Tu Rendimiento Hoy")
    
    usuario_actual = st.session_state.username
    df_logs = cargar_metricas_usuario(usuario_actual)

    if not df_logs.empty:
        # Aseguramos formato de fecha
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at'])
        
        # Filtrar solo registros de HOY
        try:
            hoy_fecha = pd.Timestamp.now(tz=df_logs['created_at'].dt.tz).date()
            df_hoy = df_logs[df_logs['created_at'].dt.date == hoy_fecha]
        except:
            # Si hay lío con zonas horarias, usamos fecha simple
            df_hoy = df_logs # Fallback simple

        # Métricas
        total_hoy = len(df_hoy)
        # Filtramos buscando "Completed" en la columna result
        ventas_hoy = len(df_hoy[df_hoy['result'].str.contains('Completed', case=False, na=False)])
        
        # Tasa de Cierre
        conversion = (ventas_hoy / total_hoy * 100) if total_hoy > 0 else 0

        # Tarjetas
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("🏆 Completed Hoy", ventas_hoy, delta="Objetivo: 10")
        kpi2.metric("📞 Llamadas Totales", total_hoy)
        kpi3.metric("📈 Efectividad", f"{conversion:.1f}%")

        # Gráfico simple
        if total_hoy > 0:
            st.markdown("##### 📅 Distribución de Resultados")
            chart_data = df_hoy['result'].value_counts().reset_index()
            chart_data.columns = ['Resultado', 'Cantidad']
            
            grafico = alt.Chart(chart_data).mark_bar(
                cornerRadiusTopLeft=5,     # Bordes redondeados arriba
                cornerRadiusTopRight=5,
                color='#0F52BA'            # <--- TU AZUL CORPORATIVO (No colores random)
            ).encode(
                x=alt.X('Cantidad', axis=None), # Quitamos eje X para limpieza
                y=alt.Y('Resultado', sort='-x', title=None), # Quitamos título eje Y
                tooltip=['Resultado', 'Cantidad']
            ).properties(height=200)
            
            # Añadimos texto sobre las barras para que se vea moderno
            text = grafico.mark_text(
                align='left',
                baseline='middle',
                dx=3  # Mueve el texto un poco a la derecha
            ).encode(
                text='Cantidad'
            )
            
            st.altair_chart(grafico + text, use_container_width=True)

    else:
        st.info("👋 Aún no tienes actividad registrada hoy. ¡Genera tu primera nota!")

if __name__ == "__main__":
    show()