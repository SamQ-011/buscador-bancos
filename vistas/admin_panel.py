import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from supabase import create_client

# --- 1. CONEXIÓN A SUPABASE (BLINDADA) ---
@st.cache_resource
def init_connection():
    try:
        # Intento 1: Buscar dentro de [connections.supabase]
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            url = st.secrets["connections"]["supabase"]["URL"]
            key = st.secrets["connections"]["supabase"]["KEY"]
        # Intento 2: Buscar en la raíz
        else:
            url = st.secrets["URL"]
            key = st.secrets["KEY"]
            
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Error de configuración de Secretos: {e}")
        return None

supabase = init_connection()

# --- 2. FUNCIONES DE DATOS (BACKEND) ---
def obtener_kpis_globales():
    """Calcula las métricas de toda la operación en tiempo real"""
    try:
        if not supabase: return 0, pd.DataFrame()

        # A. Total de Bancos (Tabla 'Creditors')
        res_bancos = supabase.table("Creditors").select("name", count="exact", head=True).execute()
        total_bancos = res_bancos.count
        
        # B. Actividad de HOY (Tabla 'Logs')
        hoy_str = datetime.now().strftime('%Y-%m-%d')
        
        # Usamos 'created_at' que es la que tiene tu tabla Logs
        res_logs = supabase.table("Logs").select("*").gte("created_at", hoy_str).execute()
        df_logs = pd.DataFrame(res_logs.data)
        
        return total_bancos, df_logs

    except Exception as e:
        # Si falla, devolvemos 0 para no romper la app
        return 0, pd.DataFrame()

# --- 3. INTERFAZ PRINCIPAL ---
def show():
    st.title("🎛️ Torre de Control")
    st.caption("Panel de Administración Centralizado")

    if not supabase:
        st.warning("No se pudo conectar a la base de datos.")
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
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏦 Base de Datos", f"{total_bancos}", delta="Bancos Activos")
        
        if not df_hoy.empty:
            total_notas = len(df_hoy)
            ventas = len(df_hoy[df_hoy['result'].str.contains('Completed', case=False, na=False)])
            agentes_on = df_hoy['agent'].nunique()
            
            col2.metric("📞 Llamadas Totales", total_notas, delta="Equipo Hoy")
            col3.metric("🏆 Ventas (Completed)", ventas, delta="Equipo Hoy")
            col4.metric("👨‍💼 Agentes Activos", agentes_on, delta="Online")
        else:
            col2.metric("📞 Llamadas Totales", 0)
            col3.metric("🏆 Ventas (Completed)", 0)
            col4.metric("👨‍💼 Agentes Activos", 0)

        st.markdown("---")

        if not df_hoy.empty:
            c_g1, c_g2 = st.columns([2, 1])
            
            with c_g1:
                st.subheader("📈 Ranking de Actividad (Hoy)")
                chart_rank = alt.Chart(df_hoy).mark_bar(
                    cornerRadius=5, 
                    color='#0F52BA'
                ).encode(
                    x=alt.X('count()', title='Cantidad de Notas'),
                    y=alt.Y('agent', sort='-x', title='Agente'),
                    tooltip=['agent', 'count()']
                ).properties(height=300)
                
                text_rank = chart_rank.mark_text(dx=3, align='left').encode(text='count()')
                st.altair_chart(chart_rank + text_rank, use_container_width=True)
            
            with c_g2:
                st.subheader("🥧 Resultados Globales")
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
            st.info("😴 Sin actividad registrada el día de hoy.")

    # ==========================================
    # PESTAÑA 2: GESTIÓN DE BANCOS
    # ==========================================
    with tab_bancos:
        st.subheader("🏦 Editor de Acreedores (Creditors)")
        col_izq, col_der = st.columns([1, 2])
        
        # --- A. CREAR NUEVO (CON DEBUGGING) ---
        with col_izq:
            with st.container(border=True):
                st.markdown("##### ➕ Agregar Manual")
                # Usamos key para que no se borre al recargar si falla
                new_name = st.text_input("Nombre Entidad", key="new_bank_name")
                new_abrev = st.text_input("Abreviación (Opcional)", key="new_bank_abrev")
                
                if st.button("Guardar Banco", type="primary", use_container_width=True):
                    if new_name:
                        try:
                            # 1. Intentamos insertar
                            response = supabase.table("Creditors").insert({
                                "name": new_name, 
                                "abreviation": new_abrev
                            }).execute()
                            
                            # 2. Verificamos si realmente se guardó
                            if response.data:
                                st.success(f"✅ {new_name} guardado correctamente.")
                                # Esperamos un segundo para que el usuario lea el mensaje antes de recargar
                                st.rerun()
                            else:
                                st.error("⚠️ La base de datos recibió la orden pero no devolvió datos.")
                                st.code(f"Respuesta DB: {response}", language="json")
                                st.info("Pista: Revisa si tienes activas las políticas RLS (Row Level Security).")

                        except Exception as e:
                            st.error(f"❌ Error Crítico: {e}")
                            # Diagnóstico inteligente de errores comunes
                            err_msg = str(e).lower()
                            if "violates not-null constraint" in err_msg and "id" in err_msg:
                                st.warning("💡 DIAGNÓSTICO: Tu columna 'id' en Supabase no es Autoincremental.")
                                st.info("Solución: Ve a Supabase > Table Editor > Creditors. Edita la columna 'id' y marca la casilla 'Is Identity' o cambia el tipo a 'int8 generated by default as identity'.")
                            elif "permission denied" in err_msg:
                                st.warning("💡 DIAGNÓSTICO: Problema de permisos (RLS).")
                    else:
                        st.warning("El nombre es obligatorio.")
        
        # --- B. BUSCAR Y EDITAR (SE MANTIENE IGUAL) ---
        with col_der:
             # ... (El resto del código de búsqueda que ya tenías está bien) ...
             # Si quieres te lo copio, pero esa parte funcionaba bien.
            search_q = st.text_input("🔍 Buscar banco para editar...", placeholder="Ej: Chase")
            
            if search_q:
                try:
                    res = supabase.table("Creditors").select("*")\
                        .ilike("name", f"%{search_q}%").limit(20).execute()
                    df_bancos = pd.DataFrame(res.data)
                    
                    if not df_bancos.empty:
                        st.dataframe(df_bancos[['id', 'name', 'abreviation']], hide_index=True, use_container_width=True)
                        st.divider()
                        
                        lista_ids = df_bancos['id'].tolist()
                        mapa_nombres = {row['id']: f"{row['name']}" for _, row in df_bancos.iterrows()}
                        
                        id_sel = st.selectbox("Selecciona cuál editar:", lista_ids, format_func=lambda x: mapa_nombres.get(x))
                        row_sel = df_bancos[df_bancos['id'] == id_sel].iloc[0]
                        
                        with st.form("form_edit_bank"):
                            c_e1, c_e2 = st.columns(2)
                            ed_name = c_e1.text_input("Nombre", value=row_sel['name'])
                            ed_abrev = c_e2.text_input("Abreviación", value=row_sel['abreviation'] or "")
                            
                            if st.form_submit_button("💾 Actualizar Datos"):
                                supabase.table("Creditors").update({
                                    "name": ed_name, "abreviation": ed_abrev
                                }).eq("id", id_sel).execute()
                                st.success("✅ Actualizado.")
                                st.rerun()

                        with st.expander("🗑️ Zona de Peligro"):
                            st.warning(f"¿Borrar '{row_sel['name']}'?")
                            if st.button("Sí, Eliminar", key="btn_del_bank"):
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
                            st.success("Publicado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.toast("⚠️ Faltan datos.")

        # --- B. LISTA DE AVISOS ACTIVOS ---
        with c_up_list:
            st.markdown("##### 📡 En Circulación (Ordenado por Fecha)")
            try:
                res_up = supabase.table("Updates").select("*")\
                    .eq("active", True)\
                    .order("date", desc=True)\
                    .execute()
                
                noticias = res_up.data
                
                if noticias:
                    for noti in noticias:
                        cat_raw = noti.get('category')
                        cat_str = str(cat_raw).upper() if cat_raw else "INFO"

                        icono = "ℹ️"
                        if cat_str == 'WARNING': icono = "⚠️"
                        if cat_str == 'CRITICAL': icono = "🚨"
                        
                        fecha_corta = noti['date']
                        
                        with st.expander(f"{icono} {noti['title']} | 📅 {fecha_corta}"):
                            st.markdown(f"**{cat_str} MESSAGE:**")
                            st.write(noti['message'])
                            st.markdown("---")
                            if st.button("🔕 Desactivar", key=f"arch_{noti['id']}"):
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
        
        # Estructura: Izquierda (Crear) - Derecha (Lista y Edición)
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
                            # Insertamos en tabla "Users" respetando mayúscula
                            supabase.table("Users").insert({
                                "username": n_user,
                                "name": n_name,
                                "password": n_pass,
                                "role": n_role,
                                "active": True
                            }).execute()
                            st.success(f"✅ Usuario {n_user} creado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al crear: {e}")
                    else:
                        st.warning("⚠️ Todos los campos son obligatorios.")

        # --- B. LISTA Y EDICIÓN ---
        with c_u_list:
            st.markdown("##### 📋 Nómina de Empleados")
            try:
                # Traemos todos los usuarios ordenados por ID
                res_users = supabase.table("Users").select("*").order("id").execute()
                df_users = pd.DataFrame(res_users.data)

                if not df_users.empty:
                    # Mostramos tabla resumen (sin password por seguridad)
                    st.dataframe(
                        df_users[['id', 'username', 'name', 'role', 'active']], 
                        hide_index=True, 
                        use_container_width=True
                    )
                    
                    st.divider()
                    st.markdown("##### 🛠️ Modificar Perfil")
                    
                    # Selector de Usuario
                    user_ids = df_users['id'].tolist()
                    user_map = {row['id']: f"{row['name']} ({row['username']})" for _, row in df_users.iterrows()}
                    
                    sel_uid = st.selectbox("Selecciona empleado:", user_ids, format_func=lambda x: user_map.get(x))
                    
                    # Obtenemos datos actuales
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
                            # Solo actualizamos pass si escribió algo
                            if e_pass:
                                update_data["password"] = e_pass
                            
                            try:
                                supabase.table("Users").update(update_data).eq("id", sel_uid).execute()
                                st.success("✅ Perfil actualizado.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar: {e}")
                else:
                    st.info("No hay usuarios registrados.")
            
            except Exception as e:

                st.error(f"Error cargando usuarios: {e}")
