import time
import pytz
import bcrypt
import io
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy import text

# --- Infrastructure & Connection ---

def init_connection():
    """
    Conexión a PostgreSQL Local (Docker) usando el conector nativo de Streamlit.
    Requiere configuración en .streamlit/secrets.toml bajo [connections.local_db]
    """
    try:
        return st.connection("local_db", type="sql")
    except Exception as e:
        st.error(f"Error conectando a BD Local: {e}")
        return None

# --- Helper para Transacciones (Escritura) ---

def run_transaction(conn, query_str: str, params: dict = None):
    """Ejecuta una operación de escritura (INSERT, UPDATE, DELETE) de forma segura."""
    try:
        with conn.session as session:
            session.execute(text(query_str), params if params else {})
            session.commit()
        return True
    except Exception as e:
        st.error(f"Error en transacción: {e}")
        return False

# --- Backend / Data Layer ---

def fetch_global_kpis(conn):
    """Recupera métricas operativas usando SQL."""
    if not conn: return 0, pd.DataFrame()

    try:
        # 1. Total Bancos
        df_count = conn.query('SELECT COUNT(*) as total FROM "Creditors"', ttl=0)
        total_bancos = df_count.iloc[0]['total'] if not df_count.empty else 0
        
        # 2. Actividad Reciente
        # Traemos logs desde ayer UTC para asegurar cobertura horaria
        yesterday_utc = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        # SQL Query: Filtrar fecha y excluir 'test'
        logs_query = """
            SELECT * FROM "Logs" 
            WHERE created_at >= :yesterday 
            AND agent != 'test'
        """
        df_logs = conn.query(logs_query, params={"yesterday": yesterday_utc}, ttl=0)
            
        return total_bancos, df_logs
    except Exception as e:
        st.error(f"KPI Fetch Error: {e}")
        return 0, pd.DataFrame()

def fetch_agent_list(conn):
    """Retorna lista de agentes (usernames) activos."""
    try:
        df = conn.query('SELECT username FROM "Users" WHERE active = TRUE ORDER BY username', ttl=60)
        return df['username'].tolist()
    except:
        return []

def fetch_user_map(conn):
    """Retorna diccionario {username: name}."""
    try:
        df = conn.query('SELECT username, name FROM "Users"', ttl=600)
        return pd.Series(df.name.values, index=df.username).to_dict()
    except:
        return {}

# --- UI Components (Tabs) ---

def _render_dashboard(conn, df_raw: pd.DataFrame, total_bancos: int):
    """Tab 1: Visualización de métricas y exportación."""
    
    # --- PROCESAMIENTO DE FECHAS (Pandas Logic - Se mantiene igual) ---
    df_today = pd.DataFrame()
    today_et = datetime.now(pytz.timezone('US/Eastern')).date()

    if not df_raw.empty and 'created_at' in df_raw.columns:
        df_raw['created_at'] = pd.to_datetime(df_raw['created_at'], utc=True)
        df_raw['date_et'] = df_raw['created_at'].dt.tz_convert('US/Eastern').dt.date
        df_today = df_raw[df_raw['date_et'] == today_et].copy()

    # 1. KPIs Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏦 Base de Datos", total_bancos, delta="Bancos Activos")
    
    if not df_today.empty:
        total_calls = len(df_today)
        sales = len(df_today[df_today['result'].str.contains('Completed', case=False, na=False) & ~df_today['result'].str.contains('Not', case=False, na=False)])
        active_agents = df_today['agent'].nunique()
        conversion = (sales / total_calls * 100) if total_calls > 0 else 0
        
        c2.metric("📞 Llamadas", total_calls, delta="Hoy (ET)")
        c3.metric("🏆 Ventas", sales, delta=f"{conversion:.1f}% Conv.")
        c4.metric("👨‍💼 Staff Online", active_agents)
    else:
        for col in [c2, c3, c4]: col.metric("-", 0)

    st.markdown("---")

    # 2. Charts
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
            df_today['Status_Simple'] = df_today['result'].apply(lambda x: 'Completed' if 'Completed' in x and 'Not' not in x else 'Not Completed')
            
            base = alt.Chart(df_today).encode(theta=alt.Theta("count()", stack=True))
            pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                color=alt.Color("Status_Simple", scale=alt.Scale(domain=['Completed', 'Not Completed'], range=['#2ecc71', '#e74c3c']), legend=None),
                tooltip=["result", "count()"],
                order=alt.Order("count()", sort="descending")
            )
            text = base.mark_text(radius=120).encode(
                text="count()",
                order=alt.Order("Status_Simple"),
                color=alt.value("black")  
            )
            st.altair_chart(pie + text, use_container_width=True)
    else:
        st.info("Sin actividad registrada hoy.")

    # 3. Export Module (AUDITORIA EXCEL - SQL Version)
    with st.expander("📥 Auditoría y Exportación", expanded=False):
        c_d1, c_d2, c_filt = st.columns([1, 1, 2])
        start_date = c_d1.date_input("Desde", value=datetime.now().replace(day=1))
        end_date = c_d2.date_input("Hasta", value=datetime.now())
        
        agent_opts = ["TODOS (Global)"] + fetch_agent_list(conn)
        target_agent = c_filt.selectbox("Filtrar Agente", agent_opts)
        
        if st.button("Generar Reporte Excel", type="primary"):
            try:
                # Construcción dinámica de la consulta SQL
                base_query = """
                    SELECT * FROM "Logs" 
                    WHERE created_at >= :start 
                    AND created_at <= :end
                """
                params = {
                    "start": f"{start_date}T00:00:00",
                    "end": f"{end_date}T23:59:59"
                }
                
                # Filtro Anti-Test y Agente Específico
                if "TODOS" not in target_agent:
                    base_query += " AND agent = :target"
                    params["target"] = target_agent
                else:
                    base_query += " AND agent != 'test'"
                
                base_query += " ORDER BY created_at DESC"
                
                # Ejecutar Query
                df_export = conn.query(base_query, params=params, ttl=0)
                
                if not df_export.empty:
                    # --- Generación de Excel (Misma lógica que antes) ---
                    user_map = fetch_user_map(conn)
                    output = io.BytesIO()
                    
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        workbook = writer.book
                        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                        
                        # HOJA 1: CENTRALIZADOR
                        summary_data = []
                        agents = sorted(df_export['agent'].unique())
                        
                        for idx, ag in enumerate(agents):
                            ag_data = df_export[df_export['agent'] == ag]
                            total = len(ag_data)
                            comp = len(ag_data[ag_data['result'].str.contains('Completed', case=False, na=False) & ~ag_data['result'].str.contains('Not', case=False, na=False)])
                            not_comp = len(ag_data[ag_data['result'].str.contains('Not', case=False, na=False)])
                            real_name = user_map.get(ag, ag)

                            summary_data.append({
                                "N°": idx + 1, "AGENT": real_name, "TOTAL WC COMPLETED": comp, "TOTAL WC NOT COMPLETED": not_comp, "TOTAL CALLS": total
                            })
                        
                        df_central = pd.DataFrame(summary_data)
                        df_central.to_excel(writer, sheet_name='Centralizador', index=False)
                        
                        ws_central = writer.sheets['Centralizador']
                        for col_num, value in enumerate(df_central.columns.values):
                            ws_central.write(0, col_num, value, header_fmt)
                        ws_central.set_column('A:A', 5); ws_central.set_column('B:B', 30); ws_central.set_column('C:E', 25)
                        
                        # HOJAS POR AGENTE
                        for ag in agents:
                            df_ag = df_export[df_export['agent'] == ag].copy()
                            df_final_ag = pd.DataFrame()
                            df_final_ag['N°'] = range(1, len(df_ag) + 1)
                            df_final_ag['CORDOBA ID'] = df_ag['cordoba_id']
                            df_final_ag['CALL PROGRESS'] = df_ag['info_until']
                            df_final_ag['REASON'] = df_ag['comments']
                            df_final_ag['RESULT'] = df_ag['result']
                            df_final_ag['LANGUAGE'] = df_ag['client_language']
                            
                            sheet_name = str(ag)[:31]
                            df_final_ag.to_excel(writer, sheet_name=sheet_name, index=False)
                            
                            ws_ag = writer.sheets[sheet_name]
                            for col_num, value in enumerate(df_final_ag.columns.values):
                                ws_ag.write(0, col_num, value, header_fmt)
                            ws_ag.set_column('A:A', 5); ws_ag.set_column('B:B', 15); ws_ag.set_column('C:C', 25)
                            ws_ag.set_column('D:D', 45); ws_ag.set_column('E:E', 25); ws_ag.set_column('F:F', 15)

                    output.seek(0)
                    st.download_button(label="💾 Descargar Reporte Excel (.xlsx)", data=output, file_name=f"Reporte_Gestion_{start_date}_{end_date}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    st.success(f"Reporte generado con éxito.")
                else:
                    st.warning("No hay datos para el periodo seleccionado.")
            except Exception as e:
                st.error(f"Error generando Excel: {e}")

def _render_log_editor(conn):
    """Tab 2: Herramienta de corrección de registros (CRUD SQL)."""
    st.subheader("🛠️ Quirófano de Registros")
    search_id = st.text_input("Buscar por ID Córdoba:", placeholder="Ej: 1234567890").strip()
    
    if not search_id: return

    try:
        # SQL Select
        df_res = conn.query('SELECT * FROM "Logs" WHERE cordoba_id = :cid ORDER BY created_at DESC', params={"cid": search_id}, ttl=0)
        
        if df_res.empty:
            st.warning("No se encontraron coincidencias por ID.")
            return

        results = df_res.to_dict('records') # Convertir a lista de dicts para compatibilidad
        options = {}
        for l in results:
            dt_utc = pd.to_datetime(l['created_at'])
            dt_et = dt_utc.tz_convert('US/Eastern') if dt_utc.tzinfo else dt_utc.tz_localize('UTC').tz_convert('US/Eastern')
            lbl = f"{dt_et.strftime('%m/%d %I:%M %p')} | {l['result']} | Ag: {l.get('agent','?')}"
            options[l['id']] = lbl

        selected_id = st.selectbox("Seleccionar entrada:", list(options.keys()), format_func=lambda x: options[x])
        record = next(r for r in results if r['id'] == selected_id)
        
        st.divider()
        
        with st.form("editor_form"):
            st.markdown(f"**Editando Registro #{record['id']}**")
            c1, c2 = st.columns(2)
            new_cid = c1.text_input("Cordoba ID", record['cordoba_id'])
            new_aff = c2.text_input("Afiliado", record['affiliate'] or "")
            c3, c4 = st.columns(2)
            valid_results = ["Completed", "No Answer", "Voicemail", "Callback", "Not Interested", "Not Completed"]
            current_res = record['result'].split(" - ")[0] if record['result'] else "Completed"
            if current_res not in valid_results: valid_results.insert(0, current_res)
            new_res = c3.selectbox("Resultado", valid_results, index=valid_results.index(current_res))
            c4.text_input("User ID (Vinculado)", value=str(record.get('user_id', 'N/A')), disabled=True)
            new_comm = st.text_area("Comentarios (Censurados)", record['comments'] or "")
            
            if st.form_submit_button("💾 Aplicar Cambios", type="primary"):
                # SQL UPDATE
                sql = """
                    UPDATE "Logs" SET 
                        cordoba_id = :cid, affiliate = :aff, 
                        result = :res, comments = :comm 
                    WHERE id = :rid
                """
                params = {"cid": new_cid, "aff": new_aff, "res": new_res, "comm": new_comm, "rid": selected_id}
                if run_transaction(conn, sql, params):
                    st.success("Registro actualizado correctamente.")
                    time.sleep(1)
                    st.rerun()
    except Exception as e:
        st.error(f"Error en búsqueda: {e}")

def _render_bank_manager(conn):
    """Tab 3: Gestión de Acreedores (SQL)."""
    c_add, c_edit = st.columns([1, 2])
    
    with c_add:
        with st.container(border=True):
            st.markdown("**Nuevo Acreedor**")
            name = st.text_input("Nombre Entidad")
            abbrev = st.text_input("Abreviación (Alias)")
            if st.button("Agregar Banco", use_container_width=True):
                if name:
                    sql = 'INSERT INTO "Creditors" (name, abreviation) VALUES (:name, :abbr)'
                    if run_transaction(conn, sql, {"name": name, "abbr": abbrev}):
                        st.rerun()
    
    with c_edit:
        q = st.text_input("🔍 Filtrar bancos...", label_visibility="collapsed")
        if q:
            df_banks = conn.query('SELECT * FROM "Creditors" WHERE name ILIKE :q LIMIT 15', params={"q": f"%{q}%"}, ttl=0)
            banks = df_banks.to_dict('records')
            
            if banks:
                b_opts = {b['id']: f"{b['name']} ({b['abreviation']})" for b in banks}
                sel_id = st.selectbox("Editar:", list(b_opts.keys()), format_func=lambda x: b_opts[x])
                target = next(b for b in banks if b['id'] == sel_id)
                
                with st.form("bank_edit"):
                    n_val = st.text_input("Nombre", target['name'])
                    a_val = st.text_input("Abrev.", target['abreviation'])
                    c_del, c_upd = st.columns([1, 1])
                    
                    if c_del.form_submit_button("🗑️ Eliminar"):
                        if run_transaction(conn, 'DELETE FROM "Creditors" WHERE id = :id', {"id": sel_id}):
                            st.rerun()
                    if c_upd.form_submit_button("Actualizar", type="primary"):
                        sql = 'UPDATE "Creditors" SET name = :n, abreviation = :a WHERE id = :id'
                        if run_transaction(conn, sql, {"n": n_val, "a": a_val, "id": sel_id}):
                            st.rerun()

def _render_updates_manager(conn):
    """Tab 4: Centro de Mensajes (SQL)."""
    c1, c2 = st.columns([1, 2])
    
    with c1:
        with st.form("new_update"):
            st.markdown("**Publicar Noticia**")
            tit = st.text_input("Título")
            msg = st.text_area("Cuerpo del mensaje")
            cat = st.selectbox("Nivel", ["Info", "Warning", "Critical"])
            
            if st.form_submit_button("Publicar", use_container_width=True):
                if tit and msg:
                    sql = """
                        INSERT INTO "Updates" (date, title, message, category, active) 
                        VALUES (:date, :tit, :msg, :cat, TRUE)
                    """
                    params = {"date": datetime.now().strftime('%Y-%m-%d'), "tit": tit, "msg": msg, "cat": cat}
                    if run_transaction(conn, sql, params):
                        st.rerun()

    with c2:
        st.markdown("**Mensajes Activos**")
        df_upd = conn.query('SELECT * FROM "Updates" WHERE active = TRUE ORDER BY date DESC', ttl=0)
        updates = df_upd.to_dict('records')
        
        for u in updates:
            color = "#dc2626" if u['category'] == 'Critical' else "#d97706" if u['category'] == 'Warning' else "#2563eb"
            with st.container(border=True):
                st.markdown(f"<span style='color:{color}; font-weight:bold'>[{u['category']}] {u['title']}</span>", unsafe_allow_html=True)
                st.write(u['message'])
                if st.button("Archivar", key=f"arc_{u['id']}"):
                    if run_transaction(conn, 'UPDATE "Updates" SET active = FALSE WHERE id = :id', {"id": u['id']}):
                        st.rerun()

def _render_user_manager(conn):
    """Tab 5: Gestión de Usuarios (SQL)."""
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
                    hashed = bcrypt.hashpw(u_pass.encode(), bcrypt.gensalt()).decode()
                    sql = """
                        INSERT INTO "Users" (username, name, password, role, active) 
                        VALUES (:u, :n, :p, :r, TRUE)
                    """
                    if run_transaction(conn, sql, {"u": u_user, "n": u_name, "p": hashed, "r": u_role}):
                        st.success(f"Usuario {u_user} creado.")
                        time.sleep(1); st.rerun()

    with c2:
        df_users = conn.query('SELECT * FROM "Users" ORDER BY username', ttl=0)
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
                sql = 'UPDATE "Users" SET name = :n, role = :r, active = :a'
                params = {"n": new_name, "r": new_role, "a": is_active, "id": sel_uid}
                
                if new_pass:
                    sql += ', password = :p'
                    params["p"] = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                
                sql += ' WHERE id = :id'
                
                if run_transaction(conn, sql, params):
                    st.success("Perfil actualizado.")
                    time.sleep(1); st.rerun()

# --- Entry Point ---

def show():
    st.title("🎛️ Torre de Control (Local)")
    conn = init_connection()
    if not conn: return

    tabs = st.tabs([
        "📊 Dashboard", 
        "🛠️ Editor Logs", 
        "🏦 Bancos", 
        "🔔 Noticias", 
        "👥 Usuarios"
    ])

    with tabs[0]:
        total_bancos, df_logs = fetch_global_kpis(conn)
        _render_dashboard(conn, df_logs, total_bancos)

    with tabs[1]:
        _render_log_editor(conn)

    with tabs[2]:
        _render_bank_manager(conn)

    with tabs[3]:
        _render_updates_manager(conn)

    with tabs[4]:
        _render_user_manager(conn)

if __name__ == "__main__":
    show()