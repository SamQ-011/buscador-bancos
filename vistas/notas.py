import streamlit as st

def show():
    st.title("📝 Generador de Notas")
    st.markdown("---")

    # 1. SELECCIÓN DE RESULTADO
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
        cordoba_id = st.text_input("Cordoba ID")
    with col3:
        affiliate = st.text_input("Affiliate (Nombre de la empresa)")

    # VARIABLES POR DEFECTO
    reason = ""
    script_stage = "All info provided"
    transfer = "Not Successful"
    return_call = "No"

    # 2. CAMPOS EXTRA SI NO SE COMPLETÓ
    if resultado == "Not Completed":
        st.markdown("---")
        st.markdown("### ⚠️ Detalles")
        
        reason = st.text_input("Reason (Razón específica)")
        
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
            transfer = st.radio("Transfer Status:", ["Successful", "Not Successful"], horizontal=True)
        with c4:
            return_call = st.radio("Return?", ["Yes", "No"], horizontal=True)

    st.markdown("---")

    # 3. BOTÓN Y GENERACIÓN
    if st.button("Generar Nota CRM", type="primary"):
        
        # LÓGICA DE FORMATO
        if resultado == "Completed":
            nota_final = f"""✅ WC Completed
CX: {cliente} CORDOBA-{cordoba_id}
Affiliate: {affiliate}"""

        else:
            # Lógica Título
            status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
            
            nota_final = f"""❌ WC Not Completed – {status_titulo}
CX: {cliente} CORDOBA-{cordoba_id}
• Reason: {reason}
• Call Progress: {script_stage}
• Transfer Status: {transfer}.
Affiliate: {affiliate}"""

        # --- EL TRUCO ESTÁ AQUÍ ---
        # Guardamos el resultado en la llave especial que usa la caja de texto
        st.session_state.contenido_nota = nota_final

    # 4. MOSTRAR EL RESULTADO (EDITABLE)
    # Si la llave "contenido_nota" aún no existe en memoria, la creamos vacía
    if "contenido_nota" not in st.session_state:
        st.session_state.contenido_nota = ""

    st.success("Nota generada (Puedes editarla antes de copiar):")
    
    # Al usar key="contenido_nota", esta caja muestra lo que hay en memoria
    # Y si tú escribes en ella, actualiza la memoria sin borrarse.
    st.text_area("Copia y pega:", key="contenido_nota", height=220)
