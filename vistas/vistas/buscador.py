import streamlit as st
import pandas as pd

# --- CARGA DE DATOS SQL ---
@st.cache_data(ttl=3600)
def cargar_datos_bancos():
    try:
        conn = st.connection("supabase", type="sql")
        
        # OJO: Usamos comillas dobles para respetar mayúsculas exactas de tu base de datos
        # Seleccionamos y ordenamos por la abreviación
        query = 'SELECT abreviation, name FROM "Creditors" ORDER BY abreviation ASC'
        
        df = conn.query(query, ttl=3600)
        
        # Renombramos y preparamos datos visuales
        if not df.empty:
            df = df.rename(columns={"abreviation": "Código", "name": "Acreedor"})
            # TRUCO VISUAL: Insertamos una columna de iconos al principio
            df.insert(0, "Tipo", "🏦")
            
        return df
    except Exception as e:
        st.error(f"Error conectando a Creditors: {e}")
        return pd.DataFrame()

def show():
    # --- LAYOUT DE ENCABEZADO (Título + Badge) ---
    # Usamos columnas [3, 1] para empujar el badge a la derecha
    c_titulo, c_badge = st.columns([3, 1], gap="medium")
    
    with c_titulo:
        st.title("🔍 Buscador")
        st.caption("Escribe el nombre o código del acreedor para obtener los datos.")
        
    # Cargamos datos para el contador
    df = cargar_datos_bancos()
    total = len(df) if not df.empty else 0

    with c_badge:
        # BADGE FLOTANTE (HTML/CSS)
        # Esto crea la tarjeta pequeña gris con el punto verde
        st.markdown(f"""
            <div style="
                text-align: right; 
                background-color: #F8F9FA; 
                padding: 8px 15px; 
                border-radius: 12px; 
                border: 1px solid #E9ECEF;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <span style="font-size: 11px; color: #6C757D; text-transform: uppercase; letter-spacing: 1px;">Base de Datos</span><br>
                <span style="font-size: 24px; font-weight: 700; color: #0F52BA;">{total}</span>
                <span style="font-size: 14px; color: #495057;"> Bancos</span>
                <span style="color: #28A745; margin-left: 5px;">●</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- BARRA DE BÚSQUEDA TIPO "SPOTLIGHT" ---
    # Grande, limpia y sin etiqueta visible
    busqueda = st.text_input(
        "Search", 
        placeholder="✨ Empieza a escribir aquí (ej: CITIBANK)...", 
        label_visibility="collapsed"
    ).strip()

    # --- RESULTADOS ---
    if busqueda:
        if not df.empty:
            # Filtro Case-Insensitive (Mayúsculas/Minúsculas)
            m1 = df['Código'].str.contains(busqueda, case=False, na=False)
            m2 = df['Acreedor'].str.contains(busqueda, case=False, na=False)
            resultados = df[m1 | m2]

            if not resultados.empty:
                st.success(f"⚡ Se encontraron {len(resultados)} coincidencias.")
                
                # TABLA VISUAL
                st.dataframe(
                    resultados, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "Tipo": st.column_config.TextColumn("", width="30px"), # Icono pequeño
                        "Código": st.column_config.TextColumn(
                            "Código ID", 
                            width="small",
                            help="Copia este valor para el CRM"
                        ),
                        "Acreedor": st.column_config.TextColumn(
                            "Nombre Oficial", 
                            width="large"
                        )
                    }
                )
            else:
                st.warning(f"🤷‍♂️ No encontré nada con: **'{busqueda}'**")
        else:
            st.error("⚠️ La base de datos parece estar vacía.")
    
    else:
        # EMPTY STATE (Estado Vacío Elegante)
        # Muestra esto cuando no están buscando nada
        st.markdown("""
            <div style="text-align: center; color: #ADB5BD; margin-top: 40px;">
                <div style="font-size: 40px; margin-bottom: 10px;">⌨️</div>
                <p>Usa la barra de arriba para filtrar los <b>900+</b> acreedores.</p>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    show()