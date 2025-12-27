import time
import pytz
import bcrypt
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime
from supabase import Client

# --- Infrastructure & Connection ---

@st.cache_resource
def init_connection() -> Client:
    """Singleton para conexión a Supabase."""
    try:
        # Soporte para secretos anidados (Streamlit Cloud) o planos (Local)
        creds = st.secrets["connections"]["supabase"] if "connections" in st.secrets else st.secrets
        return Client(creds["URL"], creds["KEY"])
    except Exception:
        return None

# --- Backend / Data Layer ---

def fetch_global_kpis(supabase: Client):
    """
    Recupera métricas operativas en tiempo real.
    Returns:
        tuple: (total_creditors, df_daily_activity)
    """
    if not supabase: return 0, pd.DataFrame()

    try:
        # Total Bancos (Query ligera usando count=exact)
        res_bancos = supabase.table("Creditors").select("name", count="exact", head=True).execute()
        
        # Actividad del día (Eastern Time)
        tz = pytz.timezone('US/Eastern')
        today_str = datetime.now(tz).strftime('%Y-%m-%d')
        
        res_logs = supabase.table("Logs").select("*")\
            .gte("created_at", today_str)\
            .neq("agent", "test")\
            .execute()
            
        return res_bancos.count, pd.DataFrame(res_logs.data)
    except Exception as e:
        st.error(f"KPI Fetch Error: {e}")
        return 0, pd.DataFrame()

def fetch_agent_list(supabase: Client):
    """Retorna lista de agentes activos para filtros de auditoría."""
    try:
        res = supabase.table("Users").select("username").eq("active", True).order("username").execute()
        return [u['username'] for u in res.data]
    except:
        return []

# --- UI Components (Tabs) ---

def _render_dashboard(supabase: Client, df_logs: pd.DataFrame, total_bancos: int):
    """Tab 1: Visualización de métricas y exportación."""
    
    # 1. KPIs Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏦 Base de Datos", total_bancos, delta="Bancos Activos")
    
    if not df_logs.empty:
        total_calls = len(df_logs)
        sales = len(df_logs[df_logs['result'].str.contains('Completed', case=False, na=False)])
        active_agents = df_logs['agent'].nunique()
        conversion = (sales / total_calls * 100) if total_calls > 0 else 0
        
        c2.metric("📞 Llamadas", total_calls, delta="Hoy (ET)")
        c3.metric("🏆 Ventas", sales, delta=f"{conversion:.1f}% Conv.")
        c4.metric("👨‍💼 Staff Online", active_agents)
    else:
        for col in [c2, c3, c4]: col.metric("-", 0)

    st.markdown("---")

    # 2. Charts
    if not df_logs.empty:
        g1, g2 = st.columns([2, 1])
        with g1:
            st.subheader("Rendimiento por Agente")
            chart = alt.Chart(df_logs).mark_bar(cornerRadius=4).encode(
                x=alt.X('count()', title='Notas'),
                y=alt.Y('agent', sort='-x', title=None),
                color=alt.Color('agent', legend=None),
                tooltip=['agent', 'count()']
            ).properties(height=320)
            st.altair_chart(chart, use_container_width=True)
            
        with g2:
            st.subheader("Resultados Globales")
            base = alt.Chart(df_logs).encode(theta=alt.Theta("count()", stack=True))
            pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                color=alt.Color("result", legend=None),
                tooltip=["result", "count()"],
                order=alt.Order("count()", sort="descending")
            )
            st.altair_chart(pie, use_container_width=True)
    else:
        st.info("Sin actividad registrada en el ciclo actual.")

    # 3. Export Module
    with st.expander("📥 Auditoría y Exportación", expanded=False):
        c_d1, c_d2, c_filt = st.columns([1, 1, 2])
        start_date = c_d1.date_input("Desde", value=datetime.now().replace(day=1))
        end_date = c_d2.date_input("Hasta", value=datetime.now())
        
        agent_opts = ["TODOS (Global)"] + fetch_agent_list(supabase)
        target_agent = c_filt.selectbox("Filtrar Agente", agent_opts)
        
        if st.button("Generar CSV", type="primary"):
            try:
                query = supabase.table("Logs").select("*")\
                    .gte("created_at", str(start_date))\
                    .lte("created_at", f"{end_date}T23:59:59")\
                    .order("created_at", desc=True)
                
                if "TODOS" not in target_agent:
                    query = query.eq("agent", target_agent)
                else:
                    query = query.neq("agent", "test")
                
                df_export = pd.DataFrame(query.execute().data)
                
                if not df_export.empty:
                    csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="💾 Descargar Reporte",
                        data=csv_data,
                        file_name=f"auditoria_{start_date}_{end_date}.csv",
                        mime="text/csv"
                    )
                    st.success(f"Procesados {len(df_export)} registros.")
                else:
                    st.warning("Búsqueda sin resultados.")
            except Exception as e:
                st.error(f"Error de exportación: {e}")

def _render_log_editor(supabase: Client):
    """Tab 2: Herramienta de corrección de registros (CRUD)."""
    st.subheader("🛠️ Quirófano de Registros")
    st.caption("Modificación de metadatos históricos.")
    
    search_term = st.text_input("Buscar registro:", placeholder="ID Córdoba o Nombre Cliente").strip()
    
    if not search_term: return

    try:
        # Búsqueda polimórfica: Si es dígito busca ID, si es texto busca nombre
        query = supabase.table("Logs").select("*").order("created_at", desc=True)
        if search_term.isdigit():
            query = query.eq("cordoba_id", search_term)
        else:
            query = query.ilike("customer", f"%{search_term}%")
            
        results = query.execute().data
        
        if not results:
            st.warning("No se encontraron coincidencias.")
            return

        # Selector de registro específico
        options = {l['id']: f"{l['created_at'][:10]} | {l['customer']} | {l['result']} ({l['agent']})" for l in results}
        selected_id = st.selectbox("Seleccionar entrada:", list(options.keys()), format_func=lambda x: options[x])
        
        record = next(r for r in results if r['id'] == selected_id)
        
        st.divider()
        
        with st.form("editor_form"):
            c1, c2 = st.columns(2)
            new_cust = c1.text_input("Cliente", record['customer'])
            new_cid = c2.text_input("Cordoba ID", record['cordoba_id'])
            
            c3, c4 = st.columns(2)
            new_aff = c3.text_input("Afiliado", record['affiliate'] or "")
            
            # Normalización de resultados permitidos
            valid_results = ["Completed", "No Answer", "Voicemail", "Callback", "Not Interested", "Not Completed"]
            current_res = record['result'].split(" - ")[0] if record['result'] else "Completed"
            res_idx = valid_results.index(current_res) if current_res in valid_results else 0
            
            new_res = c4.selectbox("Resultado", valid_results, index=res_idx)
            new_comm = st.text_area("Comentarios", record['comments'] or "")
            
            if st.form_submit_button("💾 Aplicar Cambios", type="primary"):
                supabase.table("Logs").update({
                    "customer": new_cust,
                    "cordoba_id": new_cid,
                    "affiliate": new_aff,
                    "result": new_res,
                    "comments": new_comm
                }).eq("id", selected_id).execute()
                
                st.success("Registro actualizado correctamente.")
                time.sleep(1)
                st.rerun()

    except Exception as e:
        st.error(f"Error en búsqueda: {e}")

def _render_bank_manager(supabase: Client):
    """Tab 3: Gestión de Acreedores (Creditors)."""
    c_add, c_edit = st.columns([1, 2])
    
    with c_add:
        with st.container(border=True):
            st.markdown("**Nuevo Acreedor**")
            name = st.text_input("Nombre Entidad")
            abbrev = st.text_input("Abreviación (Alias)")
            
            if st.button("Agregar Banco", use_container_width=True):
                if name:
                    supabase.table("Creditors").insert({"name": name, "abreviation": abbrev}).execute()
                    st.rerun()
    
    with c_edit:
        q = st.text_input("🔍 Filtrar bancos...", label_visibility="collapsed")
        if q:
            res = supabase.table("Creditors").select("*").ilike("name", f"%{q}%").limit(15).execute()
            banks = res.data
            
            if banks:
                b_opts = {b['id']: f"{b['name']} ({b['abreviation']})" for b in banks}
                sel_id = st.selectbox("Editar:", list(b_opts.keys()), format_func=lambda x: b_opts[x])
                target = next(b for b in banks if b['id'] == sel_id)
                
                with st.form("bank_edit"):
                    n_val = st.text_input("Nombre", target['name'])
                    a_val = st.text_input("Abrev.", target['abreviation'])
                    
                    c_del, c_upd = st.columns([1, 1])
                    if c_del.form_submit_button("🗑️ Eliminar"):
                        supabase.table("Creditors").delete().eq("id", sel_id).execute()
                        st.rerun()
                    if c_upd.form_submit_button("Actualizar", type="primary"):
                        supabase.table("Creditors").update({"name": n_val, "abreviation": a_val}).eq("id", sel_id).execute()
                        st.rerun()

def _render_updates_manager(supabase: Client):
    """Tab 4: Sistema de Notificaciones."""
    c1, c2 = st.columns([1, 2])
    
    with c1:
        with st.form("new_update"):
            st.markdown("**Publicar Noticia**")
            tit = st.text_input("Título")
            msg = st.text_area("Cuerpo del mensaje")
            cat = st.selectbox("Nivel", ["Info", "Warning", "Critical"])
            
            if st.form_submit_button("Publicar", use_container_width=True):
                if tit and msg:
                    supabase.table("Updates").insert({
                        "date": datetime.now().strftime('%Y-%m-%d'),
                        "title": tit, "message": msg, "category": cat, "active": True
                    }).execute()
                    st.rerun()

    with c2:
        st.markdown("**Mensajes Activos**")
        updates = supabase.table("Updates").select("*").eq("active", True).order("date", desc=True).execute().data
        
        for u in updates:
            color = "#dc2626" if u['category'] == 'Critical' else "#d97706" if u['category'] == 'Warning' else "#2563eb"
            with st.container(border=True):
                st.markdown(f"<span style='color:{color}; font-weight:bold'>[{u['category']}] {u['title']}</span>", unsafe_allow_html=True)
                st.write(u['message'])
                if st.button("Archivar", key=f"arc_{u['id']}"):
                    supabase.table("Updates").update({"active": False}).eq("id", u['id']).execute()
                    st.rerun()

def _render_user_manager(supabase: Client):
    """Tab 5: Administración de Usuarios (IAM)."""
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
                    # Encriptación obligatoria para cumplimiento SOC2
                    hashed = bcrypt.hashpw(u_pass.encode(), bcrypt.gensalt()).decode()
                    try:
                        supabase.table("Users").insert({
                            "username": u_user, 
                            "name": u_name, 
                            "password": hashed, 
                            "role": u_role
                        }).execute()
                        st.success(f"Usuario {u_user} creado.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando usuario: {e}")

    with c2:
        users = supabase.table("Users").select("*").order("username").execute().data
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
            new_pass = col_d.text_input("Reset Password", type="password", help="Dejar vacío para mantener la actual")
            
            if st.form_submit_button("Actualizar Perfil"):
                payload = {"name": new_name, "role": new_role, "active": is_active}
                if new_pass:
                    payload["password"] = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                
                supabase.table("Users").update(payload).eq("id", sel_uid).execute()
                st.success("Perfil actualizado.")
                time.sleep(1)
                st.rerun()

# --- Entry Point ---

def show():
    """Vista principal del Panel de Administración."""
    st.title("🎛️ Torre de Control")
    
    supabase = init_connection()
    if not supabase:
        st.error("Fatal Error: Database connection failed.")
        return

    # Tabs container
    tabs = st.tabs([
        "📊 Dashboard", 
        "🛠️ Editor Logs", 
        "🏦 Bancos", 
        "🔔 Noticias", 
        "👥 Usuarios"
    ])

    with tabs[0]:
        total_bancos, df_logs = fetch_global_kpis(supabase)
        _render_dashboard(supabase, df_logs, total_bancos)

    with tabs[1]:
        _render_log_editor(supabase)

    with tabs[2]:
        _render_bank_manager(supabase)

    with tabs[3]:
        _render_updates_manager(supabase)

    with tabs[4]:
        _render_user_manager(supabase)

if __name__ == "__main__":
    show()
