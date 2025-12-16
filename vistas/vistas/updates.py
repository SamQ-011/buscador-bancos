import streamlit as st
import pandas as pd

# --- FUNCIÓN DE CARGA SQL (Supabase) ---
def cargar_noticias_supabase():
    try:
        conn = st.connection("supabase", type="sql")
        
        # OJO: Usamos comillas dobles en "Updates" y ordenamos por la columna "date"
        # Traemos SOLO las activas (Active = TRUE)
        query = 'SELECT * FROM "Updates" WHERE active = TRUE ORDER BY date DESC'
        
        # Ejecutamos la consulta (ttl=600 guarda en caché 10 mins)
        df = conn.query(query, ttl=600)
        return df
    except Exception as e:
        # Si la tabla no existe o hay error
        st.error(f"Error conectando a la tabla Updates: {e}")
        return pd.DataFrame()

def show():
    st.title("🗞️ Tablón de Anuncios")
    st.caption("Historial completo de comunicados y actualizaciones operativas.")
    st.markdown("---")

    # 1. Cargar datos desde Supabase
    df = cargar_noticias_supabase()

    if not df.empty:
        # 2. Renderizado de Noticias
        for index, row in df.iterrows():
            # Extraemos datos usando los nombres NUEVOS de tu base de datos
            # category, title, message, date
            cat_raw = str(row.get('category', 'Info')).strip().upper()
            titulo = row.get('title', 'Sin Título')
            mensaje = row.get('message', '')
            fecha = row.get('date', '')

            # Diseño del Encabezado
            header_texto = f"**{fecha}** | {titulo}"

            # 3. Lógica de Colores según tu nueva categoría (Critical, Warning, Info)
            if cat_raw == 'CRITICAL':
                st.error(f"🚨 {header_texto}\n\n{mensaje}", icon="🚨")
            
            elif cat_raw == 'WARNING':
                st.warning(f"⚠️ {header_texto}\n\n{mensaje}", icon="⚠️")
            
            else: # Info
                st.info(f"ℹ️ {header_texto}\n\n{mensaje}", icon="ℹ️")
    
    else:
        st.info("📭 No hay noticias en el tablón por el momento.")

    # Botón para recargar manual
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refrescar Tablón", type="secondary"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    show()