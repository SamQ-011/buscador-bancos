# vistas/admin_panel.py
import time
import pytz
import io
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime

# --- IMPORTACIONES MODULARIZADAS ---
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

# Importamos el servicio
import services.admin_service as admin_service

# --- UI Components ---

def _render_dashboard(conn, df_raw: pd.DataFrame, total_bancos: int):
    """Tab 1: Visualización de métricas y exportación."""
    df_today = pd.DataFrame()
    today_et = datetime.now(pytz.timezone('US/Eastern')).date()

    if not df_raw.empty and 'created_at' in df_raw.columns:
        df_raw['created_at'] = pd.to_datetime(df_raw['created_at'], utc=True)
        df_raw['date_et'] = df_raw['created_at'].dt.tz_convert('US/Eastern').dt.date
        df_today = df_raw[df_raw['date_et'] == today_et].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏦 Base de Datos", total_bancos, delta="Bancos Activos")
    
    if not df_today.empty:
        total_calls = len(df_today)
        sales = len(df_today[df_today['result'].str.contains('Completed', case=False, na=False) & 
                             ~df_today['result'].str.contains('Not', case=False, na=False)])
        active_agents = df_today['agent'].nunique()
        conversion = (sales / total_calls * 100) if total_calls > 0 else 0
        
        c2.metric("📞 Llamadas", total_calls, delta="Hoy (ET)")
        c3.metric("🏆 Ventas", sales, delta=f"{conversion:.1f}% Conv.")
        c4.metric("👨‍💼 Staff Online", active_agents)
    else:
        for col in [c2, c3, c4]: col.metric("-", 0)

    st.markdown("---")

    # Gráficos
    if not df_today.empty:
        g1, g2 = st.columns([2, 1])
        with g1:
            st.subheader("Rendimiento por Agente (Hoy)")
            chart_data = df_today['agent'].value_counts().reset_index()
            chart_data.columns = ['Agente', 'Notas']
            chart = alt.Chart(chart_data).mark_bar(cornerRadius=4).encode(
                x=alt.X('Notas', title='Cantidad de Notas'),
                y=alt.Y('Agente', sort='-x', title=None),
                color=alt.value("#3b82f6")
            ).properties(height=320)
            st.altair_chart(chart, use_container_width=True)
            
        with g2:
            st.subheader("Resultados Globales")
            df_today['Status_Simple'] = df_today['result'].apply(
                lambda x: 'Completed' if 'Completed' in str(x) and 'Not' not in str(x) else 'Not Completed'
            )
            pie = alt.Chart(df_today).mark_arc(innerRadius=60).encode(
                theta=alt.Theta("count()", stack=True),
                color=alt.Color("Status_Simple", scale=alt.Scale(range=['#2ecc71', '#e74c3c']), legend=None),
                tooltip=["Status_Simple", "count()"]
            )
            st.altair_chart(pie, use_container_width=True)

    # MODULO DE EXPORTACIÓN
    with st.expander("📥 Auditoría y Exportación", expanded=False):
        c_d1, c_d2, c_filt = st.columns([1, 1, 2])
        start_date = c_d1.date_input("Desde", value=datetime.now().replace(day=1))
        end_date = c_d2.date_input("Hasta", value=datetime.now())
        
        agent_opts = ["TODOS (Global)"] + admin_service.fetch_agent_list(conn)
        target_agent = c_filt.selectbox("Filtrar Agente", agent_opts)
        
        if st.button("Generar Reporte Excel", type="primary"):
            try:
                # Llamada al servicio para obtener datos
                df_export = admin_service.fetch_logs_for_export(conn, start_date, end_date, target_agent)
                
                if not df_export.empty:
                    user_map = admin_service.fetch_user_map(conn)
                    output = io.BytesIO()
                    
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Resumen Centralizador
                        summary_data = []
                        agents = sorted(df_export['agent'].unique(), key=lambda x: x.lower())
                        
                        for idx, ag in enumerate(agents):
                            ag_data = df_export[df_export['agent'] == ag]
                            total = len(ag_data)
                            comp = len(ag_data[ag_data['result'].str.contains('Completed', case=False, na=False) & 
                                             ~ag_data['result'].str.contains('Not', case=False, na=False)])
                            not_comp = total - comp
                            real_name = user_map.get(ag, ag)

                            summary_data.append({
                                "N°": idx + 1, "AGENT": real_name, "TOTAL WC COMPLETED": comp, 
                                "TOTAL WC NOT COMPLETED": not_comp, "TOTAL CALLS": total
                            })
                        
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Centralizador', index=False)
                        
                        # Hojas individuales
                        for ag in agents:
                            df_ag = df_export[df_export['agent'] == ag].copy()
                            df_final = pd.DataFrame({
                                'N°': range(1, len(df_ag) + 1),
                                'CORDOBA ID': df_ag['cordoba_id'],
                                'CALL PROGRESS': df_ag['info_until'],
                                'REASON': df_ag['comments'],
                                'RESULT': df_ag['result'],
                                'LANGUAGE': df_ag['client_language']
                            })
                            df_final.to_excel(writer, sheet_name=str(ag)[:31], index=False)

                    st.download_button(
                        label="💾 Descargar Reporte Excel", 
                        data=output.getvalue(), 
                        file_name=f"Reporte_{start_date}_{end_date}.xlsx", 
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("No se encontraron datos para los filtros seleccionados.")
            except Exception as e:
                st.error(f"Error generando reporte: {e}")

def _render_log_editor(conn):
    st.subheader("🛠️ Quirófano de Registros")
    search_id = st.text_input("Buscar por ID Córdoba:").strip()
    if not search_id: return

    df_res = admin_service.fetch_log_by_cordoba_id(conn, search_id)
    if df_res.empty:
        st.warning("ID no encontrado.")
        return

    record = df_res.iloc[0].to_dict()
    with st.form("edit_log"):
        new_res = st.text_input("Resultado", record['result'])
        new_comm = st.text_area("Comentarios", record['comments'])
        if st.form_submit_button("Actualizar"):
            if admin_service.update_log_entry(conn, record['id'], new_res, new_comm):
                st.success("Actualizado.")
                st.rerun()

def _render_bank_manager(conn):
    """Tab 3: Gestión de Acreedores (Mejorado)."""
    c_add, c_edit = st.columns([1, 2], gap="large")
    
    # --- Columna Izquierda: Crear Nuevo ---
    with c_add:
        with st.container(border=True):
            st.markdown("🆕 **Nuevo Acreedor**")
            name = st.text_input("Nombre Entidad")
            abbrev = st.text_input("Abreviación (Alias)")
            
            if st.button("Agregar Banco", use_container_width=True, type="primary"):
                if name:
                    if admin_service.create_creditor(conn, name, abbrev):
                        st.success("Banco creado.")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.error("El nombre es obligatorio.")
    
    # --- Columna Derecha: Editar/Ver Lista Completa ---
    with c_edit:
        st.markdown("✏️ **Editar Acreedor Existente**")
        
        # Filtro de búsqueda (Opcional)
        q = st.text_input("Filtro rápido:", placeholder="Escribe para buscar o deja vacío para ver todos...", label_visibility="collapsed")
        
        # Lógica: Si q está vacío, busca "" (trae todo). Si tiene texto, filtra.
        search_term = q if q else ""
        
        try:
            df_banks = admin_service.search_creditors(conn, search_term)
        except Exception:
            df_banks = pd.DataFrame()
        
        if not df_banks.empty:
            banks = df_banks.to_dict('records')
            
            # Crear diccionario para el Selectbox: ID -> Texto a mostrar
            b_opts = {b['id']: f"{b['name']} ({b['abreviation']})" for b in banks}
            
            # Selectbox siempre visible con los resultados
            sel_id = st.selectbox(
                "Selecciona un banco:", 
                options=list(b_opts.keys()), 
                format_func=lambda x: b_opts[x]
            )
            
            # Obtener datos del banco seleccionado
            target = next((b for b in banks if b['id'] == sel_id), None)
            
            if target:
                st.divider()
                with st.container(border=True):
                    st.caption(f"Editando ID: {sel_id}")
                    with st.form("bank_edit_form"):
                        c_n, c_a = st.columns(2)
                        n_val = c_n.text_input("Nombre", value=target['name'])
                        a_val = c_a.text_input("Abrev.", value=target['abreviation'])
                        
                        st.markdown("") # Espacio
                        c_del, c_upd = st.columns([1, 2])
                        
                        with c_del:
                            if st.form_submit_button("🗑️ Eliminar", use_container_width=True):
                                if admin_service.delete_creditor(conn, sel_id):
                                    st.warning("Eliminado correctamente.")
                                    time.sleep(0.5)
                                    st.rerun()
                                    
                        with c_upd:
                            if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                                if admin_service.update_creditor(conn, sel_id, n_val, a_val):
                                    st.success("Cambios guardados.")
                                    time.sleep(0.5)
                                    st.rerun()
        else:
            if q:
                st.info(f"No se encontraron bancos con: '{q}'")
            else:
                st.info("No hay bancos registrados en la base de datos.")

def _render_updates_manager(conn):
    """Tab 4: Centro de Mensajes."""
    c1, c2 = st.columns([1, 2])
    
    with c1:
        with st.form("new_update"):
            st.markdown("**Publicar Noticia**")
            tit = st.text_input("Título")
            msg = st.text_area("Cuerpo del mensaje")
            cat = st.selectbox("Nivel", ["Info", "Warning", "Critical"])
            
            if st.form_submit_button("Publicar", use_container_width=True):
                if tit and msg:
                    if admin_service.create_update(conn, tit, msg, cat):
                        st.rerun()

    with c2:
        st.markdown("**Mensajes Activos**")
        df_upd = admin_service.fetch_active_updates(conn)
        updates = df_upd.to_dict('records')
        
        for u in updates:
            color = "#dc2626" if u['category'] == 'Critical' else "#d97706" if u['category'] == 'Warning' else "#2563eb"
            with st.container(border=True):
                st.markdown(f"<span style='color:{color}; font-weight:bold'>[{u['category']}] {u['title']}</span>", unsafe_allow_html=True)
                st.write(u['message'])
                if st.button("Archivar", key=f"arc_{u['id']}"):
                    if admin_service.archive_update(conn, u['id']):
                        st.rerun()

def _render_user_manager(conn):
    """Tab 5: Gestión de Usuarios."""
    c1, c2 = st.columns([1, 2])
    
    with c1:
        with st.form("create_user"):
            st.markdown("**Alta de Usuario**")
            u_user = st.text_input("Username (Login)")
            u_name = st.text_input("Nombre Completo")
            u_pass = st.text_input("Contraseña", type="password")
            u_role = st.selectbox("Rol", ["Agent", "Admin"])
            
            if st.form_submit_button("Crear Usuario", use_container_width=True):
                if u_user and u_pass:
                    if admin_service.create_user(conn, u_user, u_name, u_pass, u_role):
                        st.success(f"Usuario {u_user} creado.")
                        time.sleep(1); st.rerun()

    with c2:
        df_users = admin_service.fetch_all_users(conn)
        users = df_users.to_dict('records')
        if not users: return
        
        st.dataframe(pd.DataFrame(users)[['username', 'name', 'role', 'active']], use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown("**Edición de Usuario**")
        
        u_map = {u['id']: f"{u['username']} ({u['name']})" for u in users}
        sel_uid = st.selectbox("Seleccionar usuario:", list(u_map.keys()), format_func=lambda x: u_map[x])
        target = next(u for u in users if u['id'] == sel_uid)
        
        with st.form("edit_user_form"):
            col_a, col_b = st.columns(2)
            new_name = col_a.text_input("Nombre", target['name'])
            new_role = col_b.selectbox("Rol", ["Agent", "Admin"], index=0 if target['role'] == "Agent" else 1)
            col_c, col_d = st.columns(2)
            is_active = col_c.checkbox("Cuenta Activa", target['active'])
            new_pass = col_d.text_input("Reset Password", type="password", help="Dejar vacío para mantener")
            
            if st.form_submit_button("Actualizar Perfil"):
                if admin_service.update_user_profile(conn, sel_uid, new_name, new_role, is_active, new_pass):
                    st.success("Perfil actualizado.")
                    time.sleep(1); st.rerun()

# --- Main View ---

def show():
    st.title("🎛️ Torre de Control")
    conn = get_db_connection()
    if not conn: return

    # Definimos las pestañas
    tabs = st.tabs(["📊 Dashboard", "🛠️ Editor Logs", "🏦 Bancos", "🔔 Noticias", "👥 Usuarios"])
    
    # 1. Dashboard
    with tabs[0]:
        total_bancos, df_logs = admin_service.fetch_global_kpis(conn)
        _render_dashboard(conn, df_logs, total_bancos)
    
    # 2. Editor (Quirófano)
    with tabs[1]: 
        _render_log_editor(conn)
    
    # 3. Bancos
    with tabs[2]:
        _render_bank_manager(conn)

    # 4. Noticias
    with tabs[3]:
        _render_updates_manager(conn)

    # 5. Usuarios
    with tabs[4]:
        _render_user_manager(conn)

if __name__ == "__main__":
    show()
