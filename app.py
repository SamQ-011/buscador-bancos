import streamlit as st
import pandas as pd

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Buscador de Acreedores", page_icon="🔍")

st.title("🔍 Buscador de Acreedores")
st.markdown("Escribe la abreviación del banco para encontrar el nombre completo.")

# FUNCIÓN DE LIMPIEZA DE DATOS (DATA CLEANING)
@st.cache_data
def cargar_y_limpiar_datos():
    try:
        # 1. Cargar el Excel
        df = pd.read_excel("content.xlsx")
        
        # Asegurarnos de que las columnas se llamen como queremos (por si acaso)
        if len(df.columns) >= 2:
            df.columns = ['Abreviacion', 'Nombre']
        
        # 2. LA MAGIA: Separar las celdas que tienen datos pegados con "Enter" (\n)
        # Convertimos a texto (str) y dividimos por el salto de línea
        df['Abreviacion'] = df['Abreviacion'].astype(str).str.split('\n')
        df['Nombre'] = df['Nombre'].astype(str).str.split('\n')
        
        # "Explotamos" las listas para crear filas individuales
        # (Esto convierte una celda doble en dos filas normales)
        df = df.explode(['Abreviacion', 'Nombre'])
        
        # 3. Limpieza final (quitar espacios extra y filas vacías)
        df['Abreviacion'] = df['Abreviacion'].str.strip()
        df['Nombre'] = df['Nombre'].str.strip()
        df = df[df['Abreviacion'] != 'nan'] # Eliminar vacíos
        
        return df
        
    except Exception as e:
        st.error(f"⚠️ Hubo un error al leer el archivo: {e}")
        return pd.DataFrame()

# Ejecutamos la carga
df = cargar_y_limpiar_datos()

# INTERFAZ DE BÚSQUEDA
if not df.empty:
    busqueda = st.text_input("Ingresa la abreviación:", "").strip().upper()

    if busqueda:
        # Buscamos coincidencias parciales
        resultados = df[df['Abreviacion'].str.contains(busqueda, case=False, na=False)]

        if not resultados.empty:
            st.success(f"✅ Se encontraron {len(resultados)} coincidencia(s):")
            st.table(resultados)
        else:
            st.warning("❌ No se encontró esa abreviación.")