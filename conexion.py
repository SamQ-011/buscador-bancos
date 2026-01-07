# vistas/conexion.py
import os
import streamlit as st

def get_db_connection():
    """
    Función centralizada para conectar a la base de datos.
    Soporta Docker (Variables de entorno).
    """
    try:
        # 1. Intenta leer la variable de entorno desde Docker
        db_url = os.getenv("DATABASE_URL")
        
        if db_url:
            # Si estamos en Docker, usamos la URL inyectada
            return st.connection("local_db", type="sql", url=db_url)
        else:
            # Si estamos en local (sin Docker), busca en .streamlit/secrets.toml
            # Busca automáticamente una sección [connections.local_db]
            return st.connection("local_db", type="sql")
            
    except Exception as e:
        print(f"⚠️ Error de conexión centralizado: {e}")
        return None