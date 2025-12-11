import streamlit as st

def show():
    st.title("📝 Generador de Notas 2.0")

    # --- GESTIÓN DE MEMORIA ---
    if "nota_generada" not in st.session_state:
        st.session_state.nota_generada = ""

    # --- PESTAÑAS ---
    tab_completed, tab_not_completed, tab_third_party = st.tabs([
        "✅ WC Completed", 
        "❌ WC Not Completed", 
        "👥 Third Party (Legal)"
    ])

    # ==========================================
    # PESTAÑA 1: COMPLETED
    # ==========================================
    with tab_completed:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Datos del Cliente")
            c_name = st.text_input("Cx Name", key="c_name")
            c_id = st.text_input("Cordoba ID", key="c_id")
            c_aff = st.text_input("Affiliate", key="c_aff")
        
        with c2:
            st.info("Nota rápida para ventas exitosas.")
            st.markdown("Presiona generar abajo.")

        if st.button("Generar Nota COMPLETED", type="primary", key="btn_comp"):
            id_clean = ''.join(filter(str.isdigit, c_id)) or "MISSING_ID"
            nota_final = f"""✅ WC Completed
CX: {c_name} CORDOBA-{id_clean}
Affiliate: {c_aff}"""
            st.session_state.nota_generada = nota_final


    # ==========================================
    # PESTAÑA 2: NOT COMPLETED
    # ==========================================
    with tab_not_completed:
        nc1, nc2 = st.columns([1, 1.5])
        
        with nc1:
            st.subheader("Datos del Cliente")
            nc_name = st.text_input("Cx Name", key="nc_name")
            nc_id = st.text_input("Cordoba ID", key="nc_id")
            nc_aff = st.text_input("Affiliate", key="nc_aff")

        with nc2:
            st.subheader("Detalles")
            reason = st.text_area("Reason", height=100, key="nc_reason")
            
            opciones_script = [
            "All info provided", "No info provided", "the text message of the VCF", "the contact info verification", "the banking info verification", 
            "the enrollment plan verification", "the Yes/No verification questions", "the creditors verification", "the right of offset",
            "1st agreement (we aren't making payments until we get a settlement)", "2nd agreement (credit could be affected)", "3rd agreement (we aren't a government program)",
            "4th agreement (client can be sued)", "5th agreement (we aren't loaning you money)", "the part where we ask for the most recent statements, after the agreements.",
            "the harassing phone calls info", "the additional legal services info, at the end of the call."
            ]
            script_stage = st.selectbox("Call Progress:", opciones_script, key="nc_script")

            col_a, col_b = st.columns(2)
            with col_a:
                transfer = st.radio("Transfer Status:", ["Successful", "Unsuccessful"], horizontal=True, key="nc_trans")
                if transfer == "Unsuccessful":
                    st.markdown("🔻 **¿Por qué falló?**")
                    transfer_fail_reason = st.selectbox("Razón fallo:", ["Voicemail", "Line Busy/Disconnected", "Language Barrier", "Refused Transfer", "Gatekeeper Block", "Hold Time Exceeded"])
            
            with col_b:
                return_call = st.radio("Return Call?", ["Yes", "No"], horizontal=True, key="nc_ret")

        if st.button("Generar Nota NOT COMPLETED", type="primary", key="btn_not"):
            id_clean = ''.join(filter(str.isdigit, nc_id)) or "MISSING_ID"
            status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
            
            texto_transfer = transfer
            if transfer == "Unsuccessful":
                texto_transfer = f"Unsuccessful ({transfer_fail_reason})"

            nota_final = f"""❌ WC Not Completed – {status_titulo}
CX: {nc_name} CORDOBA-{id_clean}
• Reason: {reason}
• Call Progress: {script_stage}
• Transfer Status: {texto_transfer}
Affiliate: {nc_aff}"""
            st.session_state.nota_generada = nota_final


    # ==========================================
    # PESTAÑA 3: THIRD PARTY (SOLO TEXTO LEGAL)
    # ==========================================
    with tab_third_party:
        st.subheader("👥 Generador de Texto Legal")
        st.markdown("Agrega las personas presentes para generar el párrafo de autorización.")
        
        # 1. Cantidad de personas
        num_terceros = st.number_input("Cantidad de personas extra:", min_value=1, value=1, step=1)
        
        lista_terceros = [] 
        
        # 2. Bucle para generar cajones
        for i in range(num_terceros):
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                nom = st.text_input(f"Nombre Persona {i+1}", key=f"p_nom_{i}")
            with c_p2:
                rel = st.text_input(f"Relación (Mother, Son...) {i+1}", key=f"p_rel_{i}")
            lista_terceros.append({'nombre': nom, 'relacion': rel})

        st.markdown("---")

        if st.button("Generar Párrafo Legal", type="primary", key="btn_tp"):
            
            # A. Singular
            if num_terceros == 1:
                nombre_p = lista_terceros[0]['nombre']
                relacion_p = lista_terceros[0]['relacion']
                
                parrafo_legal = f"During the WC, {nombre_p} was present on the call. This person is the {relacion_p} of the client, and their participation was authorized by the client."
            
            # B. Plural
            else:
                nombres = ", ".join([p['nombre'] for p in lista_terceros])
                relaciones = ", ".join([p['relacion'] for p in lista_terceros])
                
                parrafo_legal = f"During the WC, {nombres} were present on the call. These persons are the {relaciones} of the client, and their participation was authorized by the client."

            # Guardamos SOLO el párrafo
            st.session_state.nota_generada = parrafo_legal


    # ==========================================
    # RESULTADO FINAL (EDITABLE)
    # ==========================================
    st.markdown("### 📋 Nota Generada")
    
    if "nota_generada" not in st.session_state:
        st.session_state.nota_generada = ""

    # Area de texto editable vinculada a la memoria
    st.text_area("Copia el texto aquí:", key="nota_generada", height=200)

if __name__ == "__main__":
    show()
