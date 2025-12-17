import streamlit as st
import pandas as pd
import re

# --- CARGA DE DATOS (Mantenemos tu lógica eficiente) ---
@st.cache_data(ttl=3600)
def cargar_datos_bancos():
    try:
        conn = st.connection("supabase", type="sql")
        # Traemos todo. Si son 40k, esto deberá cambiar a futuro, pero por ahora funciona.
        query = 'SELECT abreviation, name FROM "Creditors" ORDER BY name ASC'
        df = conn.query(query, ttl=3600)
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Código", "name": "Acreedor"})
            df.insert(0, "Tipo", "🏦")
        return df
    except Exception as e:
        st.error(f"Error conectando a Creditors: {e}")
        return pd.DataFrame()

def limpiar_linea_texto(linea):
    """
    Intenta extraer solo el nombre del acreedor de una línea sucia.
    Ej: "CAPITAL ONE   517805898236   $2,544.00" -> "CAPITAL ONE"
    """
    # 1. Si hay tabulaciones (\t), partimos por ahí y tomamos el primero
    parts = re.split(r'\t', linea)
    if len(parts) > 1:
        return parts[0].strip()
    
    # 2. Si no hay tabs, buscamos cuando empieza un número largo (la cuenta) o un símbolo $
    # Regex: Busca el primer dígito o el signo $
    match = re.search(r'(\d|\$)', linea)
    if match:
        # Cortamos el texto hasta donde empieza el número/dinero
        return linea[:match.start()].strip()
    
    # 3. Si no encuentra nada raro, devuelve la línea tal cual
    return linea.strip()

def show():
    st.title("🔍 Buscador Inteligente")
    st.caption("Búsqueda individual o análisis masivo de tablas.")

    # Cargamos la DB en memoria
    df_db = cargar_datos_bancos()

    # --- PESTAÑAS PARA MODOS DE BÚSQUEDA ---
    tab_single, tab_batch = st.tabs(["🔎 Búsqueda Manual", "🚀 Pegar Tabla (Batch)"])

    # ==========================================
    # MODO 1: MANUAL (Lo que ya tenías)
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
    
    # ==========================================
    # MODO 2: PEGADO MASIVO (La Magia Nueva)
    # ==========================================
    with tab_batch:
        st.info("💡 Copia la tabla de deudas del CRM y pégala aquí abajo. El sistema limpiará los números de cuenta.")
        
        texto_pegado = st.text_area("Pega tu tabla aquí:", height=150, placeholder="Creditor   Account #   Balance\nLENDMARK   25601...    $10,000\nCapital One ...")
        
        if st.button("⚡ Analizar Lote", type="primary"):
            if not texto_pegado:
                st.warning("El campo está vacío.")
            else:
                # 1. Procesar texto línea por línea
                lineas = texto_pegado.split('\n')
                encontrados = []
                no_encontrados = []

                st.divider()
                
                barra = st.progress(0)
                
                for i, linea in enumerate(lineas):
                    linea_clean = linea.strip()
                    # Ignoramos cabeceras comunes o líneas vacías
                    if not linea_clean or "Creditor" in linea_clean or "Account" in linea_clean or "Debt Balance" in linea_clean:
                        continue
                    
                    # Limpiamos el nombre (quitamos números de cuenta y montos)
                    nombre_buscado = limpiar_linea_texto(linea_clean)
                    
                    if len(nombre_buscado) < 2: continue # Ignorar basura muy corta

                    # Buscamos en la DB (Búsqueda exacta o parcial)
                    # Usamos 'contains' para ser flexibles
                    match = df_db[df_db['Acreedor'].str.contains(nombre_buscado, case=False, regex=False)]
                    
                    if not match.empty:
                        # Tomamos el primer resultado (o el mejor)
                        mejor_match = match.iloc[0]
                        encontrados.append({
                            "Buscaste": nombre_buscado,
                            "Encontrado en DB": mejor_match['Acreedor'],
                            "Código": mejor_match['Código'],
                            "Confidence": "✅"
                        })
                    else:
                        no_encontrados.append(nombre_buscado)
                    
                    # Actualizar barrita visual
                    barra.progress((i + 1) / len(lineas))

                # --- RESULTADOS VISUALES ---
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
                                "Código": st.column_config.TextColumn("ID", help="Copia este ID")
                            }
                        )
                    else:
                        st.info("Ninguno identificado automáticamente.")

                with c_fail:
                    if no_encontrados:
                        st.error(f"⚠️ {len(no_encontrados)} Sin Coincidencia")
                        st.write("No encontramos estos en la base de datos (revisa manual):")
                        for n in no_encontrados:
                            st.code(n, language="text")
                    else:
                        if encontrados:
                            st.balloons()
                            st.caption("¡Perfecto! Todos reconocidos.")

if __name__ == "__main__":
    show()
