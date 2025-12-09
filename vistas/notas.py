import streamlit as st

def show():
    st.title("📝 Generador de Notas")
    st.markdown("---")

    # --- 0. GESTIÓN DE MEMORIA (Para que no desaparezca la nota) ---
    if "nota_generada" not in st.session_state:
        st.session_state.nota_generada = ""

    # --- 1. SELECCIÓN DE RESULTADO ---
    resultado = st.radio(
        "Resultado:", 
        ["Completed", "Not Completed"], 
        horizontal=True
    )

    st.markdown("### 👤 Datos del Cliente")
    # Mantenemos 3 columnas para que se vea alineado
    col1, col2, col3 = st.columns(3)
    with col1:
        cliente = st.text_input("Cx Name (Nombre)")
    with col2:
        cordoba_id = st.text_input("Cordoba ID")
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
        
        reason = st.text_input("Reason (Razón específica)")
        
        # Lista de script
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
            # Cambio de opciones según tu solicitud
            transfer = st.radio("Transfer Status:", ["Successful", "Not Successful"], horizontal=True)
        with c4:
            return_call = st.radio("Return?", ["Yes", "No"], horizontal=True)

    st.markdown("---")

    # --- 3. BOTÓN Y GENERACIÓN ---
    if st.button("Generar Nota CRM", type="primary"):
        
        # LÓGICA DE FORMATO
        if resultado == "Completed":
            # FORMATO 1: COMPLETADO
            # ✅ WC completed
            # CX: Erica Drake CORDOBA-1176230795
            # Affiliate: ...
            nota_final = f"""✅ WC Completed
CX: {cliente} CORDOBA-{cordoba_id}
Affiliate: {affiliate}"""

        else:
            # FORMATO 2: NO COMPLETADO
            # ❌ WC Not Completed – Returned
            # CX: Erica Drake CORDOBA-1176230795
            # • Reason: ...
            # • Call Progress: ...
            # • Transfer Status: ...
            # Affiliate: ...
            
            # Lógica Título
            status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
            
            nota_final = f"""❌ WC Not Completed – {status_titulo}
CX: {cliente} CORDOBA-{cordoba_id}
• Reason: {reason}
• Call Progress: {script_stage}
• Transfer Status: {transfer}.
Affiliate: {affiliate}"""

        # GUARDAMOS EN MEMORIA (SESSION STATE)
        st.session_state.nota_generada = nota_final

    # --- 4. MOSTRAR EL RESULTADO (PERSISTENTE) ---
    # Esto se ejecuta siempre, así que si hay una nota guardada, la muestra
    if st.session_state.nota_generada:
        st.success("Nota generada:")
        st.text_area("Copia y pega:", st.session_state.nota_generada, height=220)
