import streamlit as st
import pandas as pd
import re

# --- CARGA DE DATOS ---
@st.cache_data(ttl=3600)
def cargar_datos_bancos():
    try:
        conn = st.connection("supabase", type="sql")
        query = 'SELECT abreviation, name FROM "Creditors" ORDER BY name ASC'
        df = conn.query(query, ttl=3600)
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Código", "name": "Acreedor"})
            df = df.dropna(subset=['Acreedor'])
            df.insert(0, "Tipo", "🏦")
        return df
    except Exception as e:
        st.error(f"Error conectando a Creditors: {e}")
        return pd.DataFrame()

def limpiar_linea_texto(linea):
    """
    Limpia la línea pegada para quedarse solo con el nombre/código.
    """
    # 1. Si hay tabulaciones, cortamos ahí
    parts = re.split(r'\t', linea)
    if len(parts) > 1:
        return parts[0].strip()
    
    # 2. Si no, buscamos dónde empieza un número largo o el signo $
    match = re.search(r'(\d|\$)', linea)
    if match:
        return linea[:match.start()].strip()
    
    return linea.strip()

def show():
    st.title("🔍 Buscador Inteligente")
    st.caption("Búsqueda individual o análisis masivo de tablas.")

    # Cargar DB
    df_db = cargar_datos_bancos()

    # Pestañas
    tab_single, tab_batch = st.tabs(["🔎 Búsqueda Manual", "🚀 Pegar Tabla (Batch)"])

    # ==========================================
    # MODO 1: BÚSQUEDA MANUAL
    # ==========================================
    with tab_single:
        st.write("")
        busqueda = st.text_input(
            "Escribe nombre o código:", 
            placeholder="Ej: CHASE...",
            label_visibility="collapsed"
        ).strip()

        if busqueda:
            if not df_db.empty:
                m1 = df_db['Código'].str.contains(busqueda, case=False, na=False)
                m2 = df_db['Acreedor'].str.contains(busqueda, case=False, na=False)
                resultados = df_db[m1 | m2]

                if not resultados.empty:
                    st.success(f"✅ {len(resultados)} coincidencias.")
                    st.dataframe(resultados, use_container_width=True, hide_index=True)
                else:
                    st.warning("🤷‍♂️ No encontré nada.")
            else:
                st.error("Base de datos vacía o error de carga.")
    
    # ==========================================
    # MODO 2: PEGADO MASIVO (BATCH)
    # ==========================================
    with tab_batch:
        st.info("💡 Pega la tabla del CRM. El sistema limpiará los números de cuenta automáticamente.")
        
        texto_pegado = st.text_area(
            "Pega tu tabla aquí:", 
            height=150, 
            placeholder="Creditor   Account #   Balance\nLENDMARK   25601...    $10,000\nDISCOVERCARD ..."
        )
        
        if st.button("⚡ Analizar Lote", type="primary"):
            if not texto_pegado:
                st.warning("El campo está vacío.")
            else:
                lineas = texto_pegado.split('\n')
                encontrados = []
                no_encontrados = []

                st.divider()
                barra = st.progress(0)
                
                for i, linea in enumerate(lineas):
                    linea_clean = linea.strip()
                    
                    if not linea_clean or "Creditor" in linea_clean or "Account" in linea_clean or "Debt Balance" in linea_clean:
                        continue
                    
                    nombre_buscado = limpiar_linea_texto(linea_clean)
                    if len(nombre_buscado) < 2: continue 

                    if not df_db.empty:
                        # Búsqueda doble (Código o Nombre)
                        m1 = df_db['Código'].str.contains(nombre_buscado, case=False, regex=False, na=False)
                        m2 = df_db['Acreedor'].str.contains(nombre_buscado, case=False, regex=False, na=False)
                        match = df_db[m1 | m2]
                        
                        if not match.empty:
                            mejor_match = match.iloc[0]
                            # --- AQUÍ CAMBIAMOS LAS COLUMNAS ---
                            encontrados.append({
                                "Code": mejor_match['Código'],  # Columna 1
                                "Name": mejor_match['Acreedor'] # Columna 2
                            })
                        else:
                            no_encontrados.append(nombre_buscado)
                    
                    barra.progress((i + 1) / len(lineas))

                # --- MOSTRAR RESULTADOS ---
                c_ok, c_fail = st.columns(2)
                
                with c_ok:
                    if encontrados:
                        st.success(f"✅ {len(encontrados)} Identificados")
                        df_res = pd.DataFrame(encontrados)
                        
                        # Mostramos solo Code y Name, limpio
                        st.dataframe(
                            df_res, 
                            hide_index=True, 
                            use_container_width=True,
                            column_config={
                                "Code": st.column_config.TextColumn("Code", help="ID para copiar al CRM", width="medium"),
                                "Name": st.column_config.TextColumn("Name", width="large")
                            }
                        )
                    else:
                        st.info("Ninguno identificado automáticamente.")

                with c_fail:
                    if no_encontrados:
                        st.error(f"⚠️ {len(no_encontrados)} Sin Coincidencia")
                        st.write("Revisar manual:")
                        for n in no_encontrados:
                            st.code(n, language="text")
                    else:
                        if encontrados:
                            st.balloons()
                            st.caption("¡Perfecto! Todos reconocidos.")

if __name__ == "__main__":
    show()
