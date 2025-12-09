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
    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Cx Name (Nombre)")
    with col2:
        cordoba_id = st.text_input("Cordoba ID")
    
    # El affiliate se pide siempre, pero se usa diferente según el caso
    # Lo mostramos aquí abajo ocupando todo el ancho o en columna
    affiliate = st.text_input("Affiliate (Nombre de la empresa)")

    # VARIABLES PARA NOT COMPLETED
    reason = ""
    script_stage = "Full Script"
    transfer = "No"
    return_call = "No"

    # 2. CAMPOS EXTRA SI NO SE COMPLETÓ
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
        script_stage = st.selectbox("Info provided until (Hasta dónde llegó):", opciones_script)
        
        c3, c4 = st.columns(2)
        with c3:
            # Transferencia
            transfer = st.radio("Transfer:", ["Successful", "No"], horizontal=True)
        with c4:
            # Retorno de llamada
            return_call = st.radio("Return?", ["Yes", "No"], horizontal=True)

    st.markdown("---")

    if st.button("Generar Nota CRM", type="primary"):
        
        # --- LÓGICA DE FORMATO EXACTO ---
        
        if resultado == "Completed":
            # FORMATO 1: COMPLETADO
            # ✅ WC completed 
            # Cx: Nombre - ID
            # Affiliate: Nombre
            nota_final = f"""✅ WC completed
Cx: {cliente} - CORDOBA - {cordoba_id}
Affiliate: {affiliate}"""

        else:
            # FORMATO 2: NO COMPLETADO
            # ❌ WC not completed - [Return Status]
            # Cx: Nombre - ID
            # · Reason: ...
            # · Info provided until: ...
            # · Transfer: ...
            # · Return: ...
            
            # Lógica para el título: Si Return es Yes, ponemos "Returned" en el título
            status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
            # 2. Lógica de la línea "Info Provided" (TU CAMBIO AQUÍ)
            if script_stage in ["All info provided", "No info provided"]:
                # Si es una de estas dos, NO ponemos "Info provided until:"
                linea_info = f"· {script_stage}"
            else:
                # Para el resto, SÍ ponemos el prefijo
                linea_info = f"· Info provided until: {script_stage}"
            nota_final = f"""❌ WC not completed - {status_titulo}
Cx: {cliente} - CORDOBA - {cordoba_id}
· Reason: {reason}
{linea_info}
· Transfer: {transfer}
· Return: {return_call}
Affiliate: {affiliate}"""

        st.success("Nota generada:")
        st.text_area("Copia y pega:", nota_final, height=200)