import streamlit as st
import time

def show():
    # --- CSS: Limpieza visual y ajuste vertical ---
    st.markdown("""
        <style>
            /* Ocultar elementos molestos */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* Ajuste para subir el login más arriba */
            .block-container {
                padding-top: 50px !important; /* Reduce el espacio superior */
            }
        </style>
    """, unsafe_allow_html=True)

    # --- LAYOUT: EL TRUCO DEL CENTRADO ---
    # Usamos columnas [3, 2, 3] para que la del medio sea angosta (compacta)
    col_izq, col_centro, col_der = st.columns([3, 2, 3])

    with col_centro:
        # LOGO O ICONO (Opcional, se ve pro)
        st.markdown("<h1 style='text-align: center; font-size: 50px;'>🏦</h1>", unsafe_allow_html=True)
        
        # --- LA TARJETA (CARD) ---
        # st.container(border=True) crea el recuadro gris sutil automáticamente
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #0F52BA;'>Acceso</h2>", unsafe_allow_html=True)
            st.caption("Ingresa tus credenciales para continuar.")
            
            # INPUTS COMPACTOS
            usuario = st.text_input("Usuario", placeholder="ej: jperez").strip()
            password = st.text_input("Contraseña", type="password", placeholder="••••••").strip()
            
            st.markdown("<br>", unsafe_allow_html=True) # Pequeño respiro

            # BOTÓN DE ACCESO
            if st.button("Entrar al Sistema", type="primary", use_container_width=True):
                if usuario and password:
                    autenticar_usuario(usuario, password)
                else:
                    st.warning("⚠️ Faltan datos.")

        # Pie de página pequeño fuera de la tarjeta
        st.markdown(
            "<div style='text-align: center; color: #888; font-size: 12px; margin-top: 10px;'>"
            "🔒 Conexión Segura v2.0<br>Authorized Personnel Only"
            "</div>", 
            unsafe_allow_html=True
        )

def autenticar_usuario(user_input, pass_input):
    try:
        # Conexión a Supabase
        conn = st.connection("supabase", type="sql")
        
        # --- CORRECCIÓN 1: Comillas dobles en "Users" ---
        # Al poner "Users" entre comillas dobles, obligamos a SQL a respetar la mayúscula.
        query = 'SELECT * FROM "Users" WHERE username = :u AND password = :p AND active = TRUE'
        
        df = conn.query(query, params={"u": user_input, "p": pass_input}, ttl=0)
        
        if not df.empty:
            datos_usuario = df.iloc[0]
            
            # Guardar sesión
            st.session_state.logged_in = True
            st.session_state.username = datos_usuario['username']
            
            # --- CORRECCIÓN 2: Usar 'name' en lugar de 'real_name' ---
            # En tu foto se ve que la columna se llama 'name'
            st.session_state.real_name = datos_usuario['name'] 
            
            # Manejo seguro del rol (por si acaso no existe la columna rol, asume 'agente')
            st.session_state.role = datos_usuario.get('role', 'agente')
            
            st.toast(f"✅ ¡Hola de nuevo, {st.session_state.real_name}!", icon="👋")
            time.sleep(1)
            st.rerun()
            
        else:
            st.error("❌ Acceso denegado. Usuario o contraseña incorrectos.")
            
    except Exception as e:
        st.error(f"Error de conexión: {e}")

if __name__ == "__main__":
    show()