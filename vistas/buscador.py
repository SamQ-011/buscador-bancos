import streamlit as st
import pandas as pd
import re
from supabase import create_client

# --- 1. CONEXIÓN SEGURA ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["connections"]["supabase"]["URL"]
        key = st.secrets["connections"]["supabase"]["KEY"]
        return create_client(url, key)
    except:
        return None

# --- 2. CARGA DE DATOS (API + CACHÉ) ---
@st.cache_data(ttl=3600) 
def cargar_datos_bancos():
    supabase = init_connection()
    if not supabase: return pd.DataFrame()

    try:
        # Traemos TODOS los bancos (Límite 10,000)
        res = supabase.table("Creditors")\
            .select("abreviation, name")\
            .order("abreviation")\
            .limit(10000)\
            .execute()
        
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Código", "name": "Acreedor"})
            df = df.dropna(subset=['Código']) 
            
            # Limpieza profunda
            df['Código_Upper'] = df['Código'].astype(str).str.strip().str.upper().str.replace(r'\s+', ' ', regex=True)
            
        return df
    except Exception as e:
        print(f"Error cargando bancos: {e}") 
        return pd.DataFrame()

def limpiar_linea_texto(linea):
    """
    Limpia para aislar el CÓDIGO del banco.
    """
    parts = re.split(r'\t|\s{2,}', linea)
    texto_base = parts[0].strip()
    match = re.search(r'(\d|\$)', texto_base)
    if match:
        texto_base = texto_base[:match.start()].strip()
    texto_base = re.sub(r'\s+', ' ', texto_base)
    return texto_base

def show():
    # Cargar DB primero para tener el conteo
    df_db = cargar_datos_bancos()
    
    # --- MEJORA VISUAL: TÍTULO + CONTADOR ---
    col_titulo, col_contador = st.columns([3, 1])
    
    with col_titulo:
        st.title("🏦 Buscador de Acreedores")
        st.caption("Validación de códigos bancarios (Manual o Masiva).")
        
    with col_contador:
        if not df_db.empty:
            # Mostramos el contador como una métrica elegante alineada a la derecha
            st.metric("Total Acreedores Registrados", len(df_db), delta="Activos")
        else:
            st.warning("⚠️ Sin conexión")
    # ----------------------------------------

    
    if not df_db.empty:
        # Optimización: Diccionarios para búsqueda rápida
        mapa_bancos = dict(zip(df_db['Código_Upper'], df_db['Acreedor']))
        lista_codigos_reales = dict(zip(df_db['Código_Upper'], df_db['Código']))
    else:
        st.error("No se pudo cargar la base de datos de acreedores o está vacía.")
        mapa_bancos = {}
        lista_codigos_reales = {}

    # Pestañas
    tab_single, tab_batch = st.tabs(["🔎 Búsqueda Manual", "🚀 Busqueda por Bloque"])

    # ==========================================
    # MODO 1: BÚSQUEDA MANUAL
    # ==========================================
    with tab_single:
        c1, c2 = st.columns([3, 1])
        with c1:
            busqueda_raw = st.text_input(
                "Escribe el Código o Nombre:", 
                placeholder="Ej: AMEX, CHASE...",
                label_visibility="collapsed"
            )
        
        st.write("")

        if busqueda_raw and not df_db.empty:
            # Normalizamos lo que escribe el usuario
            busqueda = re.sub(r'\s+', ' ', busqueda_raw.strip().upper())

            # Búsqueda flexible (CONTIENE)
            mask = (df_db['Código_Upper'].str.contains(busqueda, regex=False)) | \
                   (df_db['Acreedor'].str.upper().str.contains(busqueda, regex=False))
            
            resultados = df_db[mask].copy()

            if not resultados.empty:
                st.success(f"✅ {len(resultados)} coincidencias.")
                st.dataframe(
                    resultados[['Código', 'Acreedor']], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning(f"⛔ No se encontraron resultados para '{busqueda_raw}'")
    
    # ==========================================
    # MODO 2: PEGADO MASIVO
    # ==========================================
    with tab_batch:
        st.info("💡 Pega una lista desde Excel/CRM para validar si los códigos existen.")
        
        texto_pegado = st.text_area("Pega tu lista aquí:", height=150)
        
        if st.button("⚡ Analizar Lote", type="primary"):
            if not texto_pegado:
                st.warning("El campo está vacío.")
            else:
                lineas = texto_pegado.split('\n')
                encontrados = []
                no_encontrados = []

                for linea in lineas:
                    linea_raw = linea.strip()
                    if not linea_raw: continue
                    
                    # Limpieza
                    codigo_input = limpiar_linea_texto(linea_raw).upper()
                    
                    # Filtros anti-basura
                    if codigo_input in ["CREDITOR", "ACCOUNT", "BALANCE", "DEBT", "AMOUNT"]:
                        continue
                    if len(codigo_input) < 2: continue 

                    # BÚSQUEDA EXACTA
                    if codigo_input in mapa_bancos:
                        encontrados.append({
                            "Input": codigo_input,
                            "Código BD": lista_codigos_reales[codigo_input],
                            "Acreedor": mapa_bancos[codigo_input]
                        })
                    else:
                        no_encontrados.append(codigo_input)

                # --- RESULTADOS ---
                st.divider()
                c_ok, c_fail = st.columns([2, 1])
                
                with c_ok:
                    if encontrados:
                        st.success(f"✅ {len(encontrados)} Códigos Válidos")
                        st.dataframe(pd.DataFrame(encontrados)[["Código BD", "Acreedor"]], hide_index=True, use_container_width=True)
                    else:
                        st.info("Ningún código válido encontrado.")

                with c_fail:
                    if no_encontrados:
                        st.error(f"⚠️ {len(no_encontrados)} Desconocidos")
                        st.caption("No existen en sistema:")
                        st.text_area("Copiar para revisar:", value="\n".join(no_encontrados), height=200)

if __name__ == "__main__":
    show()

