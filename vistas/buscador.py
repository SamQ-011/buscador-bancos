import re
import pandas as pd
import streamlit as st
import services.search_service as service  # Importamos tu servicio

def show():
    # 1. Obtener datos desde el servicio
    df_creditors = service.fetch_creditor_master_list()
    
    # 2. Header & Métricas
    col_header, col_metric = st.columns([3, 1])
    with col_header:
        st.title("🏦 Buscador de Acreedores")
        st.caption("Validación y normalización de códigos bancarios.")
        
    with col_metric:
        count = len(df_creditors) if not df_creditors.empty else 0
        st.metric("Total Creditors", count, delta="DB Activa" if count > 0 else "Offline")

    # 3. Preparar Mapas de Búsqueda (Indexación)
    if not df_creditors.empty:
        code_map = dict(zip(df_creditors['Normalized_Code'], df_creditors['Code']))
        name_map = dict(zip(df_creditors['Normalized_Code'], df_creditors['Name']))
    else:
        code_map, name_map = {}, {}

    # 4. Tabs de la Interfaz
    tab_manual, tab_batch = st.tabs(["🔎 Búsqueda Manual", "🚀 Proceso por Lotes"])

    # --- Tab Manual ---
    with tab_manual:
        c1, _ = st.columns([3, 1])
        query = c1.text_input("Buscar Código o Nombre:", placeholder="Ej: AMEX", label_visibility="collapsed")
        
        if query and not df_creditors.empty:
            normalized_query = re.sub(r'\s+', ' ', query.strip().upper())
            
            # Búsqueda difusa usando Pandas
            mask = (df_creditors['Normalized_Code'].str.contains(normalized_query, regex=False)) | \
                   (df_creditors['Name'].str.upper().str.contains(normalized_query, regex=False))
            
            results = df_creditors[mask]

            if not results.empty:
                st.success(f"{len(results)} coincidencias encontradas.")
                st.dataframe(results[['Code', 'Name']], use_container_width=True, hide_index=True)
            else:
                st.warning(f"No hay resultados para '{query}'")

    # --- Tab Lotes ---
    with tab_batch:
        st.info("Validador Masivo: Pega tu lista desde Excel.")
        raw_input = st.text_area("Datos de entrada:", height=150)
        
        if st.button("⚡ Procesar Lote", type="primary"):
            if not raw_input: return

            lines = raw_input.split('\n')
            valid_hits = []
            unknowns = []

            for line in lines:
                clean_line = line.strip()
                if not clean_line: continue
                
                # Usamos la función de limpieza del servicio
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
                    unknowns.append(parsed_code)

            st.divider()
            c_hits, c_miss = st.columns([2, 1])
            
            with c_hits:
                if valid_hits:
                    st.success(f"✅ {len(valid_hits)} Códigos Validados")
                    st.dataframe(pd.DataFrame(valid_hits), hide_index=True, use_container_width=True)
                else:
                    st.info("No se encontraron códigos válidos.")

            with c_miss:
                if unknowns:
                    st.error(f"⚠️ {len(unknowns)} Desconocidos")
                    st.text_area("Revisión:", value="\n".join(unknowns), height=200)

if __name__ == "__main__":
    show()