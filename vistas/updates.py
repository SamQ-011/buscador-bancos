import streamlit as st
import pandas as pd

# --- FUNCIÓN DE CARGA SQL (Supabase) ---
def cargar_noticias_supabase():
    try:
        conn = st.connection("supabase", type="sql")
        
        # OJO: Usamos comillas dobles en "Updates" y "Active" 
        # porque Supabase respeta las mayúsculas de tu CSV original.
        # Buscamos solo las noticias donde Active es TRUE
        query = 'SELECT * FROM "Updates" WHERE active = TRUE'
        
        # Ejecutamos la consulta (ttl=600 guarda en caché 10 mins)
        df = conn.query(query, ttl=600)
        return df
    except Exception as e:
        # Si la tabla no existe o hay error de columnas
        st.error(f"Error conectando a la tabla Updates: {e}")
        return pd.DataFrame()

def show():
    st.title("🔔 Central de Noticias")
    st.caption("Comunicados oficiales del equipo.")
    st.markdown("---")

    # 1. Cargar datos desde Supabase
    df = cargar_noticias_supabase()

    if not df.empty:
        # 2. ORDENAMIENTO POR FECHA
        # Intentamos convertir la columna 'Date' a formato fecha para ordenar bien
        # Si falla (porque está en texto raro), no pasa nada, se muestra como venga.
        if 'Date' in df.columns:
            try:
                df['fecha_dt'] = pd.to_datetime(df['Date'], dayfirst=False, errors='coerce')
                df = df.sort_values(by='fecha_dt', ascending=False)
            except:
                pass 

        # 3. RENDERIZADO DE TARJETAS
        for index, row in df.iterrows():
            # Usamos .get() para evitar errores si falta alguna columna
            tipo = str(row.get('Type', 'Info')).strip().lower()
            titulo = row.get('title', 'Sin Título')
            mensaje = row.get('message', '')
            fecha = row.get('date', '')

            # Diseño del Encabezado
            header_texto = f"**{fecha}** | {titulo}"

            # Lógica de Colores (Alertas visuales)
            if tipo in ['alerta', 'alert', 'error', 'urgent', 'critical']:
                st.error(f"🚨 {header_texto}\n\n{mensaje}")
            
            elif tipo in ['exito', 'success', 'done', 'new', 'nuevo']:
                st.success(f"🎉 {header_texto}\n\n{mensaje}")
            
            else: # Info, General
                st.info(f"ℹ️ {header_texto}\n\n{mensaje}")
    
    else:
        st.info("📭 No hay noticias activas por el momento.")

    # Botón discreto para recargar si alguien subió algo nuevo
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Actualizar Lista", type="secondary"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    show()