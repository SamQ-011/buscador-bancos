import pandas as pd
import streamlit as st
from datetime import datetime
import services.updates_service as service # Importamos tu servicio

# Configuración Visual (Themes)
CATEGORY_THEMES = {
    'CRITICAL': {'border': '#DC2626', 'bg': '#DC2626', 'icon': '🚨'},
    'WARNING':  {'border': '#D97706', 'bg': '#D97706', 'icon': '⚠️'},
    'INFO':     {'border': '#2563EB', 'bg': '#2563EB', 'icon': 'ℹ️'}
}

def _render_update_card(row: pd.Series):
    """Genera HTML para una tarjeta individual."""
    cat = str(row.get('category', 'Info')).strip().upper()
    title = row.get('title', 'Aviso del Sistema')
    msg = row.get('message', '')
    raw_date = row.get('date', '')

    try:
        if isinstance(raw_date, str):
            date_str = datetime.strptime(raw_date, '%Y-%m-%d').strftime('%b %d, %Y')
        else:
            date_str = raw_date.strftime('%b %d, %Y')
    except (ValueError, AttributeError):
        date_str = str(raw_date)

    theme = CATEGORY_THEMES.get(cat, CATEGORY_THEMES['INFO'])

    st.markdown(f"""
    <div style="
        background-color: #FFFFFF; border-radius: 6px;
        border-left: 4px solid {theme['border']};
        box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1);
        padding: 1.25rem; margin-bottom: 1rem;
        font-family: 'Segoe UI', sans-serif;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <span style="background-color: {theme['bg']}; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700;">
                {theme['icon']} {cat}
            </span>
            <span style="color: #6B7280; font-size: 0.85rem;">{date_str}</span>
        </div>
        <h3 style="margin: 0 0 0.5rem 0; color: #111827; font-size: 1.1rem; font-weight: 600;">{title}</h3>
        <div style="color: #374151; font-size: 0.95rem; line-height: 1.5; white-space: pre-wrap;">{msg}</div>
    </div>
    """, unsafe_allow_html=True)

def show():
    # Header
    c_head, c_act = st.columns([4, 1])
    with c_head:
        st.title("📢 Centro de Novedades")
        st.caption("Comunicaciones oficiales y actualizaciones operativas.")
    with c_act:
        st.write("") 
        if st.button("🔄 Refrescar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # 1. Llamada al Servicio
    df = service.fetch_updates()

    if df.empty:
        st.info("No hay anuncios activos en este momento.")
        return

    # Filtros
    c_search, c_filter = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("Buscar...", placeholder="Palabras clave...", label_visibility="collapsed")
    with c_filter:
        cat_filter = st.selectbox("Tipo", ["Todos", "🔴 Critical", "🟡 Warning", "🔵 Info"], label_visibility="collapsed")

    # Lógica de Filtrado (en Vista porque es interacción UI)
    if search_query:
        mask = df['title'].str.contains(search_query, case=False, na=False) | \
               df['message'].str.contains(search_query, case=False, na=False)
        df = df[mask]

    if cat_filter != "Todos":
        target_cat = cat_filter.split(" ")[1].strip()
        df = df[df['category'].str.upper() == target_cat]

    st.write("")

    # Renderizado
    if not df.empty:
        for _, row in df.iterrows():
            _render_update_card(row)
    else:
        st.warning("No se encontraron actualizaciones con esos criterios.")

if __name__ == "__main__":
    show()