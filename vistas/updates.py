import streamlit as st
import pandas as pd
from datetime import datetime

# --- FUNCIÓN DE CARGA SQL ---
@st.cache_data(ttl=600)
def cargar_noticias_supabase():
    try:
        conn = st.connection("supabase", type="sql")
        # Traemos activas ordenadas por fecha
        query = 'SELECT * FROM "Updates" WHERE active = TRUE ORDER BY date DESC'
        df = conn.query(query, ttl=600)
        return df
    except Exception as e:
        st.error(f"Error conectando a Updates: {e}")
        return pd.DataFrame()

def show():
    # --- ENCABEZADO Y ESTILO ---
    c_head, c_btn = st.columns([4, 1])
    with c_head:
        st.title("📢 Centro de Noticias")
        st.caption("Comunicados oficiales y actualizaciones operativas.")
    with c_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # --- CARGA DE DATOS ---
    df = cargar_noticias_supabase()

    if not df.empty:
        # --- BARRA DE HERRAMIENTAS (FILTROS) ---
        col_search, col_filter = st.columns([2, 1])
        
        with col_search:
            search_txt = st.text_input("Buscar en noticias:", placeholder="Ej: Feriado, Script...", label_visibility="collapsed")
        
        with col_filter:
            filtro_cat = st.selectbox(
                "Filtrar por:", 
                ["Todas", "🔴 Critical", "🟡 Warning", "🔵 Info"], 
                label_visibility="collapsed"
            )

        # --- LÓGICA DE FILTRADO (Python) ---
        # 1. Filtro de Texto
        if search_txt:
            mask = df['title'].str.contains(search_txt, case=False, na=False) | \
                   df['message'].str.contains(search_txt, case=False, na=False)
            df = df[mask]

        # 2. Filtro de Categoría
        if filtro_cat != "Todas":
            keyword = filtro_cat.split(" ")[1].upper() # Extrae "CRITICAL", "WARNING", etc.
            # Aseguramos que la columna category se compare bien
            df = df[df['category'].astype(str).str.upper() == keyword]

        st.markdown("<br>", unsafe_allow_html=True)

        # --- RENDERIZADO DE TARJETAS ---
        if not df.empty:
            for index, row in df.iterrows():
                # Preparar datos
                cat_raw = str(row.get('category', 'Info')).strip().upper()
                titulo = row.get('title', 'Sin Título')
                mensaje = row.get('message', '')
                fecha_raw = str(row.get('date', ''))

                # Formatear fecha bonita (Intenta parsear, si falla usa la raw)
                try:
                    fecha_obj = datetime.strptime(fecha_raw, '%Y-%m-%d')
                    fecha_fmt = fecha_obj.strftime('%b %d, %Y') # Ej: Dec 18, 2025
                except:
                    fecha_fmt = fecha_raw

                # Estilos Dinámicos (CSS en Python)
                if cat_raw == 'CRITICAL':
                    border_color = "#ff4444" # Rojo
                    bg_badge = "#ff4444"
                    icon = "🚨"
                elif cat_raw == 'WARNING':
                    border_color = "#ffbb33" # Amarillo
                    bg_badge = "#ffbb33"
                    icon = "⚠️"
                else: # Info
                    border_color = "#0099CC" # Azul
                    bg_badge = "#0099CC"
                    icon = "ℹ️"

                # HTML CARD (Diseño Profesional)
                st.markdown(
                    f"""
                    <div style="
                        background-color: white;
                        border-radius: 8px;
                        border-left: 5px solid {border_color};
                        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                        padding: 20px;
                        margin-bottom: 15px;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <span style="
                                background-color: {bg_badge}; 
                                color: white; 
                                padding: 4px 10px; 
                                border-radius: 15px; 
                                font-size: 12px; 
                                font-weight: bold;
                                text-transform: uppercase;
                            ">{icon} {cat_raw}</span>
                            <span style="color: #888; font-size: 14px;">📅 {fecha_fmt}</span>
                        </div>
                        <h3 style="margin: 0 0 10px 0; color: #333; font-size: 18px;">{titulo}</h3>
                        <div style="color: #555; font-size: 15px; line-height: 1.5;">
                            {mensaje}
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        else:
            st.info("No se encontraron noticias con esos filtros.")

    else:
        st.info("📭 No hay noticias publicadas en el sistema.")

if __name__ == "__main__":
    show()