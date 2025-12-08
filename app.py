import streamlit as st
import pandas as pd
import os # Necesario para investigar el sistema

st.set_page_config(page_title="Debug Mode", layout="wide")

st.title("🕵️ Modo Diagnóstico")

# 1. VERIFICAR QUÉ ARCHIVOS VE EL SERVIDOR
st.write("### 1. Archivos en la carpeta actual del servidor:")
archivos = os.listdir()
st.code(archivos)

# 2. INTENTAR CARGAR EL CSV
st.write("### 2. Intentando cargar 'datos.csv'...")

if "datos.csv" in archivos:
    st.success("✅ ¡El archivo 'datos.csv' EXISTE!")
    try:
        df = pd.read_csv("datos.csv", dtype=str, on_bad_lines='skip')
        st.success(f"✅ Lectura exitosa. Filas cargadas: {len(df)}")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"❌ El archivo existe, pero falló al leerse. Error: {e}")
        st.warning("Posible causa: ¿El CSV usa ';' en vez de ','? (Común en Excel en español)")
else:
    st.error("❌ ERROR CRÍTICO: El servidor NO ve el archivo 'datos.csv'.")
    st.info("Mira la lista del paso 1. ¿Ves tu archivo con otro nombre? (ej: Datos.csv, content.csv, etc)")
