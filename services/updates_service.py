import pandas as pd
from sqlalchemy import text
from conexion import get_db_connection

def fetch_updates(conn) -> pd.DataFrame:
    """Obtiene los mensajes activos ordenados por fecha."""
    if not conn: return pd.DataFrame()
    
    try:
        # ttl=0 para asegurar que si lanzas una alerta, salga YA.
        query = 'SELECT * FROM "Updates" WHERE active = TRUE ORDER BY date DESC'
        return conn.query(query, ttl=0)
    except Exception as e:
        print(f"[Updates Fetch Error] {e}")
        return pd.DataFrame()

def fetch_read_ids(conn, username: str) -> list:
    """
    Retorna una lista simple de los IDs que este usuario ya marcó.
    Ejemplo: [1, 5, 8]
    """
    if not conn or not username: return []
    
    try:
        query = 'SELECT update_id FROM "Updates_Reads" WHERE username = :user'
        df = conn.query(query, params={"user": username}, ttl=0)
        
        if not df.empty:
            return df['update_id'].tolist()
        return []
    except Exception as e:
        print(f"[Reads Fetch Error] {e}")
        return []

def mark_as_read(conn, update_id: int, username: str) -> bool:
    """Escribe en la base de datos que el usuario leyó la noticia."""
    if not conn or not username: return False
    
    try:
        # ON CONFLICT DO NOTHING evita errores si le dan click doble muy rápido
        sql = """
            INSERT INTO "Updates_Reads" (update_id, username) 
            VALUES (:uid, :user)
            ON CONFLICT (update_id, username) DO NOTHING
        """
        with conn.session as session:
            session.execute(text(sql), {"uid": update_id, "user": username})
            session.commit()
        return True
    except Exception as e:
        print(f"[Mark Read Error] {e}")
        return False