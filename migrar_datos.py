import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# --- CONFIGURACIÓN DE CREDENCIALES ---

# 1. CONTRASEÑA SUPABASE
PASS_RAW = "franKlin-2016/cordobiTo"
PASS_SAFE = quote_plus(PASS_RAW)

# 2. DATOS DE CONEXIÓN A SUPABASE (Pooler IPv4)
SUPA_USER = "postgres.wqyalzwcqjgsbdohubcz"
SUPA_HOST = "aws-0-us-west-2.pooler.supabase.com"
SUPA_PORT = "5432"
SUPA_DB   = "postgres"

SUPABASE_URL = f"postgresql://{SUPA_USER}:{PASS_SAFE}@{SUPA_HOST}:{SUPA_PORT}/{SUPA_DB}"

# 3. DESTINO (Docker Local)
LOCAL_URL = "postgresql://admin:cordoba_secure_password_2025@localhost:5432/cordoba_workspace"

# --- ORDEN DE IMPORTACIÓN ---
TABLAS = ["Users", "Creditors", "Affiliates", "Updates", "Logs"]

def limpiar_tablas_locales(engine_local):
    """Borra el contenido local para evitar choques de IDs."""
    print("\n🧹 Limpiando base de datos local para importación limpia...")
    with engine_local.begin() as conn:
        # Orden inverso para respetar Foreign Keys (borrar hijos primero)
        conn.execute(text('TRUNCATE TABLE "Logs" CASCADE;'))
        conn.execute(text('TRUNCATE TABLE "Updates" CASCADE;'))
        conn.execute(text('TRUNCATE TABLE "Affiliates" CASCADE;'))
        conn.execute(text('TRUNCATE TABLE "Creditors" CASCADE;'))
        conn.execute(text('TRUNCATE TABLE "Users" CASCADE;'))
    print("✨ Base de datos local vaciada y lista.")

def procesar_dataframe(df, tabla):
    """Lógica de limpieza específica para cada tabla."""
    
    # 1. Corrección de Fechas (General)
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    if 'date' in df.columns: # Para Updates
        df['date'] = pd.to_datetime(df['date'])

    # 2. Correcciones Específicas
    if tabla == "Creditors":
        # Eliminar filas donde el nombre sea nulo
        len_antes = len(df)
        df = df.dropna(subset=['name'])
        df = df[df['name'] != '']
        if len(df) < len_antes:
            print(f"   ✂️ Eliminados {len_antes - len(df)} bancos sin nombre (basura).")

    if tabla == "Updates":
        if 'type' in df.columns:
            df = df.drop(columns=['type'])
            print("   ✂️ Columna obsoleta 'type' eliminada.")

    if tabla == "Affiliates":
        # Eliminar duplicados por nombre, conservando el primero
        len_antes = len(df)
        df = df.drop_duplicates(subset=['name'], keep='first')
        if len(df) < len_antes:
            print(f"   ✂️ Eliminados {len_antes - len(df)} afiliados duplicados.")
            
    return df

def migrar():
    print(f"🚀 Conectando sistemas...")
    
    try:
        engine_origen = create_engine(SUPABASE_URL)
        engine_destino = create_engine(LOCAL_URL)
        
        # Paso 0: Limpiar Local
        limpiar_tablas_locales(engine_destino)

        # Paso 1: Migración
        for tabla in TABLAS:
            print(f"\n📦 Tabla: {tabla}")
            try:
                # Extract
                df = pd.read_sql(f'SELECT * FROM "{tabla}"', engine_origen)
                print(f"   ⬇️ Descargados: {len(df)}")
                
                if df.empty: continue

                # Transform
                df = procesar_dataframe(df, tabla)

                # Load
                df.to_sql(tabla, engine_destino, if_exists='append', index=False, method='multi', chunksize=1000)
                print(f"   ✅ Insertados: {len(df)}")
                
                # Reset Sequence (Vital para que los nuevos IDs sigan la numeración)
                if 'id' in df.columns:
                    with engine_destino.begin() as conn:
                        sql_reset = f"""SELECT setval(pg_get_serial_sequence('"{tabla}"', 'id'), coalesce(max(id),0) + 1, false) FROM "{tabla}";"""
                        conn.execute(text(sql_reset))

            except Exception as e:
                print(f"   ❌ Error crítico en {tabla}: {e}")
                # Si falla Users, paramos porque Logs fallará sí o sí
                if tabla == "Users":
                    print("⚠️ Deteniendo migración por fallo en Usuarios.")
                    return

        print("\n🏆 --- MIGRACIÓN EXITOSA --- 🏆")
        print("Ahora tienes una copia exacta de Supabase en tu Docker.")

    except Exception as e:
        print(f"\n❌ Error General: {e}")

if __name__ == "__main__":
    migrar()
