import re
import pandas as pd
import streamlit as st
from conexion import get_db_connection

# --- Configuración ---
CACHE_TTL = 3600  # 1 hora
IGNORED_TOKENS = {"CREDITOR", "ACCOUNT", "BALANCE", "DEBT", "AMOUNT"}

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_creditor_master_list() -> pd.DataFrame:
    """
    Obtiene y cachea la lista maestra de acreedores desde la DB.
    Retorna DataFrame normalizado con ['Code', 'Name', 'Normalized_Code'].
    """
    conn = get_db_connection()
    if not conn: return pd.DataFrame()

    try:
        query = 'SELECT abreviation, name FROM "Creditors" ORDER BY abreviation LIMIT 10000'
        df = conn.query(query, ttl=CACHE_TTL)
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Code", "name": "Name"})
            df = df.dropna(subset=['Code'])
            # Pre-computar mayúsculas para búsquedas rápidas
            df['Normalized_Code'] = df['Code'].astype(str).str.strip().str.upper().str.replace(r'\s+', ' ', regex=True)
        return df
    except Exception as e:
        print(f"[DataFetch Error] Creditors: {e}") 
        return pd.DataFrame()

def sanitize_input(raw_text: str) -> str:
    """Limpia el texto pegado desde Excel/CRM para extraer códigos."""
    # Dividir por tabs o espacios dobles
    parts = re.split(r'\t|\s{2,}', raw_text)
    base_text = parts[0].strip()
    
    # Remover montos que a veces se pegan por error
    match = re.search(r'(\d|\$)', base_text)
    if match:
        base_text = base_text[:match.start()].strip()
        
    return re.sub(r'\s+', ' ', base_text)