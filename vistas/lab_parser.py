import streamlit as st
import re
import pandas as pd

def parse_crm_text(raw_text):
    """
    Motor de extracción de datos basado en patrones de texto de Forth CRM.
    """
    data = {}
    
    # --- 1. DATOS DE IDENTIFICACIÓN ---
    
    # ID: Busca CORDOBA- seguido de digitos
    match_id = re.search(r"(CORDOBA-\d+)", raw_text)
    if match_id: data['cordoba_id'] = match_id.group(1)

    # Nombre: Limpieza avanzada
    # Tomamos la primera línea no vacía
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    if lines:
        raw_line = lines[0]
        # CORRECCIÓN: Eliminamos "Purchaser X Eligible" y cualquier cosa que siga
        # Usamos Regex para borrar "Purchaser" + digitos + "Eligible"
        clean_name = re.sub(r"\s*Purchaser\s+\d+\s+Eligible.*", "", raw_line, flags=re.IGNORECASE)
        data['raw_name_guess'] = clean_name.strip()

    # Idioma
    match_lang = re.search(r"Language:\s*(\w+)", raw_text, re.IGNORECASE)
    if match_lang: data['language'] = match_lang.group(1)

    # Email
    match_email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    if match_email: data['email'] = match_email.group(0)

    # --- 2. DATOS DE CAMPAÑA / AFILIADO ---
    # Marketing Company (Suele ser el Afiliado real)
    match_mkt = re.search(r"Marketing Company\s*(.*)", raw_text, re.IGNORECASE)
    if match_mkt and len(match_mkt.group(1).strip()) > 1:
        data['marketing_company'] = match_mkt.group(1).strip()
    
    # Campaign
    match_camp = re.search(r"Campaign\s*(.*)", raw_text, re.IGNORECASE)
    if match_camp and len(match_camp.group(1).strip()) > 1:
        data['campaign'] = match_camp.group(1).strip()

    # --- 3. DATOS FINANCIEROS (Limpiamos el signo $ y comas) ---
    def clean_money(val):
        return float(val.replace('$','').replace(',',''))

    # Deuda Total (Soporta "Debt:" y "Total Debt:")
    match_debt = re.search(r"(?:Total )?Debt:\s*\$([\d,]+\.\d{2})", raw_text)
    if match_debt: data['total_debt'] = clean_money(match_debt.group(1))

    # Income
    match_inc = re.search(r"Income:\s*\$([\d,]+\.\d{2})", raw_text)
    if match_inc: data['income'] = clean_money(match_inc.group(1))

    # Expenses
    match_exp = re.search(r"Expenses:\s*\$([\d,]+\.\d{2})", raw_text)
    if match_exp: data['expenses'] = clean_money(match_exp.group(1))

    # --- 4. DATOS GEOGRÁFICOS ---
    # Busca patrón de estado de 2 letras y ZIP (FL 33405)
    match_geo = re.search(r"\b([A-Z]{2})\s+(\d{5})", raw_text)
    if match_geo:
        data['state'] = match_geo.group(1)
        data['zip'] = match_geo.group(2)

    # --- 5. DATOS OPERATIVOS ---
    # Fecha de Creación (Created At)
    match_created = re.search(r"Created At\s*(\d{2}/\d{2}/\d{4})", raw_text)
    if match_created: data['created_at'] = match_created.group(1)

    # Status (Underwriting)
    match_status = re.search(r"Underwriting\s*:\s*(\w+)", raw_text)
    if match_status: data['uw_status'] = match_status.group(1)

    return data

def show():
    st.title("🧪 Laboratorio de Parsing (Admin Only)")
    st.markdown("""
    Pega aquí el texto completo copiado (**Ctrl+A -> Ctrl+C**) desde el perfil de CRM (Forth).
    El sistema analizará qué datos puede extraer automáticamente.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        raw_input = st.text_area("📋 Pega el texto crudo aquí:", height=400, placeholder="Debt Settlement...\nCustomer ID: CORDOBA-...")
        
        if st.button("🚀 Analizar Texto", type="primary", use_container_width=True):
            if raw_input:
                extracted_data = parse_crm_text(raw_input)
                st.session_state['lab_results'] = extracted_data
            else:
                st.warning("El campo está vacío.")

    with col2:
        st.subheader("🔍 Datos Detectados")
        
        if 'lab_results' in st.session_state and st.session_state['lab_results']:
            res = st.session_state['lab_results']
            
            # Visualización bonita tipo Tarjetas
            
            # Tarjeta Principal
            st.info(f"👤 **Cliente:** {res.get('raw_name_guess', 'N/A')} | 🆔 **{res.get('cordoba_id', 'N/A')}**")
            
            # Métricas Clave
            m1, m2, m3 = st.columns(3)
            m1.metric("Deuda Total", f"${res.get('total_debt', 0):,.2f}")
            m2.metric("Income", f"${res.get('income', 0):,.2f}")
            m3.metric("State", res.get('state', 'N/A'))

            # Tabla de Detalles
            df_display = pd.DataFrame([
                {"Campo": k, "Valor Detectado": v} for k, v in res.items()
            ])
            st.dataframe(df_display, hide_index=True, use_container_width=True)

            # Validación visual
            if 'cordoba_id' in res and 'raw_name_guess' in res:
                st.success("✅ Estructura válida para generar nota")
            else:
                st.warning("⚠️ Faltan datos críticos (ID o Nombre)")

        else:
            st.info("Esperando datos...")
            st.caption("Copia todo el texto de una ficha de cliente y pégalo a la izquierda.")

if __name__ == "__main__":
    show()
