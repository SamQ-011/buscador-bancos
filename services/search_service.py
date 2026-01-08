import re
import pandas as pd
import streamlit as st
from sqlalchemy import text  # Necesario para inserts seguros

# --- Configuración ---
IGNORED_TOKENS = {"CREDITOR", "ACCOUNT", "BALANCE", "DEBT", "AMOUNT", "TOTAL"}

# 1. Función de Búsqueda (SIN CACHÉ para tiempo real)
def fetch_creditor_master_list(conn) -> pd.DataFrame:
    """
    Obtiene la lista maestra de acreedores en TIEMPO REAL.
    """
    if not conn: return pd.DataFrame()

    try:
        # Consultamos directo a la BD sin guardarlo en memoria (cache)
        query = 'SELECT abreviation, name FROM "Creditors" ORDER BY abreviation LIMIT 10000'
        df = conn.query(query, ttl=0) # ttl=0 asegura datos frescos siempre
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Code", "name": "Name"})
            df = df.dropna(subset=['Code'])
            # Normalizamos para búsqueda
            df['Normalized_Code'] = df['Code'].astype(str).str.strip().str.upper().str.replace(r'\s+', ' ', regex=True)
        return df
    except Exception as e:
        print(f"[DataFetch Error] Creditors: {e}") 
        return pd.DataFrame()

# 2. Función de Limpieza
def sanitize_input(raw_text: str) -> str:
    """Limpia el texto pegado desde Excel/CRM."""
    parts = re.split(r'\t|\s{2,}', raw_text)
    base_text = parts[0].strip()
    
    match = re.search(r'(\d|\$)', base_text)
    if match:
        base_text = base_text[:match.start()].strip()
        
    return re.sub(r'\s+', ' ', base_text)

# 3. Función para Guardar Reportes (NUEVO)
def report_unknown_codes(conn, code_list: list, cordoba_id: str):
    """Guarda los códigos no encontrados en la tabla Search_Misses."""
    if not code_list or not conn: return False

    try:
        # Preparamos los valores para insertar varios de golpe
        values = [{"abbr": code, "cid": cordoba_id} for code in code_list]
        
        sql = """
            INSERT INTO "Search_Misses" (abreviation, cordoba_id) 
            VALUES (:abbr, :cid)
        """
        
        with conn.session as session:
            session.execute(text(sql), values)
            session.commit()
        return True
    except Exception as e:
        st.error(f"Error reportando: {e}")
        return False