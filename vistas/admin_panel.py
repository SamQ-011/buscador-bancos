import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, time as dt_time
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
    """Calcula las métricas de toda la operación en tiempo real (Filtrando 'test')"""
    try:
        if not supabase: return 0, pd.DataFrame()

        # A. Total de Bancos
        res_bancos = supabase.table("Creditors").select("name", count="exact", head=True).execute()
        total_bancos = res_bancos.count
        
        # B. Actividad de HOY (Filtrando usuario 'test')
        hoy_str = datetime.now().strftime('%Y-%m-%d')
        
        # Traemos logs de hoy QUE NO SEAN de 'test'
        res_logs = supabase.table("Logs").select("*")\
            .gte("created_at", hoy_str)\
            .neq("agent", "test")\
            .execute()
            
        df_logs = pd.DataFrame(res_logs.data)
        
        return total_bancos, df_logs

    except Exception as e:
        return 0, pd.DataFrame()

def obtener_lista_agentes():
    """Trae la lista de usuarios activos para el filtro de reporte"""
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

    # --- NAVEGACIÓN ---
    tab_dash, tab_bancos, tab_updates, tab_users = st.tabs([
        "📊 Dashboard Global", 
        "🏦 Gestión Bancos", 
        "🔔 Noticias (Updates)", 
        "👥 Usuarios (RRHH)"
    ])

    # ==========================================
    # PESTAÑA 1: DASHBOARD GLOBAL
    # ==========================================
    with tab_dash:
        total_bancos, df_hoy = obtener_kpis_globales()
        
        # TARJETAS DE MÉTRICAS (KPIs)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏦 Base de Datos", f"{total_bancos}", delta="Bancos Activos")
        
        if not df_hoy.empty:
            total_notas = len(df_hoy)
            # Filtro flexible para detectar "Completed" o "WC Completed"
            ventas = len(df_hoy[df_hoy['result'].str.contains('Completed', case=False, na=False)])
            agentes_on = df_hoy['agent'].nunique()
            
            # Tasa de conversión simple
            tasa = (ventas / total_notas * 100) if total_notas > 0 else 0
            
            col2.metric("📞 Llamadas Totales", total_notas, delta="Equipo Hoy")
            col3.metric("🏆 Ventas (Completed)", ventas, delta=f"{tasa:.1f}% Conv.")
            col4.metric("👨‍💼 Agentes Activos", agentes_on, delta="Online")
        else:
            col2.metric("📞 Llamadas Totales", 0)
            col3.metric("🏆 Ventas (Completed)", 0)
            col4.metric("👨‍💼 Agentes Activos", 0)

        st.markdown("---")

        # GRÁFICOS
        if not df_hoy.empty:
            c_g1, c_g2 = st.columns([2, 1])
            
            with c_g1:
                st.subheader("📈 Ranking de Actividad")
                chart_rank = alt.Chart(df_hoy).mark_bar(cornerRadius=5).encode(
                    x=alt.X('count()', title='Notas Generadas'),
                    y=alt.Y('agent', sort='-x', title=None),
                    color=alt.Color('agent', legend=None, scale=alt.Scale(scheme='blues')),
                    tooltip=['agent', 'count()']
                ).properties(height=300)
                
                text_rank = chart_rank.mark_text(dx=3, align='left').encode(text='count()')
                st.altair_chart(chart_rank + text_rank, use_container_width=True)
            
            with c_g2:
                st.subheader("🥧 Resultados")
                base = alt.Chart(df_hoy).encode(theta=alt.Theta("count()", stack=True))
                pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                    color=alt.Color("result", legend=None),
                    tooltip=["result", "count()"],
                    order=alt.Order("count()", sort="descending")
                )
                text = base.mark_text(radius=120).encode(
                    text=alt.Text("count()"),
                    order=alt.Order("count()", sort="descending"),
                    color=alt.value("black") 
                )
                st.altair_chart(pie + text, use_container_width=True)
        else:
            st.info("😴 Sin actividad registrada el día de hoy (excluyendo pruebas).")

        st.markdown("---")
        
        # ==========================================
        # 📥 ZONA DE DESCARGAS (REPORTING AVANZADO)
        # ==========================================
        with st.expander("📥 Exportar Datos (Auditoría & Excel)", expanded=False):
            st.markdown("##### ⚙️ Configuración del Reporte")
            
            # 1. Filtros de Fecha y Agente
            c_d1, c_d2, c_agente = st.columns([1, 1, 2])
            
            with c_d1:
                f_inicio = st.date_input("Desde:", value=datetime.now().replace(day=1))
            with c_d2:
                f_fin = st.date_input("Hasta:", value=datetime.now())
            
            with c_agente:
                # Cargamos lista de agentes real desde BD
                lista_raw = obtener_lista_agentes()
                opciones_agentes = ["🏢 REPORTE GLOBAL (Todos)"] + lista_raw
                agente_filtro = st.selectbox("Seleccionar Objetivo:", opciones_agentes)
            
            # 2. Lógica de Conversión (Cacheada para velocidad)
            @st.cache_data(ttl=60, show_spinner=False)
            def convertir_df_a_csv(dataframe):
                return dataframe.to_csv(index=False).encode('utf-8-sig')

            st.write("") # Espacio
            
            # 3. Botón de Procesamiento
            if st.button("🔄 Generar Archivo", type="secondary", use_container_width=True):
                try:
                    # Construcción de la Query Dinámica
                    query = supabase.table("Logs").select("*")\
                        .gte("created_at", f"{f_inicio}T00:00:00")\
                        .lte("created_at", f"{f_fin}T23:59:59")\
                        .order("created_at", desc=True)
                    
                    # Lógica de Filtrado
                    es_global = "REPORTE GLOBAL" in agente_filtro
                    
                    if es_global:
                        # Si es global, traemos todo MENOS 'test'
                        query = query.neq("agent", "test")
                        nombre_archivo = f"Reporte_GLOBAL_{f_inicio}_{f_fin}.csv"
                    else:
                        # Si es un agente específico, filtramos solo por él
                        query = query.eq("agent", agente_filtro)
                        nombre_archivo = f"Auditoria_{agente_filtro}_{f_inicio}_{f_fin}.csv"

                    # Ejecutar Query
                    res_dl = query.execute()
                    df_export = pd.DataFrame(res_dl.data)

                    if not df_export.empty:
                        # Reordenar columnas para que el Excel se vea lógico
                        cols_order = ['created_at', 'agent', 'result', 'customer', 'cordoba_id', 'affiliate', 'client_language', 'info_until']
                        cols_existentes = [c for c in cols_order if c in df_export.columns]
                        cols_extra = [c for c in df_export.columns if c not in cols_order]
                        df_final = df_export[cols_existentes + cols_extra]

                        # Generar CSV en memoria
                        csv_data = convertir_df_a_csv(df_final)
                        
                        st.session_state['csv_buffer'] = csv_data
                        st.session_state['csv_name'] = nombre_archivo
                        
                        msg_exito = f"✅ Reporte Global: {len(df_final)} registros." if es_global else f"✅ Auditoría para {agente_filtro}: {len(df_final)} registros."
                        st.toast(msg_exito, icon="📊")
                    else:
                        st.warning("No se encontraron datos con esos filtros.")
                        if 'csv_buffer' in st.session_state: del st.session_state['csv_buffer']
                        
                except Exception as e:
                    st.error(f"Error generando reporte: {e}")

            # 4. Botón de Descarga Real (Aparece solo si hay datos listos)
            if 'csv_buffer' in st.session_state:
                st.download_button(
                    label=f"💾 Descargar: {st.session_state.get('csv_name', 'data.csv')}",
                    data=st.session_state['csv_buffer'],
                    file_name=st.session_state['csv_name'],
                    mime='text/csv',
                    type='primary',
                    use_container_width=True
                )

    # ==========================================
    # PESTAÑA 2: GESTIÓN DE BANCOS
    # ==========================================
    with tab_bancos:
        st.subheader("🏦 Editor de Acreedores")
        col_izq, col_der = st.columns([1, 2])
        
        # --- A. CREAR NUEVO ---
        with col_izq:
            with st.container(border=True):
                st.markdown("##### ➕ Agregar Manual")
                
                if "k_name" not in st.session_state: st.session_state.k_name = ""
                if "k_abrev" not in st.session_state: st.session_state.k_abrev = ""

                new_name = st.text_input("Nombre Entidad", key="k_name")
                new_abrev = st.text_input("Abreviación", key="k_abrev")
                
                if st.button("Guardar Banco", type="primary", use_container_width=True):
                    if new_name:
                        try:
                            supabase.table("Creditors").insert({
                                "name": new_name, 
                                "abreviation": new_abrev
                            }).execute()
                            
                            st.toast(f"✅ ¡{new_name} agregado!", icon="🏦")
                            
                            # Limpiar inputs
                            st.session_state.k_name = ""  
                            st.session_state.k_abrev = ""
                            time.sleep(0.5) 
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                    else:
                        st.warning("⚠️ El nombre es obligatorio.")
        
        # --- B. BUSCAR Y EDITAR ---
        with col_der:
            st.markdown("##### 🔍 Buscar y Editar")
            search_q = st.text_input("Escribe para buscar...", placeholder="Ej: Chase, Wells Fargo...", label_visibility="collapsed")
            
            if search_q:
                try:
                    res = supabase.table("Creditors").select("*")\
                        .ilike("name", f"%{search_q}%").limit(10).execute()
                    df_bancos = pd.DataFrame(res.data)
                    
                    if not df_bancos.empty:
                        # Selector para editar
                        opciones = {row['id']: f"{row['name']} ({row['abreviation'] or 'N/A'})" for _, row in df_bancos.iterrows()}
                        id_sel = st.selectbox("Selecciona para editar:", list(opciones.keys()), format_func=lambda x: opciones[x])
                        
                        row_sel = df_bancos[df_bancos['id'] == id_sel].iloc[0]
                        
                        st.divider()
                        with st.form("form_edit_bank"):
                            c_e1, c_e2 = st.columns(2)
                            ed_name = c_e1.text_input("Nombre", value=row_sel['name'])
                            ed_abrev = c_e2.text_input("Abreviación", value=row_sel['abreviation'] or "")
                            
                            if st.form_submit_button("💾 Actualizar Datos"):
                                supabase.table("Creditors").update({
                                    "name": ed_name, "abreviation": ed_abrev
                                }).eq("id", id_sel).execute()
                                st.success("✅ Actualizado correctamente.")
                                time.sleep(1)
                                st.rerun()

                        with st.expander("🗑️ Zona de Peligro"):
                            st.warning(f"¿Estás seguro de borrar '{row_sel['name']}'?")
                            if st.button("Sí, Eliminar Banco", type="primary"):
                                supabase.table("Creditors").delete().eq("id", id_sel).execute()
                                st.success("Eliminado.")
                                st.rerun()
                    else:
                        st.info("No se encontraron resultados.")
                except Exception as e:
                    st.error(f"Error en búsqueda: {e}")

    # ==========================================
    # PESTAÑA 3: NOTICIAS (UPDATES)
    # ==========================================
    with tab_updates:
        st.subheader("📢 Centro de Comunicaciones")
        c_up_new, c_up_list = st.columns([1, 2])
        
        # --- A. PUBLICAR NUEVA ---
        with c_up_new:
            with st.container(border=True):
                st.markdown("##### ✍️ Nuevo Aviso")
                u_title = st.text_input("Título (Corto)")
                u_msg = st.text_area("Mensaje", height=150)
                u_cat = st.selectbox("Prioridad", ["🔵 Info", "🟡 Warning", "🔴 Critical"])
                
                if st.button("🚀 Publicar", use_container_width=True):
                    if u_title and u_msg:
                        cat_db = "Info"
                        if "Warning" in u_cat: cat_db = "Warning"
                        if "Critical" in u_cat: cat_db = "Critical"
                        
                        try:
                            hoy_fecha = datetime.now().strftime('%Y-%m-%d')
                            supabase.table("Updates").insert({
                                "date": hoy_fecha, 
                                "title": u_title,
                                "message": u_msg,
                                "category": cat_db,
                                "active": True
                            }).execute()
                            st.toast("Publicado con éxito!", icon="📢")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("⚠️ Título y Mensaje requeridos.")

        # --- B. LISTA DE AVISOS ACTIVOS ---
        with c_up_list:
            st.markdown("##### 📡 En Circulación")
            try:
                res_up = supabase.table("Updates").select("*")\
                    .eq("active", True)\
                    .order("date", desc=True)\
                    .execute()
                
                noticias = res_up.data
                
                if noticias:
                    for noti in noticias:
                        cat_raw = noti.get('category', 'Info')
                        cat_str = str(cat_raw).upper()

                        # Colores y Iconos
                        if cat_str == 'CRITICAL': 
                            border_c = "#ff4444"
                            icon = "🚨"
                        elif cat_str == 'WARNING': 
                            border_c = "#ffbb33"
                            icon = "⚠️"
                        else: 
                            border_c = "#0099CC"
                            icon = "ℹ️"
                        
                        with st.container():
                            st.markdown(
                                f"""
                                <div style="border-left: 5px solid {border_c}; padding-left: 10px; margin-bottom: 10px; background-color: #f9f9f9; border-radius: 5px; padding: 10px;">
                                    <small>{noti['date']}</small><br>
                                    <strong>{icon} {noti['title']}</strong><br>
                                    {noti['message']}
                                </div>
                                """, unsafe_allow_html=True
                            )
                            if st.button("🔕 Archivar", key=f"arch_{noti['id']}"):
                                supabase.table("Updates").update({"active": False}).eq("id", noti['id']).execute()
                                st.rerun()
                else:
                    st.info("✅ No hay alertas activas.")
            except Exception as e:
                st.error(f"Error cargando noticias: {e}")

    # ==========================================
    # PESTAÑA 4: USUARIOS (RRHH)
    # ==========================================
    with tab_users:
        st.subheader("👥 Gestión de Usuarios (RRHH)")
        
        c_u_new, c_u_list = st.columns([1, 2])

        # --- A. CREAR NUEVO USUARIO ---
        with c_u_new:
            with st.container(border=True):
                st.markdown("##### ➕ Nuevo Agente")
                
                n_user = st.text_input("Username (Login)", placeholder="ej: jdoe")
                n_name = st.text_input("Nombre Real", placeholder="John Doe")
                n_pass = st.text_input("Contraseña Inicial", type="password")
                n_role = st.selectbox("Rol", ["Agent", "Admin"])
                
                if st.button("Crear Usuario", type="primary", use_container_width=True):
                    if n_user and n_name and n_pass:
                        try:
                            # --- ENCRIPTAR ---
                            hashed = bcrypt.hashpw(n_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                            supabase.table("Users").insert({
                                "username": n_user,
                                "name": n_name,
                                "password": hashed,
                                "role": n_role,
                                "active": True
                            }).execute()
                            
                            st.success(f"✅ Usuario {n_user} creado.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al crear: {e}")
                    else:
                        st.warning("⚠️ Todos los campos son obligatorios.")

        # --- B. LISTA Y EDICIÓN ---
        with c_u_list:
            st.markdown("##### 📋 Nómina de Empleados")
            try:
                res_users = supabase.table("Users").select("*").order("id").execute()
                df_users = pd.DataFrame(res_users.data)

                if not df_users.empty:
                    st.dataframe(
                        df_users[['id', 'username', 'name', 'role', 'active']], 
                        hide_index=True, 
                        use_container_width=True
                    )
                    
                    st.divider()
                    st.markdown("##### 🛠️ Modificar Perfil")
                    
                    user_ids = df_users['id'].tolist()
                    user_map = {row['id']: f"{row['name']} ({row['username']})" for _, row in df_users.iterrows()}
                    
                    sel_uid = st.selectbox("Selecciona empleado:", user_ids, format_func=lambda x: user_map.get(x))
                    
                    curr_user = df_users[df_users['id'] == sel_uid].iloc[0]
                    
                    with st.form("edit_user_form"):
                        c1, c2 = st.columns(2)
                        e_name = c1.text_input("Nombre Real", value=curr_user['name'])
                        e_role = c2.selectbox("Rol", ["Agent", "Admin"], index=0 if curr_user['role'] == "Agent" else 1)
                        
                        e_active = st.checkbox("✅ Usuario Activo (Acceso permitido)", value=curr_user['active'])
                        
                        st.markdown("**🔐 Cambiar Contraseña (Opcional)**")
                        e_pass = st.text_input("Nueva contraseña (dejar vacío para no cambiar)", type="password")
                        
                        if st.form_submit_button("💾 Guardar Cambios"):
                            update_data = {
                                "name": e_name,
                                "role": e_role,
                                "active": e_active
                            }
                            if e_pass:
                                hashed_new = bcrypt.hashpw(e_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                update_data["password"] = hashed_new
                            
                            try:
                                supabase.table("Users").update(update_data).eq("id", sel_uid).execute()
                                st.success("✅ Perfil actualizado.")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar: {e}")
                else:
                    st.info("No hay usuarios registrados.")
            
            except Exception as e:
                st.error(f"Error cargando usuarios: {e}")

if __name__ == "__main__":
    show()