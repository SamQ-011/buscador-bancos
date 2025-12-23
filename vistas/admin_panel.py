import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client
import bcrypt
import time
import pytz

# --- 1. CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["URL"]
        key = st.secrets["connections"]["supabase"]["KEY"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_connection()

# --- 2. FUNCIONES DE DATOS (BACKEND) ---
def obtener_kpis_globales():
    """Calcula las métricas de toda la operación en tiempo real"""
    try:
        if not supabase: return 0, pd.DataFrame()

        # A. Total de Bancos
        res_bancos = supabase.table("Creditors").select("name", count="exact", head=True).execute()
        total_bancos = res_bancos.count
        
        # B. Actividad de HOY (Hora NY)
        zona_et = pytz.timezone('US/Eastern')
        ahora_et = datetime.now(zona_et)
        hoy_str = ahora_et.strftime('%Y-%m-%d')
        
        res_logs = supabase.table("Logs").select("*")\
            .gte("created_at", hoy_str)\
            .neq("agent", "test")\
            .execute()
            
        df_logs = pd.DataFrame(res_logs.data)
        return total_bancos, df_logs

    except Exception as e:
        return 0, pd.DataFrame()

def obtener_lista_agentes():
    try:
        if not supabase: return []
        res = supabase.table("Users").select("username").eq("active", True).order("username").execute()
        return [u['username'] for u in res.data]
    except:
        return []

# --- 3. INTERFAZ PRINCIPAL ---
def show():
    st.title("🎛️ Torre de Control")
    st.caption("Panel de Administración & Auditoría")

    if not supabase:
        st.error("🚨 Error Crítico: No hay conexión con la Base de Datos.")
        return

    # --- NAVEGACIÓN (5 Pestañas) ---
    tab_dash, tab_editor, tab_bancos, tab_updates, tab_users = st.tabs([
        "📊 Dashboard Global", 
        "🛠️ Editor de Registros",  # <--- NUEVA HERRAMIENTA
        "🏦 Gestión Bancos", 
        "🔔 Noticias (Updates)", 
        "👥 Usuarios (RRHH)"
    ])

    # ==========================================
    # PESTAÑA 1: DASHBOARD GLOBAL
    # ==========================================
    with tab_dash:
        total_bancos, df_hoy = obtener_kpis_globales()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏦 Base de Datos", f"{total_bancos}", delta="Bancos Activos")
        
        if not df_hoy.empty:
            total_notas = len(df_hoy)
            ventas = len(df_hoy[df_hoy['result'].str.contains('Completed', case=False, na=False)])
            agentes_on = df_hoy['agent'].nunique()
            tasa = (ventas / total_notas * 100) if total_notas > 0 else 0
            
            col2.metric("📞 Llamadas Totales", total_notas, delta="Equipo Hoy")
            col3.metric("🏆 Ventas (Completed)", ventas, delta=f"{tasa:.1f}% Conv.")
            col4.metric("👨‍💼 Agentes Activos", agentes_on, delta="Online")
        else:
            col2.metric("📞 Llamadas Totales", 0)
            col3.metric("🏆 Ventas (Completed)", 0)
            col4.metric("👨‍💼 Agentes Activos", 0)

        st.markdown("---")

        if not df_hoy.empty:
            c_g1, c_g2 = st.columns([2, 1])
            with c_g1:
                st.subheader("📈 Ranking de Actividad")
                chart_rank = alt.Chart(df_hoy).mark_bar(cornerRadius=5).encode(
                    x=alt.X('count()', title='Notas'),
                    y=alt.Y('agent', sort='-x', title=None),
                    color=alt.Color('agent', legend=None),
                    tooltip=['agent', 'count()']
                ).properties(height=300)
                st.altair_chart(chart_rank, use_container_width=True)
            
            with c_g2:
                st.subheader("🥧 Resultados")
                base = alt.Chart(df_hoy).encode(theta=alt.Theta("count()", stack=True))
                pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                    color=alt.Color("result", legend=None),
                    tooltip=["result", "count()"],
                    order=alt.Order("count()", sort="descending")
                )
                st.altair_chart(pie, use_container_width=True)
        else:
            st.info("😴 Sin actividad registrada hoy (Horario ET).")

        # Zona de Descargas (Auditoría)
        with st.expander("📥 Exportar Datos (Auditoría & Excel)", expanded=False):
            c_d1, c_d2, c_agente = st.columns([1, 1, 2])
            with c_d1: f_inicio = st.date_input("Desde:", value=datetime.now().replace(day=1))
            with c_d2: f_fin = st.date_input("Hasta:", value=datetime.now())
            with c_agente:
                opciones_agentes = ["🏢 REPORTE GLOBAL (Todos)"] + obtener_lista_agentes()
                agente_filtro = st.selectbox("Seleccionar Objetivo:", opciones_agentes)
            
            if st.button("🔄 Generar CSV Auditoría", use_container_width=True):
                try:
                    query = supabase.table("Logs").select("*").gte("created_at", f"{f_inicio}").lte("created_at", f"{f_fin}T23:59:59").order("created_at", desc=True)
                    if "REPORTE GLOBAL" in agente_filtro: query = query.neq("agent", "test")
                    else: query = query.eq("agent", agente_filtro)
                    
                    res = query.execute()
                    df_ex = pd.DataFrame(res.data)
                    
                    if not df_ex.empty:
                        csv = df_ex.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("💾 Descargar CSV", csv, "auditoria.csv", "text/csv", type='primary')
                        st.success(f"Generado: {len(df_ex)} registros.")
                    else:
                        st.warning("No hay datos.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # ==========================================
    # PESTAÑA 2: EDITOR DE REGISTROS (QUIRÓFANO)
    # ==========================================
    with tab_editor:
        st.subheader("🛠️ Corrección de Logs (Quirófano)")
        st.caption("Busca por ID o Nombre para corregir errores en registros existentes.")
        
        # 1. Buscador
        search_log = st.text_input("🔍 Buscar registro:", placeholder="Escribe el ID Córdoba (ej: 12345) o Nombre Cliente").strip()
        
        if search_log:
            try:
                # Lógica Inteligente: Si es número busca ID, si es texto busca Nombre
                if search_log.isdigit():
                    res_search = supabase.table("Logs").select("*").eq("cordoba_id", search_log).order("created_at", desc=True).execute()
                else:
                    res_search = supabase.table("Logs").select("*").ilike("customer", f"%{search_log}%").order("created_at", desc=True).execute()
                
                logs_found = res_search.data
                
                if logs_found:
                    st.success(f"✅ Se encontraron {len(logs_found)} registros.")
                    
                    # Selector visual para elegir cuál editar
                    opciones_logs = {log['id']: f"{log['created_at'][:10]} | {log['customer']} | {log['result']} (Agente: {log['agent']})" for log in logs_found}
                    selected_log_id = st.selectbox("Selecciona el registro a editar:", list(opciones_logs.keys()), format_func=lambda x: opciones_logs[x])
                    
                    # Cargar datos del seleccionado
                    log_data = next(l for l in logs_found if l['id'] == selected_log_id)
                    
                    st.divider()
                    
                    # Formulario de Edición
                    with st.form("edit_log_form"):
                        st.markdown(f"**Editando ID Interno:** `{log_data['id']}` | **Agente:** `{log_data['agent']}`")
                        
                        col_e1, col_e2 = st.columns(2)
                        new_customer = col_e1.text_input("Nombre Cliente", value=log_data['customer'])
                        new_cordoba_id = col_e2.text_input("Cordoba ID", value=log_data['cordoba_id'])
                        
                        col_e3, col_e4 = st.columns(2)
                        new_affiliate = col_e3.text_input("Afiliado", value=log_data['affiliate'] or "")
                        
                        # Lista de resultados posibles para facilitar la corrección
                        posibles_resultados = ["Completed", "No Answer", "Voicemail", "Callback", "Not Interested", "Not Completed"]
                        # Asegurar que el valor actual esté en la lista
                        idx_res = 0
                        current_res_simple = log_data['result'].split(" - ")[0] if log_data['result'] else "Completed"
                        if current_res_simple in posibles_resultados:
                            idx_res = posibles_resultados.index(current_res_simple)
                            
                        new_result_base = col_e4.selectbox("Resultado", posibles_resultados, index=idx_res)
                        
                        new_comments = st.text_area("Notas / Comentarios", value=log_data['comments'] or "")
                        
                        st.markdown("---")
                        if st.form_submit_button("💾 Guardar Corrección", type="primary"):
                            # Actualizar en Supabase
                            supabase.table("Logs").update({
                                "customer": new_customer,
                                "cordoba_id": new_cordoba_id,
                                "affiliate": new_affiliate,
                                "result": new_result_base, # Ojo: aquí simplificamos el resultado si lo cambian
                                "comments": new_comments
                            }).eq("id", selected_log_id).execute()
                            
                            st.success("✅ Registro corregido exitosamente.")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.warning("No se encontraron registros con ese criterio.")
                    
            except Exception as e:
                st.error(f"Error buscando: {e}")

    # ==========================================
    # PESTAÑA 3: GESTIÓN DE BANCOS
    # ==========================================
    with tab_bancos:
        st.subheader("🏦 Editor de Acreedores")
        c_bk1, c_bk2 = st.columns([1, 2])
        
        with c_bk1:
            with st.container(border=True):
                st.markdown("##### ➕ Nuevo Banco")
                new_bk_name = st.text_input("Nombre Entidad")
                new_bk_abrev = st.text_input("Abreviación")
                if st.button("Guardar Banco", type="primary", use_container_width=True):
                    if new_bk_name:
                        supabase.table("Creditors").insert({"name": new_bk_name, "abreviation": new_bk_abrev}).execute()
                        st.toast("✅ Banco agregado")
                        time.sleep(1)
                        st.rerun()
        
        with c_bk2:
            st.markdown("##### 🔍 Buscar y Editar")
            q_bk = st.text_input("Buscar banco...", label_visibility="collapsed")
            if q_bk:
                res = supabase.table("Creditors").select("*").ilike("name", f"%{q_bk}%").limit(10).execute()
                df_bk = pd.DataFrame(res.data)
                if not df_bk.empty:
                    bk_opts = {r['id']: f"{r['name']} ({r['abreviation']})" for _, r in df_bk.iterrows()}
                    sel_bk = st.selectbox("Editar:", list(bk_opts.keys()), format_func=lambda x: bk_opts[x])
                    
                    row = df_bk[df_bk['id'] == sel_bk].iloc[0]
                    with st.form("edit_bk"):
                        e_bk_n = st.text_input("Nombre", row['name'])
                        e_bk_a = st.text_input("Abrev.", row['abreviation'])
                        if st.form_submit_button("Actualizar"):
                            supabase.table("Creditors").update({"name": e_bk_n, "abreviation": e_bk_a}).eq("id", sel_bk).execute()
                            st.rerun()
                    
                    if st.button("🗑️ Eliminar Banco"):
                        supabase.table("Creditors").delete().eq("id", sel_bk).execute()
                        st.rerun()

    # ==========================================
    # PESTAÑA 4: NOTICIAS (UPDATES)
    # ==========================================
    with tab_updates:
        st.subheader("📢 Centro de Comunicaciones")
        c_up1, c_up2 = st.columns([1, 2])
        
        with c_up1:
            with st.container(border=True):
                st.markdown("##### ➕ Publicar")
                up_tit = st.text_input("Título")
                up_msg = st.text_area("Mensaje")
                up_cat = st.selectbox("Tipo", ["Info", "Warning", "Critical"])
                if st.button("Publicar", use_container_width=True):
                    if up_tit and up_msg:
                        supabase.table("Updates").insert({
                            "date": datetime.now().strftime('%Y-%m-%d'),
                            "title": up_tit, "message": up_msg, "category": up_cat, "active": True
                        }).execute()
                        st.rerun()

        with c_up2:
            st.markdown("##### 📡 Activas")
            ups = supabase.table("Updates").select("*").eq("active", True).order("date", desc=True).execute().data
            for u in ups:
                color = "#ff4444" if u['category'] == 'Critical' else "#ffbb33" if u['category'] == 'Warning' else "#0099CC"
                st.markdown(f"<div style='border-left:5px solid {color};padding:10px;background:#f9f9f9;margin-bottom:5px'><b>{u['title']}</b><br>{u['message']}</div>", unsafe_allow_html=True)
                if st.button("🔕 Archivar", key=f"del_{u['id']}"):
                    supabase.table("Updates").update({"active": False}).eq("id", u['id']).execute()
                    st.rerun()

    # ==========================================
    # PESTAÑA 5: USUARIOS
    # ==========================================
    with tab_users:
        st.subheader("👥 Gestión de Usuarios")
        c_u1, c_u2 = st.columns([1, 2])
        
        with c_u1:
            with st.container(border=True):
                st.markdown("##### ➕ Nuevo Usuario")
                nu_user = st.text_input("Usuario")
                nu_name = st.text_input("Nombre Real")
                nu_pass = st.text_input("Password", type="password")
                nu_role = st.selectbox("Rol", ["Agent", "Admin"])
                if st.button("Crear", type="primary", use_container_width=True):
                    if nu_user and nu_pass:
                        hashed = bcrypt.hashpw(nu_pass.encode(), bcrypt.gensalt()).decode()
                        supabase.table("Users").insert({"username": nu_user, "name": nu_name, "password": hashed, "role": nu_role}).execute()
                        st.success("Creado!")
                        time.sleep(1)
                        st.rerun()

        with c_u2:
            users = supabase.table("Users").select("*").order("id").execute().data
            if users:
                df_u = pd.DataFrame(users)
                st.dataframe(df_u[['username', 'name', 'role', 'active']], hide_index=True, use_container_width=True)
                
                u_opts = {u['id']: f"{u['name']} ({u['username']})" for u in users}
                sel_u = st.selectbox("Modificar:", list(u_opts.keys()), format_func=lambda x: u_opts[x])
                u_dat = next(u for u in users if u['id'] == sel_u)
                
                with st.form("edit_user"):
                    eu_n = st.text_input("Nombre", u_dat['name'])
                    eu_r = st.selectbox("Rol", ["Agent", "Admin"], index=0 if u_dat['role'] == "Agent" else 1)
                    eu_a = st.checkbox("Activo", u_dat['active'])
                    eu_p = st.text_input("Nueva Pass (Opcional)", type="password")
                    
                    if st.form_submit_button("Actualizar"):
                        upd = {"name": eu_n, "role": eu_r, "active": eu_a}
                        if eu_p: upd["password"] = bcrypt.hashpw(eu_p.encode(), bcrypt.gensalt()).decode()
                        supabase.table("Users").update(upd).eq("id", sel_u).execute()
                        st.rerun()

if __name__ == "__main__":
    show()
