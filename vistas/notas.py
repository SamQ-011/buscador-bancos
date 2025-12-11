import streamlit as st

def show():
    st.title("📝 Generador de Notas")

    # --- GESTIÓN DE MEMORIA (INDEPENDIENTE PARA CADA PESTAÑA) ---
    # Esto asegura que lo que escribas en una pestaña no borre lo de la otra
    if "nota_completed" not in st.session_state:
        st.session_state.nota_completed = ""
    
    if "nota_not_completed" not in st.session_state:
        st.session_state.nota_not_completed = ""
        
    if "nota_third_party" not in st.session_state:
        st.session_state.nota_third_party = ""

    # --- PESTAÑAS ---
    tab_completed, tab_not_completed, tab_third_party = st.tabs([
        "✅ WC Completed", 
        "❌ WC Not Completed", 
        "👥 Third Party (Legal)"
    ])

    # ==========================================
    # PESTAÑA 1: COMPLETED (DIVIDIDA)
    # ==========================================
    with tab_completed:
        c_izq, c_der = st.columns([1, 1])
        
        with c_izq:
            st.subheader("📝 Datos")
            c_name = st.text_input("Cx Name", key="c_name")
            c_id = st.text_input("Cordoba ID", key="c_id")
            c_aff = st.text_input("Affiliate", key="c_aff")
            
            st.markdown("---")
            
            # BOTÓN COMPLETED
            if st.button("Generar Nota COMPLETED", type="primary", key="btn_comp"):
                id_clean = ''.join(filter(str.isdigit, c_id)) or "MISSING_ID"
                
                texto_generado = f"""✅ WC Completed
CX: {c_name} CORDOBA-{id_clean}
Affiliate: {c_aff}"""
                
                # Guardamos en su memoria específica y recargamos
                st.session_state.nota_completed = texto_generado
                st.rerun()

        with c_der:
            st.subheader("📋 Resultado")
            # Vinculamos esta caja SOLO a 'nota_completed'
            st.text_area("Copia aquí:", key="nota_completed", height=300)


    # ==========================================
    # PESTAÑA 2: NOT COMPLETED (DIVIDIDA)
    # ==========================================
    with tab_not_completed:
        nc_izq, nc_der = st.columns([1, 1])
        
        with nc_izq:
            st.subheader("📝 Datos")
            nc_name = st.text_input("Cx Name", key="nc_name")
            nc_id = st.text_input("Cordoba ID", key="nc_id")
            nc_aff = st.text_input("Affiliate", key="nc_aff")
            
            st.markdown("---")
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
                    transfer_fail_reason = st.selectbox("Razón:", ["Voicemail", "Line Busy", "Refused", "Gatekeeper", "Hold Time"])
            
            with col_b:
                return_call = st.radio("Return Call?", ["Yes", "No"], horizontal=True, key="nc_ret")

            st.markdown("---")
            
            # BOTÓN NOT COMPLETED
            if st.button("Generar Nota NOT COMPLETED", type="primary", key="btn_not"):
                id_clean = ''.join(filter(str.isdigit, nc_id)) or "MISSING_ID"
                status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
                
                texto_transfer = transfer
                if transfer == "Unsuccessful":
                    texto_transfer = f"Unsuccessful ({transfer_fail_reason})"

                texto_generado = f"""❌ WC Not Completed – {status_titulo}
CX: {nc_name} CORDOBA-{id_clean}
• Reason: {reason}
• Call Progress: {script_stage}
• Transfer Status: {texto_transfer}
Affiliate: {nc_aff}"""
                
                # Guardamos en su memoria específica y recargamos
                st.session_state.nota_not_completed = texto_generado
                st.rerun()

        with nc_der:
            st.subheader("📋 Resultado")
            # Vinculamos esta caja SOLO a 'nota_not_completed'
            st.text_area("Copia aquí:", key="nota_not_completed", height=600)


    # ==========================================
    # PESTAÑA 3: THIRD PARTY (DIVIDIDA)
    # ==========================================
    with tab_third_party:
        tp_izq, tp_der = st.columns([1, 1])
        
        with tp_izq:
            st.subheader("👥 Personas Presentes")
            
            num_terceros = st.number_input("Cantidad de personas extra:", min_value=1, value=1, step=1)
            
            lista_terceros = [] 
            
            for i in range(num_terceros):
                st.markdown(f"**Persona {i+1}**")
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    nom = st.text_input(f"Nombre", key=f"p_nom_{i}")
                with c_p2:
                    rel = st.text_input(f"Relación", placeholder="Mother, Son...", key=f"p_rel_{i}")
                lista_terceros.append({'nombre': nom, 'relacion': rel})

            st.markdown("---")
            
            # BOTÓN THIRD PARTY
            if st.button("Generar Third Party", type="primary", key="btn_tp"):
                
                if num_terceros == 1:
                    nombre_p = lista_terceros[0]['nombre']
                    relacion_p = lista_terceros[0]['relacion']
                    parrafo_legal = f"During the WC, {nombre_p} was present on the call. This person is the {relacion_p} of the client, and their participation was authorized by the client."
                else:
                    nombres = ", ".join([p['nombre'] for p in lista_terceros])
                    relaciones = ", ".join([p['relacion'] for p in lista_terceros])
                    parrafo_legal = f"During the WC, {nombres} were present on the call. These persons are the {relaciones} of the client, and their participation was authorized by the client."

                # Guardamos en su memoria específica y recargamos
                st.session_state.nota_third_party = parrafo_legal
                st.rerun()

        with tp_der:
            st.subheader("⚖️ Third party")
            
            # Vinculamos esta caja SOLO a 'nota_third_party'
            st.text_area("Nota:", key="nota_third_party", height=300)

if __name__ == "__main__":
    show()