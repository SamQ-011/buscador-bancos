import streamlit as st

def show():
    st.title("📝 Generador de Notas")
    st.markdown("---")

    # --- 0. GESTIÓN DE MEMORIA (Persistencia) ---
    if "nota_generada" not in st.session_state:
        st.session_state.nota_generada = ""

    # --- 1. SELECCIÓN DE RESULTADO ---
    resultado = st.radio(
        "Resultado:", 
        ["Completed", "Not Completed"], 
        horizontal=True
    )

    st.markdown("### 👤 Datos del Cliente")
    col1, col2, col3 = st.columns(3)
    with col1:
        cliente = st.text_input("Cx Name (Nombre)")
    with col2:
        # El agente puede pegar lo que sea aquí, nosotros lo limpiamos después
        cordoba_id = st.text_input("Cordoba ID (Solo números o con texto)")
    with col3:
        affiliate = st.text_input("Affiliate (Nombre de la empresa)")

    # VARIABLES POR DEFECTO
    reason = ""
    script_stage = "All info provided"
    transfer = "Not Successful"
    return_call = "No"

    # --- 2. CAMPOS EXTRA SI NO SE COMPLETÓ ---
    if resultado == "Not Completed":
        st.markdown("---")
        st.markdown("### ⚠️ Detalles")
        
        # CAMBIO 1: Text Area para permitir múltiples líneas y listas de deudas
        reason = st.text_area("Reason (Permite múltiples líneas)", height=100)
        
        opciones_script = [
            "All info provided", "No info provided", "the text message of the VCF", "the contact info verification", "the banking info verification", 
            "the enrollment plan verification", "the Yes/No verification questions", "the creditors verification", "the right of offset",
            "1st agreement (we aren't making payments until we get a settlement)", "2nd agreement (credit could be affected)", "3rd agreement (we aren't a government program)",
            "4th agreement (client can be sued)", "5th agreement (we aren't loaning you money)", "the part where we ask for the most recent statements, after the agreements.",
            "the harassing phone calls info", "the additional legal services info, at the end of the call."
        ]
        script_stage = st.selectbox("Call Progress (Hasta dónde llegó):", opciones_script)
        
        c3, c4 = st.columns(2)
        with c3:
            transfer = st.radio("Transfer Status:", ["Successful", "Unsuccessful"], horizontal=True)
        with c4:
            return_call = st.radio("Return?", ["Yes", "No"], horizontal=True)

    st.markdown("---")

    # --- 3. BOTÓN Y GENERACIÓN ---
    if st.button("Generar Nota CRM", type="primary"):
        
        # CAMBIO 2: LIMPIEZA AUTOMÁTICA DEL ID
        # Esta línea mágica elimina letras, guiones y espacios. Deja solo números.
        # Ejemplo: "CORDOBA-12345" -> "12345"
        id_numerico = ''.join(filter(str.isdigit, cordoba_id))
        
        # Si el usuario no puso nada, dejamos un aviso
        if not id_numerico:
            id_numerico = "MISSING_ID"

        # LÓGICA DE FORMATO
        if resultado == "Completed":
            # Usamos id_numerico en lugar de cordoba_id
            nota_final = f"""✅ WC Completed
CX: {cliente} CORDOBA-{id_numerico}
Affiliate: {affiliate}"""

        else:
            status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
            
            nota_final = f"""❌ WC Not Completed – {status_titulo}
CX: {cliente} CORDOBA-{id_numerico}
• Reason: {reason}
• Call Progress: {script_stage}
• Transfer Status: {transfer}.
Affiliate: {affiliate}"""

        # Guardamos en memoria
        st.session_state.contenido_nota = nota_final

    # --- 4. MOSTRAR RESULTADO (EDITABLE) ---
    if "contenido_nota" not in st.session_state:
        st.session_state.contenido_nota = ""

    if st.session_state.contenido_nota:
        st.success("Nota generada (Editable):")
        st.text_area("Copia y pega:", key="contenido_nota", height=250)


