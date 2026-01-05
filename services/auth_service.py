import bcrypt
from sqlalchemy import text
import pandas as pd

def login_user(conn, username, password):
    """Verifica credenciales. Retorna dict usuario o None."""
    if not conn: return None
    try:
        user = get_user_by_username(conn, username)
        if not user: return None

        stored_hash = user['password']
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return user
        return None
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

def get_user_by_username(conn, username):
    """Busca un usuario por username sin validar password (para cookies)."""
    if not conn: return None
    try:
        query = 'SELECT * FROM "Users" WHERE username = :u'
        df = conn.query(query, params={"u": username}, ttl=0)
        
        if df.empty: return None
        return df.iloc[0].to_dict() # Retornamos diccionario para consistencia
    except Exception as e:
        print(f"User Fetch Error: {e}")
        return None

def update_credentials(conn, username, current_pass, new_pass):
    """Actualiza la contraseña."""
    if not conn: return False, "DB offline"
    try:
        user = get_user_by_username(conn, username)
        if not user: return False, "Usuario no encontrado"
            
        stored_hash = user['password']
        if not bcrypt.checkpw(current_pass.encode('utf-8'), stored_hash.encode('utf-8')):
            return False, "Contraseña actual incorrecta"

        new_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update transaccional
        with conn.session as s:
            s.execute(
                text('UPDATE "Users" SET password = :p WHERE username = :u'), 
                {"p": new_hash, "u": username}
            )
            s.commit()
            
        return True, "Contraseña actualizada correctamente"
    except Exception as e:
        return False, f"Error: {e}"