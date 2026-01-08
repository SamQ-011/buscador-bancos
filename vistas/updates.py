import pandas as pd
import streamlit as st
from datetime import datetime
import services.updates_service as service

try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

# Iconos para el título
ICONS = {
    'CRITICAL': '🚨',
    'WARNING':  '⚠️',
    'INFO':     'ℹ️',
    'SUCCESS':  '🎉'
}

def _render_expander_item(conn, row: pd.Series, is_read: bool, username: str):
    """Renderiza la noticia usando SOLO componentes nativos de Streamlit."""
    
    # 1. Preparar Datos
    uid = row['id']
    cat = str(row.get('category', 'Info')).strip().upper()
    title = row.get('title', 'Aviso')
    msg = row.get('message', '')
    raw_date = row.get('date', '')

    try:
        if isinstance(raw_date, str):
            dt_obj = datetime.strptime(raw_date, '%Y-%m-%d')
        else:
            dt_obj = raw_date
        date_str = dt_obj.strftime('%b %d')
        # Es nuevo si tiene menos de 3 días
        is_new = (datetime.now() - pd.to_datetime(dt_obj)).days < 3
    except:
        date_str = str(raw_date)
        is_new = False

    icon = ICONS.get(cat, '📢')

    # --- DISEÑO UNIFICADO (EXPANDERS) ---
    
    if not is_read:
        # === MODO PENDIENTE ===
        # Título visualmente distintivo
        label = f"{icon} [{cat}] {title}  | 📅 {date_str}"
        if is_new: label += " ✨ NUEVO"
        
        # Si es Crítico, lo abrimos por defecto para llamar la atención
        start_open = True if cat == 'CRITICAL' else False
        
        with st.expander(label, expanded=start_open):
            # Usamos markdown para el cuerpo
            st.markdown(f"**{msg}**") 
            st.caption(f"Categoría: {cat}")
            st.write("---")
            
            # Botón para marcar como leído
            c_spacer, c_btn = st.columns([3, 1])
            with c_btn:
                btn_type = "primary" if cat == "CRITICAL" else "secondary"
                if st.button(f"Marcar como Leído", key=f"read_{uid}", type=btn_type, use_container_width=True):
                    if service.mark_as_read(conn, uid, username):
                        st.rerun()

    else:
        # === MODO LEÍDO ===
        # Título limpio y discreto
        label = f"✅ {date_str} | {title}"
        
        with st.expander(label, expanded=False):
            st.info("Ya has leído este mensaje.")
            st.markdown(msg)

def show():
    conn = get_db_connection()
    username = st.session_state.get("username", "Invitado")

    # Header
    c1, c2 = st.columns([5, 1])
    with c1:
        st.title("📢 Centro de Novedades")
    with c2:
        if st.button("🔄", help="Refrescar"):
            st.cache_data.clear()
            st.rerun()

    # 1. Obtener Datos
    df = service.fetch_updates(conn)
    if df.empty:
        st.info("No hay anuncios activos.")
        return

    # 2. Cruzar con Leídos
    read_ids = service.fetch_read_ids(conn, username)
    df['is_read'] = df['id'].isin(read_ids)

    # 3. Filtros
    c_search, c_filt = st.columns([3, 1])
    search = c_search.text_input("Buscar", placeholder="Filtrar...", label_visibility="collapsed")
    filtro = c_filt.selectbox("Ver", ["Todos", "Pendientes", "Leídos"], label_visibility="collapsed")

    if search:
        mask = df['title'].str.contains(search, case=False, na=False) | df['message'].str.contains(search, case=False, na=False)
        df = df[mask]
    
    if filtro == "Pendientes": df = df[df['is_read'] == False]
    elif filtro == "Leídos": df = df[df['is_read'] == True]

    # 4. Ordenar: Pendientes Críticos -> Pendientes Nuevos -> Leídos
    df = df.sort_values(by=['is_read', 'date'], ascending=[True, False])

    st.write("")

    # 5. Renderizar
    pendientes = df[df['is_read'] == False]
    leidos = df[df['is_read'] == True]

    if not pendientes.empty:
        st.caption("🔴 Pendientes")
        for _, row in pendientes.iterrows():
            _render_expander_item(conn, row, False, username)
        st.write("")

    if not leidos.empty:
        if not pendientes.empty: st.markdown("---")
        st.caption("📂 Historial Leído")
        for _, row in leidos.iterrows():
            _render_expander_item(conn, row, True, username)

if __name__ == "__main__":
    show()