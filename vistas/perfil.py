import streamlit as st
import time
from sqlalchemy import text 
import bcrypt

def actualizar_password_supabase(username, nueva_clave):
    try:
        conn = st.connection("supabase", type="sql")
        
        # Sentencia SQL con comillas para respetar mayúsculas
        query = 'UPDATE "Users" SET password = :p WHERE username = :u'
        
        # Ejecutamos la transacción
        with conn.session as s:
            # CORRECCIÓN AQUÍ: Usamos text() de sqlalchemy, no st.text()
            s.execute(text(query), {"p": nueva_clave, "u": username})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error técnico al actualizar: {e}")
        return False

def validar_clave_actual(username, clave_ingresada):
    try:
        conn = st.connection("supabase", type="sql")
        # 1. Traemos el hash de la BD (NO comparamos en SQL)
        query = 'SELECT password FROM "Users" WHERE username = :u'
        df = conn.query(query, params={"u": username}, ttl=0)
        
        if not df.empty:
            hash_db = df.iloc[0]['password']
            # 2. Comparamos con bcrypt
            return bcrypt.checkpw(clave_ingresada.encode('utf-8'), hash_db.encode('utf-8'))
        return False
    except:
        return False
def show():
    st.title("⚙️ Mi Perfil")
    st.caption("Gestiona tu seguridad y preferencias.")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    # --- TARJETA IZQUIERDA ---
    with col1:
        with st.container(border=True):
            st.markdown("### 👤 Datos")
            st.info(f"**Usuario:**\n{st.session_state.username}")
            st.info(f"**Nombre:**\n{st.session_state.real_name}")
            st.info(f"**Rol:**\n{st.session_state.role}")

    # --- TARJETA DERECHA ---
    with col2:
        with st.container(border=True):
            st.markdown("### 🔐 Cambiar Contraseña")
            
            pass_actual = st.text_input("Contraseña Actual", type="password", key="p_old")
            pass_nueva = st.text_input("Nueva Contraseña", type="password", key="p_new")
            pass_confirm = st.text_input("Confirmar Nueva Contraseña", type="password", key="p_conf")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Actualizar Contraseña", type="primary", use_container_width=True):
                # Validaciones
                if not pass_actual or not pass_nueva:
                    st.warning("⚠️ Debes llenar los campos.")
                    return
                
                if pass_nueva != pass_confirm:
                    st.error("❌ Las nuevas contraseñas no coinciden.")
                    return
                
                if len(pass_nueva) < 4: # Bajé el límite a 4 por si usas claves cortas
                    st.warning("⚠️ La contraseña es muy corta.")
                    return

                # Lógica de guardado
                if validar_clave_actual(st.session_state.username, pass_actual):
                    
                    # --- ENCRIPTAR LA NUEVA ---
                    hashed_new = bcrypt.hashpw(pass_nueva.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                    if actualizar_password_supabase(st.session_state.username, hashed_new): # Enviamos hash
                        st.success("✅ ¡Contraseña actualizada correctamente!")
                        st.balloons()
                        time.sleep(2)
                        # Limpiamos campos recargando
                        st.rerun()
                    else:
                        st.error("Hubo un problema al guardar en la base de datos.")
                else:
                    st.error("❌ La contraseña actual es incorrecta.")

if __name__ == "__main__":
    show()