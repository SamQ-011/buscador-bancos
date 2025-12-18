import streamlit as st
import pandas as pd
import re

# --- CARGA DE DATOS OPTIMIZADA ---
@st.cache_data(ttl=3600)
def cargar_datos_bancos():
    try:
        conn = st.connection("supabase", type="sql")
        # Traemos solo lo necesario
        query = 'SELECT abreviation, name FROM "Creditors" ORDER BY abreviation ASC'
        df = conn.query(query, ttl=3600)
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Código", "name": "Acreedor"})
            df = df.dropna(subset=['Código']) # Si no tiene código, no nos sirve para buscar
            # Normalizamos a mayúsculas para búsquedas exactas
            df['Código_Upper'] = df['Código'].str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Error conectando a Creditors: {e}")
        return pd.DataFrame()

def limpiar_linea_texto(linea):
    """
    Limpia agresivamente para aislar el CÓDIGO del banco.
    Ej: "CHASE    12345 $500" -> "CHASE"
    """
    # 1. Separar por tabulaciones o múltiples espacios
    parts = re.split(r'\t|\s{2,}', linea)
    texto_base = parts[0].strip()
    
    # 2. Cortar si aparece un número largo (cuenta) o símbolo de dinero
    # Busca donde empieza el primer dígito o el signo $
    match = re.search(r'(\d|\$)', texto_base)
    if match:
        texto_base = texto_base[:match.start()].strip()
    
    return texto_base

def show():
    st.title("🔍 Buscador de Bancos")
    st.caption("Búsqueda estricta por Código (Abreviation).")

    # Cargar DB
    df_db = cargar_datos_bancos()
    
    # Crear un Diccionario Maestro para búsqueda ultra-rápida y exacta
    # Estructura: {'CHASE': 'JPMORGAN CHASE...', 'AMEX': 'AMERICAN EXPRESS...'}
    if not df_db.empty:
        # Creamos un mapa: CLAVE (Mayúscula) -> VALOR (Nombre Real)
        mapa_bancos = dict(zip(df_db['Código_Upper'], df_db['Acreedor']))
        lista_codigos_reales = dict(zip(df_db['Código_Upper'], df_db['Código'])) # Para mantener el casing original (ej: Chase vs CHASE)
    else:
        mapa_bancos = {}
        lista_codigos_reales = {}

    # Pestañas
    tab_single, tab_batch = st.tabs(["🔎 Manual", "🚀 Por Lote (Batch)"])

    # ==========================================
    # MODO 1: BÚSQUEDA MANUAL (Filtrado estricto)
    # ==========================================
    with tab_single:
        c1, c2 = st.columns([3, 1])
        with c1:
            busqueda = st.text_input(
                "Escribe el Código:", 
                placeholder="Ej: AMEX",
                label_visibility="collapsed"
            ).strip().upper()
        
        with c2:
            st.write("") # Espaciador

        if busqueda:
            if not df_db.empty:
                # LÓGICA: Buscar SOLO en la columna Código
                # Usamos startswith para que sea cómodo (si escribes 'AME' sale 'AMEX')
                # Pero NO buscamos en el Nombre.
                mask = df_db['Código_Upper'].str.startswith(busqueda)
                resultados = df_db[mask].copy()

                if not resultados.empty:
                    st.success(f"✅ {len(resultados)} coincidencias de código.")
                    # Mostramos tabla limpia (sin la columna auxiliar Upper)
                    st.dataframe(
                        resultados[['Código', 'Acreedor']], 
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    st.warning(f"⛔ No existe ningún código que empiece con '{busqueda}'")
            else:
                st.error("Base de datos vacía.")
    
    # ==========================================
    # MODO 2: PEGADO MASIVO (Exact Match)
    # ==========================================
    with tab_batch:
        st.info("💡 Pega la lista del CRM. El sistema buscará coincidencias EXACTAS en los Códigos.")
        
        texto_pegado = st.text_area(
            "Pega tu tabla aquí:", 
            height=150, 
            
        )
        
        if st.button("⚡ Analizar Lote", type="primary"):
            if not texto_pegado:
                st.warning("El campo está vacío.")
            else:
                lineas = texto_pegado.split('\n')
                encontrados = []
                no_encontrados = []

                # Procesamiento
                for linea in lineas:
                    linea_raw = linea.strip()
                    if not linea_raw: continue
                    
                    # 1. Limpieza
                    codigo_input = limpiar_linea_texto(linea_raw).upper()
                    
                    # Filtros anti-basura (cabeceras comunes)
                    if codigo_input in ["CREDITOR", "ACCOUNT", "BALANCE", "DEBT"]:
                        continue
                        
                    if len(codigo_input) < 2: continue 

                    # 2. BÚSQUEDA EXACTA EN EL DICCIONARIO (O(1) Speed)
                    # Verifica si el código limpio existe EXACTAMENTE en la base de datos
                    if codigo_input in mapa_bancos:
                        nombre_real = mapa_bancos[codigo_input]
                        codigo_real = lista_codigos_reales[codigo_input]
                        
                        encontrados.append({
                            "Input": codigo_input, # Lo que detectamos
                            "Código BD": codigo_real, # Como está en la BD
                            "Acreedor": nombre_real
                        })
                    else:
                        no_encontrados.append(codigo_input)

                # --- RESULTADOS ---
                st.divider()
                c_ok, c_fail = st.columns([2, 1])
                
                with c_ok:
                    if encontrados:
                        st.success(f"✅ {len(encontrados)} Reconocidos (Exactos)")
                        df_res = pd.DataFrame(encontrados)
                        st.dataframe(
                            df_res[["Código BD", "Acreedor"]], 
                            hide_index=True, 
                            use_container_width=True
                        )
                    else:
                        st.info("Ningún código exacto encontrado.")

                with c_fail:
                    if no_encontrados:
                        st.error(f"⚠️ {len(no_encontrados)} Desconocidos")
                        st.caption("Estos códigos no existen en la columna 'abreviation':")
                        # Mostramos lista simple para copiar
                        st.text_area("No encontrados:", value="\n".join(no_encontrados), height=200)

if __name__ == "__main__":
    show()