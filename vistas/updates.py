import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN ---
@st.cache_data(ttl=600)
def cargar_noticias_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Leemos los secretos
        creds_dict = st.secrets["gcp_service_account"]
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Abrimos el Sheet
        sheet = client.open("Updates_App").sheet1 

        # Convertimos a DataFrame
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return pd.DataFrame()

def show():
    st.title("🔔 Central de Noticias")
    st.caption("Conectado en tiempo real a Google Sheets")
    st.markdown("---")

    # Cargar datos
    df = cargar_noticias_google()

    if not df.empty:
        # 1. FILTRADO (Ahora busca la columna 'Active')
        # Convertimos a string y mayúsculas para asegurar que 'TRUE' o 'True' funcionen
        if 'Active' in df.columns:
            df['Active'] = df['Active'].astype(str).str.upper()
            df_activas = df[df['Active'] == 'TRUE']
        else:
            st.error("⚠️ Error: No encuentro la columna 'Active' en el Excel.")
            return

        # 2. ORDENAMIENTO (Ahora busca la columna 'Date')
        try:
            # Intentamos convertir la fecha. dayfirst=False asume formato gringo (MM/DD/YYYY)
            # Si usas formato latino (DD/MM/YYYY), cambia a dayfirst=True
            df_activas['Fecha_dt'] = pd.to_datetime(df_activas['Date'], dayfirst=False)
            df_activas = df_activas.sort_values(by='Fecha_dt', ascending=False)
        except:
            pass # Si falla, muestra el orden tal cual viene del Excel

        # 3. MOSTRAR TARJETAS
        if not df_activas.empty:
            for index, row in df_activas.iterrows():
                # Leemos las columnas en INGLÉS
                tipo = str(row['Type']).strip().lower()
                titulo_texto = row['Title']
                mensaje = row['Message']
                fecha_texto = row['Date']

                titulo_final = f"**{fecha_texto}** | {titulo_texto}"

                # Lógica Bilingüe (Acepta 'alert' o 'alerta')
                if tipo in ['alerta', 'alert', 'error', 'urgent']:
                    st.error(f"🚨 {titulo_final}\n\n{mensaje}")
                
                elif tipo in ['exito', 'success', 'done', 'new']:
                    st.success(f"🎉 {titulo_final}\n\n{mensaje}")
                
                else: # Info, General, etc.
                    st.info(f"ℹ️ {titulo_final}\n\n{mensaje}")
        else:
            st.info("No hay noticias activas en este momento.")
    
    else:
        st.warning("No se pudo conectar a la base de noticias o la hoja está vacía.")

    # Botón de recarga
    if st.button("🔄 Actualizar Noticias"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    show()