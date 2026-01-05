import pandas as pd
from conexion import get_db_connection

def fetch_updates() -> pd.DataFrame:
    """Obtiene los mensajes activos ordenados por fecha desde SQL."""
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    
    try:
        query = 'SELECT * FROM "Updates" WHERE active = TRUE ORDER BY date DESC'
        # TTL corto (60s) para ver actualizaciones casi en tiempo real
        return conn.query(query, ttl=60)
    except Exception as e:
        print(f"[Updates Fetch Error] {e}")
        return pd.DataFrame()