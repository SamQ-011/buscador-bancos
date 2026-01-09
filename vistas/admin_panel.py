import time
import pytz
import io
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime

# --- IMPORTACIONES ---
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

import services.admin_service as admin_service

# ==============================================================================
# MOTOR DE REPORTES MODULAR (EXCEL GENERATOR)
# ==============================================================================
def _generate_excel_file(df_export, user_map, report_type):
    """
    Genera reportes específicos con corrección de zonas horarias y formatos.
    """
    output = io.BytesIO()
    
    # --- CORRECCIÓN CRÍTICA DE FECHAS (TIMEZONE FIX) ---
    if 'created_at' in df_export.columns:
        df_export['created_at'] = pd.to_datetime(df_export['created_at'])
        if df_export['created_at'].dt.tz is not None:
            df_export['created_at'] = df_export['created_at'].dt.tz_localize(None)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # --- ESTILOS ---
        header_fmt = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#1F4E78', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'top', 'text_wrap': True}) 
        cell_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        pct_fmt = workbook.add_format({'num_format': '0.0%', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        int_fmt = workbook.add_format({'num_format': '0', 'border': 1, 'align': 'center', 'valign': 'vcenter'}) 
        
        success_fmt = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'border': 1, 'num_format': '0.0%'})
        alert_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1, 'num_format': '0.0%'})

        agents = sorted(df_export['agent'].unique(), key=lambda x: str(x).lower())

        # =========================================================
        # TIPO 1: ESTRATÉGICO (KPIs & Negocio)
        # =========================================================
        if report_type == "Estratégico (KPIs & Negocio)":
            
            # --- HOJA: DASHBOARD GLOBAL ---
            summary_data = []
            for ag in agents:
                ag_data = df_export[df_export['agent'] == ag]
                total = len(ag_data)
                comp = len(ag_data[ag_data['result'].str.contains('Completed', case=False, na=False) & 
                                 ~ag_data['result'].str.contains('Not', case=False, na=False)])
                conversion = comp / total if total > 0 else 0
                
                summary_data.append({
                    "AGENTE": user_map.get(ag, ag), "TOTAL": total, 
                    "VENTAS": comp, "CONVERSIÓN": conversion
                })
            
            df_sum = pd.DataFrame(summary_data).sort_values("CONVERSIÓN", ascending=False)
            df_sum.to_excel(writer, sheet_name='KPI Global', index=False)
            
            ws = writer.sheets['KPI Global']
            ws.set_tab_color('#1F4E78')
            for col_num, value in enumerate(df_sum.columns.values):
                ws.write(0, col_num, value, header_fmt)

            ws.set_column('A:A', 25, cell_fmt)
            ws.set_column('B:C', 15, cell_center)
            ws.set_column('D:D', 15, pct_fmt)
            ws.conditional_format(f'D2:D{len(df_sum)+1}', {'type': 'cell', 'criteria': '>=', 'value': 0.10, 'format': success_fmt})
            ws.conditional_format(f'D2:D{len(df_sum)+1}', {'type': 'cell', 'criteria': '<', 'value': 0.05, 'format': alert_fmt})

            # --- HOJA: CALIDAD AFILIADOS ---
            if 'affiliate' in df_export.columns:
                df_export['Es_Venta'] = df_export['result'].apply(lambda x: 1 if 'Completed' in str(x) and 'Not' not in str(x) else 0)
                pv_aff = df_export.pivot_table(index='affiliate', values=['id', 'Es_Venta'], aggfunc={'id':'count', 'Es_Venta':'sum'})
                pv_aff = pv_aff.rename(columns={'id': 'TOTAL LEADS', 'Es_Venta': 'VENTAS'})
                pv_aff = pv_aff[['VENTAS', 'TOTAL LEADS']]
                pv_aff['CONVERSIÓN'] = pv_aff['VENTAS'] / pv_aff['TOTAL LEADS']
                pv_aff = pv_aff.sort_values('CONVERSIÓN', ascending=False).reset_index()
                
                pv_aff.to_excel(writer, sheet_name='Calidad Tráfico', index=False)
                ws_aff = writer.sheets['Calidad Tráfico']
                ws_aff.set_tab_color('#8E44AD')
                
                for col_num, value in enumerate(pv_aff.columns.values):
                    ws_aff.write(0, col_num, value, header_fmt)

                ws_aff.set_column('A:A', 30, cell_fmt)
                ws_aff.set_column('B:B', 15, int_fmt)
                ws_aff.set_column('C:C', 15, int_fmt)
                ws_aff.set_column('D:D', 15, pct_fmt)

        # =========================================================
        # TIPO 2: OPERATIVO (Desempeño & Detalle)
        # =========================================================
        elif report_type == "Operativo (Desempeño & Detalle)":
            
            # --- HOJA: RANKING OPERATIVO ---
            rank_data = []
            for ag in agents:
                ag_data = df_export[df_export['agent'] == ag]
                total = len(ag_data)
                comp = len(ag_data[ag_data['result'].str.contains('Completed', case=False, na=False) & 
                                 ~ag_data['result'].str.contains('Not', case=False, na=False)])
                not_comp = total - comp
                conv = comp / total if total > 0 else 0
                
                rank_data.append({
                    "AGENTE": user_map.get(ag, ag),
                    "TOTAL GESTIONES": total,
                    "WC COMPLETED": comp,
                    "WC NOT COMPLETED": not_comp,
                    "CONVERSIÓN": conv
                })
            
            df_rank = pd.DataFrame(rank_data).sort_values("WC COMPLETED", ascending=False)
            
            df_rank.to_excel(writer, sheet_name='Ranking Operativo', index=False)
            ws_rank = writer.sheets['Ranking Operativo']
            ws_rank.set_tab_color('#2980B9')
            
            for col, val in enumerate(df_rank.columns):
                ws_rank.write(0, col, val, header_fmt)
            
            ws_rank.set_column('A:A', 30, cell_fmt)
            ws_rank.set_column('B:D', 18, int_fmt)
            ws_rank.set_column('E:E', 15, pct_fmt)
            ws_rank.conditional_format(f'E2:E{len(df_rank)+1}', {'type': 'cell', 'criteria': '>=', 'value': 0.10, 'format': success_fmt})

            # --- HOJAS INDIVIDUALES POR AGENTE ---
            for ag in agents:
                df_ag = df_export[df_export['agent'] == ag].copy()
                t_status = df_ag['transfer_status'] if 'transfer_status' in df_ag.columns else '-'
                
                df_final = pd.DataFrame({
                    'FECHA': df_ag['created_at'].dt.strftime('%Y-%m-%d %H:%M'),
                    'ID': df_ag['cordoba_id'],
                    'ETAPA': df_ag['info_until'],
                    'RESULTADO': df_ag['result'],
                    'TRANSFERENCIA': t_status,
                    'COMENTARIOS': df_ag['comments']
                })
                
                sheet_name = str(user_map.get(ag, ag)).replace('/', '')[:30]
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
                
                ws_ag = writer.sheets[sheet_name]
                ws_ag.set_column('A:A', 18, cell_center)
                ws_ag.set_column('B:B', 15, cell_center)
                ws_ag.set_column('C:C', 20, cell_fmt)
                ws_ag.set_column('D:E', 20, cell_fmt)
                ws_ag.set_column('F:F', 60, cell_fmt)

                for col, val in enumerate(df_final.columns):
                    ws_ag.write(0, col, val, header_fmt)

        # =========================================================
        # TIPO 3: CALIDAD (Fricción & Errores)
        # =========================================================
        elif report_type == "Calidad (Fricción & Errores)":
            
            # --- HOJA: FUNNEL DE CAÍDAS ---
            if 'info_until' in df_export.columns:
                df_funnel = df_export['info_until'].value_counts().reset_index()
                df_funnel.columns = ['ETAPA', 'CANTIDAD']
                df_funnel['%'] = df_funnel['CANTIDAD'] / len(df_export)
                df_funnel.to_excel(writer, sheet_name='Funnel Caídas', index=False)
                
                ws_fun = writer.sheets['Funnel Caídas']
                ws_fun.set_tab_color('#C0392B')
                for col, val in enumerate(df_funnel.columns): ws_fun.write(0, col, val, header_fmt)
                
                ws_fun.set_column('A:A', 40, cell_fmt)
                ws_fun.set_column('B:B', 15, cell_center)
                ws_fun.set_column('C:C', 15, pct_fmt)
                ws_fun.conditional_format(f'B2:B{len(df_funnel)+1}', {'type': 'data_bar', 'bar_color': '#E74C3C'})

            # --- HOJA: FALLOS TRANSFERENCIA ---
            mask_fail = df_export['comments'].str.contains('Unsuccessful', case=False, na=False) | \
                        df_export['comments'].str.contains('Issue:', case=False, na=False)
            if 'transfer_status' in df_export.columns:
                mask_fail = mask_fail | df_export['transfer_status'].str.contains('Unsuccessful', case=False, na=False)
                
            df_err = df_export[mask_fail][['agent', 'transfer_status', 'comments', 'cordoba_id']].copy()
            df_err.to_excel(writer, sheet_name='Errores Transfer', index=False)
            
            ws_err = writer.sheets['Errores Transfer']
            ws_err.set_tab_color('#D35400')
            for col, val in enumerate(df_err.columns): ws_err.write(0, col, val, header_fmt)
            ws_err.set_column('A:B', 20, cell_fmt)
            ws_err.set_column('C:C', 50, cell_fmt)

            # --- HOJA: AUDITORÍA FULL (LIMPIA) ---
            # Columnas permitidas: Quitamos id, user_id, customer
            allowed_cols = [
                'created_at', 'agent', 'cordoba_id', 'result', 
                'affiliate', 'comments', 'info_until', 
                'client_language', 'transfer_status'
            ]
            
            # Filtramos solo las que existen en el dataframe
            cols_to_export = [c for c in allowed_cols if c in df_export.columns]
            
            df_clean_audit = df_export[cols_to_export].copy()
            
            # Formatear fecha a string para que se vea bien
            if 'created_at' in df_clean_audit.columns:
                df_clean_audit['created_at'] = df_clean_audit['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')

            df_clean_audit.to_excel(writer, sheet_name='Auditoría Full', index=False)
            
            ws_raw = writer.sheets['Auditoría Full']
            ws_raw.set_tab_color('#7F7F7F')
            for col, val in enumerate(df_clean_audit.columns): 
                ws_raw.write(0, col, val, header_fmt)
            
            ws_raw.set_column('A:Z', 20, cell_fmt)

    return output

# ==============================================================================
# SECCIÓN DE UI
# ==============================================================================

def _render_dashboard(conn, df_raw: pd.DataFrame, total_bancos: int):
    # --- KPIs SUPERIORES ---
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

    # --- LIVE FEED ---
    st.subheader("📡 Actividad en Tiempo Real")
    if st.button("🔄 Refrescar Feed"):
        st.rerun()

    df_feed = admin_service.fetch_live_feed(conn)
    if not df_feed.empty:
        st.dataframe(
            df_feed,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Time": st.column_config.TextColumn("Hora (ET)", width="small"),
                "agent_real_name": st.column_config.TextColumn("Agente", width="medium"),
                "cordoba_id": st.column_config.TextColumn("Cordoba ID", width="medium"),
                "result": st.column_config.TextColumn("Resultado Detallado", width="large"),
                "affiliate": st.column_config.TextColumn("Afiliado", width="medium"),
            }
        )
    else:
        st.info("Esperando actividad...")

    st.markdown("---")

    # --- GRÁFICOS ---
    if not df_today.empty:
        g1, g2 = st.columns([2, 1])
        with g1:
            st.subheader("Rendimiento por Agente (Hoy)")
            chart_data = df_today['agent'].value_counts().reset_index()
            chart_data.columns = ['Agente', 'Notas']
            chart = alt.Chart(chart_data).mark_bar(cornerRadius=4).encode(
                x=alt.X('Notas', title='Cantidad de Notas'),
                y=alt.Y('Agente', sort='-x', title=None),
                color=alt.value("#3b82f6"),
                tooltip=['Agente', 'Notas']
            ).properties(height=320)
            st.altair_chart(chart, use_container_width=True)
            
        with g2:
            st.subheader("Resultados Globales")
            df_today['Status_Simple'] = df_today['result'].apply(
                lambda x: 'Completed' if 'Completed' in str(x) and 'Not' not in str(x) else 'Not Completed'
            )
            pie = alt.Chart(df_today).mark_arc(innerRadius=60).encode(
                theta=alt.Theta("count()", stack=True),
                color=alt.Color("Status_Simple", scale=alt.Scale(domain=['Completed', 'Not Completed'], range=['#2ecc71', '#e74c3c']), legend=None),
                tooltip=["Status_Simple", "count()"]
            )
            st.altair_chart(pie, use_container_width=True)

    # --- CENTRO DE REPORTES INTELIGENTE ---
    with st.expander("📥 Centro de Reportes y Exportación", expanded=False):
        st.markdown("### Configuración del Reporte")
        
        c_type, c_filt = st.columns([2, 2])
        
        with c_type:
            report_type = st.radio(
                "Selecciona el Tipo de Reporte:",
                [
                    "Estratégico (KPIs & Negocio)",
                    "Operativo (Desempeño & Detalle)",
                    "Calidad (Fricción & Errores)"
                ],
                captions=[
                    "Para Gerencia: Conversión global, Afiliados y Ranking por Eficiencia.",
                    "Para Supervisión: Ranking por Volumen (WC Completed), Conversión y detalle por agente.",
                    "Para QA/IT: Análisis de caídas, errores de transferencia y logs crudos."
                ]
            )

        with c_filt:
            st.markdown("**Filtros de Datos**")
            c_d1, c_d2 = st.columns(2)
            start_date = c_d1.date_input("Desde", value=datetime.now().replace(day=1))
            end_date = c_d2.date_input("Hasta", value=datetime.now())
            
            agent_opts = ["TODOS (Global)"] + admin_service.fetch_agent_list(conn)
            target_agent = st.selectbox("Filtrar Agente Específico", agent_opts)
        
        st.divider()
        
        if st.button(f"📊 Generar Reporte {report_type.split(' ')[0]}", type="primary", use_container_width=True):
            try:
                with st.spinner(f"Compilando datos para reporte {report_type.split(' ')[0]}..."):
                    df_export = admin_service.fetch_logs_for_export(conn, start_date, end_date, target_agent)
                    
                    if not df_export.empty:
                        user_map = admin_service.fetch_user_map(conn)
                        # Llamada al motor modular
                        excel_data = _generate_excel_file(df_export, user_map, report_type)
                        
                        file_prefix = "Estrategico" if "Estratégico" in report_type else "Operativo" if "Operativo" in report_type else "Calidad_QA"
                        
                        st.success("✅ Archivo listo para descarga.")
                        st.download_button(
                            label="💾 Descargar Archivo Excel", 
                            data=excel_data.getvalue(), 
                            file_name=f"Reporte_{file_prefix}_{start_date}_{end_date}.xlsx", 
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("No se encontraron datos en el rango seleccionado.")
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
    c_add, c_edit = st.columns([1, 2], gap="large")
    with c_add:
        st.subheader("Nuevo Acreedor")
        with st.container(border=True):
            name = st.text_input("Nombre Entidad", key="new_name")
            abbrev = st.text_input("Abreviación (Alias)", key="new_abbr")
            if st.button("Agregar Banco", use_container_width=True, type="primary"):
                if name:
                    if admin_service.create_creditor(conn, name, abbrev):
                        st.success("Banco creado.")
                        time.sleep(0.5); st.rerun()
                else:
                    st.error("Nombre obligatorio.")
    with c_edit:
        st.subheader("Editar Acreedor")
        try:
            df_all = admin_service.search_creditors(conn, "")
        except:
            df_all = pd.DataFrame()
        search_query = st.text_input("Buscar por Abreviación o Nombre:", placeholder="Ej: TDRC").strip()
        target_bank = None
        if not df_all.empty and search_query:
            mask = (df_all['name'].str.contains(search_query, case=False, na=False) | 
                    df_all['abreviation'].str.contains(search_query, case=False, na=False))
            df_results = df_all[mask]
            if not df_results.empty:
                results = df_results.to_dict('records')
                if len(results) == 1:
                    target_bank = results[0]
                    st.success(f"✅ Encontrado: {target_bank['name']}")
                elif 1 < len(results) <= 10:
                    options = {r['id']: f"{r['abreviation']} - {r['name']}" for r in results}
                    sel = st.radio("Selecciona:", list(options.keys()), format_func=lambda x: options[x])
                    target_bank = next(r for r in results if r['id'] == sel)
                else:
                    st.warning(f"⚠️ {len(results)} resultados. Refina tu búsqueda.")
            else:
                st.info("Sin coincidencias.")
        if target_bank:
            with st.container(border=True):
                with st.form("bank_edit"):
                    c1, c2 = st.columns([2, 1])
                    n_val = c1.text_input("Nombre", target_bank['name'])
                    a_val = c2.text_input("Abrev.", target_bank['abreviation'])
                    if st.form_submit_button("💾 Guardar Cambios"):
                        if admin_service.update_creditor(conn, target_bank['id'], n_val, a_val):
                            st.success("Guardado."); st.rerun()
    st.markdown("---")
    st.subheader("🚨 Reportes de Agentes (Bancos No Encontrados)")
    df_misses = admin_service.fetch_search_misses(conn)
    if not df_misses.empty:
        for idx, row in df_misses.iterrows():
            with st.container(border=True):
                c_info, c_act = st.columns([4, 1])
                with c_info:
                    st.markdown(f"**Código Buscado:** `{row['abreviation']}`")
                    st.caption(f"Reportado en Córdoba ID: {row['cordoba_id']} | Fecha: {row['created_at']}")
                with c_act:
                    if st.button("🗑️ Descartar", key=f"dismiss_{row['id']}"):
                        if admin_service.dismiss_search_miss(conn, row['id']):
                            st.rerun()
    else:
        st.success("✨ ¡Todo limpio! No hay reportes pendientes.")

def _render_updates_manager(conn):
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
        st.markdown("**Mensajes Activos & Auditoría**")
        df_upd = admin_service.fetch_active_updates(conn)
        updates = df_upd.to_dict('records')
        total_agents = admin_service.get_total_active_agents(conn)
        for u in updates:
            color = "#dc2626" if u['category'] == 'Critical' else "#d97706" if u['category'] == 'Warning' else "#2563eb"
            with st.container(border=True):
                st.markdown(f"<h4 style='color:{color}; margin:0'>[{u['category']}] {u['title']}</h4>", unsafe_allow_html=True)
                st.write(u['message'])
                st.caption(f"Publicado: {u['date']}")
                df_reads = admin_service.fetch_update_reads(conn, u['id'])
                read_count = len(df_reads)
                pct = read_count / total_agents if total_agents > 0 else 0
                st.progress(pct, text=f"Leído por {read_count} de ~{total_agents} agentes")
                with st.expander(f"👁️ Ver quién leyó ({read_count})"):
                    if not df_reads.empty:
                        st.dataframe(df_reads, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nadie lo ha leído aún.")
                if st.button("Archivar Noticia", key=f"arc_{u['id']}", type="primary"):
                    if admin_service.archive_update(conn, u['id']):
                        st.rerun()

def _render_user_manager(conn):
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

def show():
    st.title("🎛️ Torre de Control")
    conn = get_db_connection()
    if not conn: return
    tabs = st.tabs(["📊 Dashboard", "🛠️ Editor Logs", "🏦 Bancos", "🔔 Noticias", "👥 Usuarios"])
    with tabs[0]:
        total_bancos, df_logs = admin_service.fetch_global_kpis(conn)
        _render_dashboard(conn, df_logs, total_bancos)
    with tabs[1]: _render_log_editor(conn)
    with tabs[2]: _render_bank_manager(conn)
    with tabs[3]: _render_updates_manager(conn)
    with tabs[4]: _render_user_manager(conn)

if __name__ == "__main__":
    show()