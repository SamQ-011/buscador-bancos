import streamlit as st
import re
import pandas as pd

# --- 1. MOTOR DE EXTRACCIÓN (El que ya validamos) ---
def parse_crm_text(raw_text):
    data = {}
    
    # ID
    match_id = re.search(r"(CORDOBA-\d+)", raw_text)
    if match_id: data['cordoba_id'] = match_id.group(1)

    # Nombre (Limpieza de "Purchaser...")
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    if lines:
        raw_line = lines[0]
        clean_name = re.sub(r"\s*Purchaser\s+\d+\s+Eligible.*", "", raw_line, flags=re.IGNORECASE)
        data['raw_name_guess'] = clean_name.strip()

    # Idioma
    match_lang = re.search(r"Language:\s*(\w+)", raw_text, re.IGNORECASE)
    if match_lang: data['language'] = match_lang.group(1)

    # Email
    match_email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    if match_email: data['email'] = match_email.group(0)

    # Afiliado / Campaña
    match_mkt = re.search(r"Marketing Company\s*(.*)", raw_text, re.IGNORECASE)
    if match_mkt and len(match_mkt.group(1).strip()) > 1:
        data['marketing_company'] = match_mkt.group(1).strip()
    
    # Deuda Total
    match_debt = re.search(r"(?:Total )?Debt:\s*\$([\d,]+\.\d{2})", raw_text)
    if match_debt: 
        data['total_debt'] = float(match_debt.group(1).replace(',',''))

    # Estado
    match_geo = re.search(r"\b([A-Z]{2})\s+(\d{5})", raw_text)
    if match_geo:
        data['state'] = match_geo.group(1)

    return data

# --- 2. LÓGICA DE EMPAREJAMIENTO (NUEVO) ---
def match_affiliate(parsed_affiliate, db_options):
    """
    Intenta encontrar el afiliado del texto en la lista oficial del sistema.
    """
    if not parsed_affiliate:
        return None
    
    parsed_clean = parsed_affiliate.lower().strip()
    
    # Intento 1: Coincidencia Exacta
    for op in db_options:
        if op.lower().strip() == parsed_clean:
            return op
            
    # Intento 2: Contiene (Ej: "Financial Relief" en "Financial Relief LLC")
    for op in db_options:
        if parsed_clean in op.lower():
            return op
            
    return None

# --- 3. INTERFAZ VISUAL ---
def show():
    st.title("🧪 Lab: Simulador de Auto-Llenado")
    
    # Lista Simulada de Afiliados (Basada en tus fotos)
    mock_affiliates_list = sorted([
        "Golden Rise Capital",
        "Prosperity Financial",
        "Independence Financial Network 2",
        "Patriot Option Group",
        "Plume Finance",
        "Priority Plus Financial",
        "Financial Relief",
        "GotLending",
        "Freedom Loan Network LLC"
    ])

    # Inicialización de variables de prueba
    if "test_name" not in st.session_state: st.session_state.test_name = ""
    if "test_id" not in st.session_state: st.session_state.test_id = ""
    if "test_aff" not in st.session_state: st.session_state.test_aff = None

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Origen (CRM)")
        raw_input = st.text_area("Pegar Texto Aquí:", height=300, placeholder="Pega el texto de Forth...")
        
        if st.button("⚡ Simular Auto-Llenado", type="primary", use_container_width=True):
            if raw_input:
                # A) Extraer datos
                extracted = parse_crm_text(raw_input)
                
                # B) Aplicar a variables de sesión (Simulando notas.py)
                if 'raw_name_guess' in extracted:
                    st.session_state.test_name = extracted['raw_name_guess']
                
                if 'cordoba_id' in extracted:
                    st.session_state.test_id = extracted['cordoba_id']
                
                # C) Lógica del Afiliado
                mkt_text = extracted.get('marketing_company', '')
                found_aff = match_affiliate(mkt_text, mock_affiliates_list)
                
                if found_aff:
                    st.session_state.test_aff = found_aff
                    st.toast(f"✅ Afiliado vinculado: {found_aff}")
                else:
                    st.session_state.test_aff = None
                    if mkt_text:
                        st.warning(f"⚠️ No se encontró '{mkt_text}' en la lista oficial.")
            else:
                st.error("Pega algo de texto primero.")

    with col2:
        st.subheader("2. Destino (Tu App)")
        st.caption("Así se verían los campos llenos automáticamente:")
        
        with st.container(border=True):
            st.text_input("Cx Name", key="test_name")
            st.text_input("Cordoba ID", key="test_id")
            
            # Selectbox para probar si selecciona el correcto
            st.selectbox(
                "Affiliate (Selectbox)", 
                options=mock_affiliates_list, 
                key="test_aff",
                index=None,
                placeholder="Seleccione..."
            )
            
        st.info("👆 Si los campos de arriba tienen datos, ¡funciona!")

if __name__ == "__main__":
    show()
