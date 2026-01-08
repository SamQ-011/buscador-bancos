import re
import pandas as pd
import streamlit as st
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection
import services.search_service as service

def show():
    conn = get_db_connection()
    
    # 1. Obtener datos (Ahora es tiempo real, pasamos 'conn')
    df_creditors = service.fetch_creditor_master_list(conn)
    
    # 2. Header
    col_header, col_metric = st.columns([3, 1])
    with col_header:
        st.title("🏦 Buscador de Acreedores")
        st.caption("Validación y normalización de códigos bancarios.")
        
    with col_metric:
        count = len(df_creditors) if not df_creditors.empty else 0
        st.metric("DB Activa", count)

    # 3. Indexación
    if not df_creditors.empty:
        code_map = dict(zip(df_creditors['Normalized_Code'], df_creditors['Code']))
        name_map = dict(zip(df_creditors['Normalized_Code'], df_creditors['Name']))
    else:
        code_map, name_map = {}, {}

    # 4. Tabs
    tab_manual, tab_batch = st.tabs(["🔎 Búsqueda Manual", "🚀 Proceso por Lotes"])

    # --- Tab Manual (Sin cambios mayores) ---
    with tab_manual:
        c1, _ = st.columns([3, 1])
        query = c1.text_input("Buscar Código o Nombre:", placeholder="Ej: AMEX", label_visibility="collapsed")
        
        if query and not df_creditors.empty:
            normalized_query = re.sub(r'\s+', ' ', query.strip().upper())
            mask = (df_creditors['Normalized_Code'].str.contains(normalized_query, regex=False)) | \
                   (df_creditors['Name'].str.upper().str.contains(normalized_query, regex=False))
            results = df_creditors[mask]

            if not results.empty:
                st.success(f"{len(results)} coincidencias.")
                st.dataframe(results[['Code', 'Name']], use_container_width=True, hide_index=True)
            else:
                st.warning(f"No hay resultados para '{query}'")

    # --- Tab Lotes (AQUÍ ESTÁ TU REQUERIMIENTO) ---
    with tab_batch:
        st.info("Pega tu lista de acreedores desde Excel.")
        raw_input = st.text_area("Datos de entrada:", height=150, key="batch_input")
        
        # Guardamos el estado del procesamiento
        if "batch_results" not in st.session_state: st.session_state.batch_results = None

        if st.button("⚡ Procesar Lote", type="primary"):
            if raw_input:
                lines = raw_input.split('\n')
                valid_hits = []
                unknowns = []

                for line in lines:
                    clean_line = line.strip()
                    if not clean_line: continue
                    
                    parsed_code = service.sanitize_input(clean_line).upper()
                    if parsed_code in service.IGNORED_TOKENS or len(parsed_code) < 2:
                        continue

                    if parsed_code in code_map:
                        valid_hits.append({
                            "Input": parsed_code,
                            "DB Code": code_map[parsed_code],
                            "Entity Name": name_map[parsed_code]
                        })
                    else:
                        if parsed_code not in unknowns: # Evitar duplicados visuales
                            unknowns.append(parsed_code)
                
                # Guardamos en sesión para que no se borre al tocar otros botones
                st.session_state.batch_results = {"valid": valid_hits, "unknown": unknowns}

        # MOSTRAR RESULTADOS (Si existen en memoria)
        if st.session_state.batch_results:
            res = st.session_state.batch_results
            st.divider()
            c_hits, c_miss = st.columns([2, 1.2])
            
            with c_hits:
                if res["valid"]:
                    st.success(f"✅ {len(res['valid'])} Encontrados")
                    st.dataframe(pd.DataFrame(res["valid"]), hide_index=True, use_container_width=True)
                else:
                    st.info("Esperando códigos válidos...")

            with c_miss:
                if res["unknown"]:
                    st.error(f"⚠️ {len(res['unknown'])} No Encontrados")
                    st.write("Estos códigos no están en el sistema:")
                    
                    # Mostramos lista simple
                    st.code("\n".join(res["unknown"]), language="text")
                    
                    st.markdown("#### 🚨 Reportar Faltantes")
                    st.caption("Ayúdanos a mejorar. Ingresa el ID para que el Admin lo revise.")
                    
                    # --- TU PEDIDO: Input Cordoba + Botón Guardar ---
                    cid_report = st.text_input("Cordoba ID:", placeholder="Ej: 118...", key="cid_rep")
                    
                    if st.button("💾 Reportar Desconocidos", type="secondary", use_container_width=True):
                        if cid_report:
                            if service.report_unknown_codes(conn, res["unknown"], cid_report):
                                st.toast("Reporte enviado al Admin!", icon="📨")
                                # Opcional: Limpiar unknowns después de reportar
                                # st.session_state.batch_results["unknown"] = []
                                # st.rerun()
                        else:
                            st.warning("⚠️ Ingresa el Cordoba ID antes de reportar.")
                else:
                    st.success("Todo limpio. No hay desconocidos.")

if __name__ == "__main__":
    show()