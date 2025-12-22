import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# --- 1. CONEXIÓN (Patrón Seguro) ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["URL"]
        key = st.secrets["connections"]["supabase"]["KEY"]
        return create_client(url, key)
    except:
        return None

# --- 2. FUNCIÓN DE CARGA DATOS ---
def cargar_noticias_supabase():
    supabase = init_connection()
    if not supabase: return pd.DataFrame()
    
    try:
        # Usamos la API en lugar de SQL directo
        res = supabase.table("Updates").select("*")\
            .eq("active", True)\
            .order("date", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error conectando a Updates: {e}")
        return pd.DataFrame()

def show():
    # --- ENCABEZADO ---
    c_head, c_btn = st.columns([4, 1])
    with c_head:
        st.title("📢 Centro de Noticias")
        st.caption("Comunicados oficiales y actualizaciones operativas.")
    with c_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear() # Limpiamos caché si usáramos @st.cache_data
            st.rerun()

    st.markdown("---")

    # --- CARGA ---
    df = cargar_noticias_supabase()

    if not df.empty:
        # --- FILTROS ---
        col_search, col_filter = st.columns([2, 1])
        
        with col_search:
            search_txt = st.text_input("Buscar:", placeholder="Ej: Feriado...", label_visibility="collapsed")
        
        with col_filter:
            filtro_cat = st.selectbox("Filtrar:", ["Todas", "🔴 Critical", "🟡 Warning", "🔵 Info"], label_visibility="collapsed")

        # --- LÓGICA DE FILTRADO ---
        if search_txt:
            mask = df['title'].str.contains(search_txt, case=False, na=False) | \
                   df['message'].str.contains(search_txt, case=False, na=False)
            df = df[mask]

        if filtro_cat != "Todas":
            keyword = filtro_cat.split(" ")[1].upper() # "CRITICAL", "WARNING"...
            df = df[df['category'].astype(str).str.upper() == keyword]

        st.markdown("<br>", unsafe_allow_html=True)

        # --- RENDERIZADO ---
        if not df.empty:
            for index, row in df.iterrows():
                # Datos
                cat_raw = str(row.get('category', 'Info')).strip().upper()
                titulo = row.get('title', 'Aviso')
                mensaje = row.get('message', '')
                fecha_raw = str(row.get('date', ''))

                # Formato Fecha
                try:
                    fecha_fmt = datetime.strptime(fecha_raw, '%Y-%m-%d').strftime('%b %d, %Y')
                except:
                    fecha_fmt = fecha_raw

                # Estilos CSS
                estilos = {
                    'CRITICAL': {'border': '#ff4444', 'bg': '#ff4444', 'icon': '🚨'},
                    'WARNING':  {'border': '#ffbb33', 'bg': '#ffbb33', 'icon': '⚠️'},
                    'INFO':     {'border': '#0099CC', 'bg': '#0099CC', 'icon': 'ℹ️'}
                }
                est = estilos.get(cat_raw, estilos['INFO'])

                # Tarjeta HTML
                st.markdown(f"""
                <div style="
                    background-color: white;
                    border-radius: 8px;
                    border-left: 5px solid {est['border']};
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                    padding: 20px;
                    margin-bottom: 15px;
                ">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="background-color: {est['bg']}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                            {est['icon']} {cat_raw}
                        </span>
                        <span style="color: #999; font-size: 12px;">📅 {fecha_fmt}</span>
                    </div>
                    <h3 style="margin: 5px 0 10px 0; color: #333; font-size: 18px;">{titulo}</h3>
                    <div style="color: #555; font-size: 15px; line-height: 1.5;">{mensaje}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No se encontraron resultados con ese filtro.")
    else:
        st.info("📭 No hay noticias publicadas.")

if __name__ == "__main__":
    show()