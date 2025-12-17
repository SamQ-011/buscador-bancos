import streamlit as st
import pandas as pd
import re

# --- CARGA DE DATOS ---
@st.cache_data(ttl=3600)
def cargar_datos_bancos():
    try:
        conn = st.connection("supabase", type="sql")
        # Traemos datos. Si la base crece mucho (40k+), esto se optimizará después.
        query = 'SELECT abreviation, name FROM "Creditors" ORDER BY name ASC'
        df = conn.query(query, ttl=3600)
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Código", "name": "Acreedor"})
            # LIMPIEZA PREVENTIVA: Eliminamos bancos que no tengan nombre para evitar errores
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
    
    # 3. Si no hay nada raro, devolvemos tal cual
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
                # Búsqueda segura con na=False
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
                    
                    # Saltar cabeceras o líneas vacías
                    if not linea_clean or "Creditor" in linea_clean or "Account" in linea_clean or "Debt Balance" in linea_clean:
                        continue
                    
                    # Limpiar el nombre
                    nombre_buscado = limpiar_linea_texto(linea_clean)
                    
                    if len(nombre_buscado) < 2: continue # Ignorar basura corta

                    if not df_db.empty:
                        # --- LÓGICA CORREGIDA ---
                        # 1. Buscamos en CÓDIGO (para encontrar DISCOVERCARD)
                        m1 = df_db['Código'].str.contains(nombre_buscado, case=False, regex=False, na=False)
                        # 2. Buscamos en ACREEDOR (para encontrar Capital One)
                        m2 = df_db['Acreedor'].str.contains(nombre_buscado, case=False, regex=False, na=False)
                        
                        # Unimos resultados
                        match = df_db[m1 | m2]
                        
                        if not match.empty:
                            mejor_match = match.iloc[0]
                            encontrados.append({
                                "Buscaste": nombre_buscado,
                                "Encontrado en DB": mejor_match['Acreedor'],
                                "Código": mejor_match['Código'],
                                "Confidence": "✅"
                            })
                        else:
                            no_encontrados.append(nombre_buscado)
                    
                    # Actualizar barra
                    barra.progress((i + 1) / len(lineas))

                # --- MOSTRAR RESULTADOS ---
                c_ok, c_fail = st.columns(2)
                
                with c_ok:
                    if encontrados:
                        st.success(f"✅ {len(encontrados)} Identificados")
                        df_res = pd.DataFrame(encontrados)
                        st.dataframe(
                            df_res, 
                            hide_index=True, 
                            use_container_width=True,
                            column_config={
                                "Código": st.column_config.TextColumn("ID", help="Copia este ID para el CRM")
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


