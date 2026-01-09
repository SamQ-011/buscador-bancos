import re
import pandas as pd
from datetime import datetime
import pytz
from sqlalchemy import text

# --- Validaciones y Helpers ---

def sanitize_text_for_db(text_str: str) -> str:
    if not text_str: return ""
    return re.sub(r'\b\d{3,}\b', '[####]', text_str)

# --- Lectura de Datos (SELECT) ---

def fetch_agent_history(conn, username: str, limit: int = 15):
    if not conn: return pd.DataFrame()
    # Usamos pd.read_sql o conn.query, asumimos conn es st.connection
    query = 'SELECT created_at, result, cordoba_id FROM "Logs" WHERE agent ILIKE :u ORDER BY created_at DESC LIMIT :l'
    df = conn.query(query, params={"u": username, "l": limit}, ttl=0)
    
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
        # Formateamos para la vista
        df['Date'] = df['created_at'].dt.tz_convert('US/Eastern').dt.strftime('%m/%d/%Y %I:%M %p')
        return df[['Date', 'result', 'cordoba_id']]
    return pd.DataFrame()

def fetch_affiliates_list(conn):
    """Obtiene lista de afiliados."""
    if not conn: return []
    try:
        df = conn.query('SELECT name FROM "Affiliates" ORDER BY name', ttl=3600)
        return df['name'].tolist()
    except Exception as e:
        print(f"Error fetching affiliates: {e}")
        return []

# --- Escritura de Datos (INSERT) ---

def commit_log(conn, payload: dict):
    comments_safe = sanitize_text_for_db(payload.get('comments', ''))
    
    # Extraemos el nuevo campo (default None si no viene)
    transfer_status = payload.get('transfer_status', None)

    sql = """
        INSERT INTO "Logs" (
            created_at, user_id, agent, customer, cordoba_id, 
            result, comments, affiliate, info_until, client_language, 
            transfer_status
        )
        VALUES (
            :created_at, :uid, :agent, NULL, :cid, 
            :res, :comm, :aff, :info, :lang, 
            :trans
        )
    """
    params = {
        "created_at": datetime.now(pytz.utc), 
        "uid": int(payload['user_id']),
        "agent": payload['username'],
        "cid": payload['cordoba_id'],
        "res": payload['result'],
        "comm": comments_safe,
        "aff": payload['affiliate'],
        "info": payload['info_until'],
        "lang": payload['client_language'],
        "trans": transfer_status  # <--- Nuevo parámetro
    }
    
    # Ejecutamos transacción de escritura
    with conn.session as session:
        session.execute(text(sql), params)
        session.commit()
    return True