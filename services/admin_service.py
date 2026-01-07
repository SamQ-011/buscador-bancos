import bcrypt
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text

# --- Helpers ---

def run_transaction(conn, query_str: str, params: dict = None):
    """Ejecuta operaciones de escritura (INSERT, UPDATE, DELETE)."""
    try:
        with conn.session as session:
            session.execute(text(query_str), params if params else {})
            session.commit()
        return True
    except Exception as e:
        print(f"Transaction Error: {e}")
        return False

# --- Dashboard & KPIs ---

def fetch_global_kpis(conn):
    # ... (tú código existente de KPIs) ...
    # (Déjalo tal cual está)
    if not conn: return 0, pd.DataFrame()
    try:
        df_count = conn.query('SELECT COUNT(*) as total FROM "Creditors"', ttl=0)
        total_bancos = df_count.iloc[0]['total'] if not df_count.empty else 0
        
        yesterday_utc = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        logs_query = 'SELECT * FROM "Logs" WHERE created_at >= :yesterday AND agent != \'test\''
        df_logs = conn.query(logs_query, params={"yesterday": yesterday_utc}, ttl=0)
            
        return total_bancos, df_logs
    except Exception as e:
        return 0, pd.DataFrame()

def fetch_live_feed(conn, limit=15):
    """Obtiene los registros más recientes con Nombres Reales y Cordoba ID."""
    if not conn: return pd.DataFrame()
    
    # Hacemos JOIN para obtener el nombre real del agente (U.name)
    query = """
        SELECT 
            L.created_at, 
            COALESCE(U.name, L.agent) as agent_real_name, 
            L.cordoba_id, 
            L.result, 
            L.affiliate 
        FROM "Logs" L
        LEFT JOIN "Users" U ON L.user_id = U.id
        WHERE L.agent != 'test'
        ORDER BY L.created_at DESC 
        LIMIT :limit
    """
    try:
        df = conn.query(query, params={"limit": limit}, ttl=0)
        
        if not df.empty:
            # Conversión de hora
            df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
            df['Time'] = df['created_at'].dt.tz_convert('US/Eastern').dt.strftime('%I:%M %p')
            
            # Devolvemos las columnas exactas que pediste
            return df[['Time', 'agent_real_name', 'cordoba_id', 'result', 'affiliate']]
            
    except Exception as e:
        print(f"Live Feed Error: {e}")
        
    return pd.DataFrame()

def fetch_agent_list(conn):
    try:
        df = conn.query('SELECT username FROM "Users" WHERE active = TRUE ORDER BY username', ttl=60)
        return df['username'].tolist()
    except:
        return []

def fetch_user_map(conn):
    try:
        df = conn.query('SELECT username, name FROM "Users"', ttl=600)
        return pd.Series(df.name.values, index=df.username).to_dict()
    except:
        return {}

def fetch_logs_for_export(conn, start_date, end_date, target_agent):
    """Obtiene los datos crudos para el reporte de Excel."""
    base_query = """
        SELECT * FROM "Logs" 
        WHERE created_at >= :start AND created_at <= :end
    """
    params = {
        "start": f"{start_date} 00:00:00",
        "end": f"{end_date} 23:59:59"
    }
    
    if "TODOS" not in target_agent:
        base_query += " AND agent ILIKE :target"
        params["target"] = target_agent
    else:
        base_query += " AND agent != 'test'"
    
    return conn.query(base_query + " ORDER BY created_at DESC", params=params, ttl=0)

# --- Gestión de Logs (Quirófano) ---

def fetch_log_by_cordoba_id(conn, cordoba_id):
    return conn.query('SELECT * FROM "Logs" WHERE cordoba_id = :cid', params={"cid": cordoba_id}, ttl=0)

def update_log_entry(conn, log_id, new_result, new_comments):
    sql = 'UPDATE "Logs" SET result = :res, comments = :comm WHERE id = :id'
    return run_transaction(conn, sql, {"res": new_result, "comm": new_comments, "id": log_id})

# --- Gestión de Bancos (Creditors) ---

def create_creditor(conn, name, abbreviation):
    sql = 'INSERT INTO "Creditors" (name, abreviation) VALUES (:name, :abbr)'
    return run_transaction(conn, sql, {"name": name, "abbr": abbreviation})

def search_creditors(conn, search_term):
    """
    Busca acreedores por Nombre O Abreviación.
    Aumentamos el LIMIT para permitir que el frontend reciba todos los datos.
    """
    # 1. Buscamos en ambas columnas (Nombre OR Abreviación)
    # 2. Subimos el LIMIT de 15 a 5000 para cubrir tus 2018 registros
    sql = """
        SELECT * FROM "Creditors" 
        WHERE name ILIKE :q OR abreviation ILIKE :q 
        ORDER BY name ASC 
        LIMIT 5000
    """
    
    # El % alrededor del término permite buscar coincidencias parciales
    return conn.query(sql, params={"q": f"%{search_term}%"}, ttl=0)
    
def update_creditor(conn, creditor_id, name, abbreviation):
    sql = 'UPDATE "Creditors" SET name = :n, abreviation = :a WHERE id = :id'
    return run_transaction(conn, sql, {"n": name, "a": abbreviation, "id": creditor_id})

def delete_creditor(conn, creditor_id):
    return run_transaction(conn, 'DELETE FROM "Creditors" WHERE id = :id', {"id": creditor_id})

# --- Gestión de Noticias (Updates) ---

def create_update(conn, title, message, category):
    sql = """
        INSERT INTO "Updates" (date, title, message, category, active) 
        VALUES (:date, :tit, :msg, :cat, TRUE)
    """
    params = {"date": datetime.now().strftime('%Y-%m-%d'), "tit": title, "msg": message, "cat": category}
    return run_transaction(conn, sql, params)

def fetch_active_updates(conn):
    return conn.query('SELECT * FROM "Updates" WHERE active = TRUE ORDER BY date DESC', ttl=0)

def archive_update(conn, update_id):
    return run_transaction(conn, 'UPDATE "Updates" SET active = FALSE WHERE id = :id', {"id": update_id})

# --- Gestión de Usuarios ---

def create_user(conn, username, name, password, role):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sql = """
        INSERT INTO "Users" (username, name, password, role, active) 
        VALUES (:u, :n, :p, :r, TRUE)
    """
    return run_transaction(conn, sql, {"u": username, "n": name, "p": hashed, "r": role})

def fetch_all_users(conn):
    return conn.query('SELECT * FROM "Users" ORDER BY username', ttl=0)

def update_user_profile(conn, user_id, name, role, active, new_password=None):
    sql = 'UPDATE "Users" SET name = :n, role = :r, active = :a'
    params = {"n": name, "r": role, "a": active, "id": user_id}
    
    if new_password:
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        sql += ', password = :p'
        params["p"] = hashed
    
    sql += ' WHERE id = :id'
    return run_transaction(conn, sql, params)
