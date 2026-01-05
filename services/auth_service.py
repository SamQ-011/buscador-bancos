# services/auth_service.py
import bcrypt
from sqlalchemy import text
import pandas as pd

def login_user(conn, username, password):
    """
    Verifica credenciales. Retorna el objeto usuario si es correcto, o None.
    """
    if not conn: return None

    try:
        # Buscamos el usuario
        query = 'SELECT * FROM "Users" WHERE username = :u'
        df = conn.query(query, params={"u": username}, ttl=0)
        
        if df.empty:
            return None

        user = df.iloc[0]
        stored_hash = user['password']

        # Comparamos hash
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return user
            
        return None

    except Exception as e:
        print(f"Auth Service Error (Login): {e}")
        return None

def update_credentials(conn, username, current_pass, new_pass):
    """
    Actualiza la contraseña. Retorna (True, "Mensaje") o (False, "Error").
    """
    if not conn: return False, "Database unavailable."

    try:
        # 1. Obtener hash actual
        query = 'SELECT password FROM "Users" WHERE username = :u'
        df = conn.query(query, params={"u": username}, ttl=0)
        
        if df.empty:
            return False, "User record not found."
            
        stored_hash = df.iloc[0]['password']

        # 2. Verificar contraseña actual
        if not bcrypt.checkpw(current_pass.encode('utf-8'), stored_hash.encode('utf-8')):
            return False, "Current password incorrect."

        # 3. Generar nuevo hash
        new_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 4. Actualizar en BD
        update_sql = text('UPDATE "Users" SET password = :p WHERE username = :u')
        
        with conn.session as s:
            s.execute(update_sql, {"p": new_hash, "u": username})
            s.commit()
            
        return True, "Password updated successfully."

    except Exception as e:
        print(f"Auth Service Error (Update): {e}")
        return False, f"System Error: {e}"