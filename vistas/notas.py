import streamlit as st

def show():
    st.title("📝 Generador de Notas 2.0")

    # --- 1. PESTAÑAS SUPERIORES ---
    # Creamos las 3 pestañas como querías
    tab_completed, tab_not_completed, tab_third_party = st.tabs([
        "✅ WC Completed", 
        "❌ WC Not Completed", 
        "bust_in_silhouette: Third Party"
    ])

    # Variables para guardar los datos (se llenarán según la pestaña activa)
    cliente = ""
    cordoba_id = ""
    affiliate = ""
    nota_final = ""

    # ==========================================
    # PESTAÑA 1: COMPLETED
    # ==========================================
    with tab_completed:
        c1, c2 = st.columns([1, 1]) # Dividimos en 2 columnas iguales
        
        with c1:
            st.subheader("Datos del Cliente")
            # Usamos keys únicas (c_...) para que no choquen con la otra pestaña
            c_name = st.text_input("Cx Name", key="c_name")
            c_id = st.text_input("Cordoba ID", key="c_id")
            c_aff = st.text_input("Affiliate", key="c_aff")
        
        with c2:
            st.info("Para una llamada completada, no se requieren detalles extra.")
            st.markdown("Presiona generar abajo cuando estés listo.")

        # Botón de Generar (Solo visible en esta pestaña)
        if st.button("Generar Nota COMPLETED", type="primary", key="btn_comp"):
            # Limpieza de ID
            id_clean = ''.join(filter(str.isdigit, c_id)) or "MISSING_ID"
            nota_final = f"""✅ WC Completed
CX: {c_name} CORDOBA-{id_clean}
Affiliate: {c_aff}"""
            st.session_state.nota_generada = nota_final


    # ==========================================
    # PESTAÑA 2: NOT COMPLETED
    # ==========================================
    with tab_not_completed:
        nc1, nc2 = st.columns([1, 1.5]) # La derecha (nc2) un poco más ancha para el Reason
        
        with nc1:
            st.subheader("Datos del Cliente")
            nc_name = st.text_input("Cx Name", key="nc_name")
            nc_id = st.text_input("Cordoba ID", key="nc_id")
            nc_aff = st.text_input("Affiliate", key="nc_aff")

        with nc2:
            st.subheader("Detalles (Reason)")
            # El text area grande como en tu dibujo
            reason = st.text_area("Reason (Escribe aquí...)", height=150, key="nc_reason")
            
            # Script Stage
            opciones_script = [
            "All info provided", "No info provided", "the text message of the VCF", "the contact info verification", "the banking info verification", 
            "the enrollment plan verification", "the Yes/No verification questions", "the creditors verification", "the right of offset",
            "1st agreement (we aren't making payments until we get a settlement)", "2nd agreement (credit could be affected)", "3rd agreement (we aren't a government program)",
            "4th agreement (client can be sued)", "5th agreement (we aren't loaning you money)", "the part where we ask for the most recent statements, after the agreements.",
            "the harassing phone calls info", "the additional legal services info, at the end of the call."
            ]
            script_stage = st.selectbox("Call Progress:", opciones_script, key="nc_script")

            # Fila para Transfer y Return
            col_a, col_b = st.columns(2)
            with col_a:
                transfer = st.radio("Transfer Status:", ["Successful", "Unsuccessful"], horizontal=True, key="nc_trans")
                
                # --- LÓGICA CONDICIONAL (LO QUE PEDISTE) ---
                transfer_fail_reason = ""
                if transfer == "Unsuccessful":
                    st.markdown("🔻 **¿Por qué falló?**")
                    transfer_fail_reason = st.selectbox(
                        "Razón de fallo:", 
                        ["Voicemail", "Line Busy/Disconnected", "Language Barrier", "Refused Transfer", "Gatekeeper Block", "Hold Time Exceeded"]
                    )
            
            with col_b:
                return_call = st.radio("Return Call?", ["Yes", "No"], horizontal=True, key="nc_ret")

        st.markdown("---")
        if st.button("Generar Nota NOT COMPLETED", type="primary", key="btn_not"):
            # Limpieza de ID
            id_clean = ''.join(filter(str.isdigit, nc_id)) or "MISSING_ID"
            
            status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
            
            # Armamos el texto de transferencia
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
    # PESTAÑA 3: THIRD PARTY (Pendiente)
    # ==========================================
    with tab_third_party:
        st.warning("🚧 Third Party en construcción... (Próximamente)")


    # ==========================================
    # RESULTADO FINAL (COMÚN PARA TODOS)
    # ==========================================
    st.markdown("### 📋 Nota Generada")
    
    # Verificamos si hay algo en session state para mostrar
    if "nota_generada" in st.session_state and st.session_state.nota_generada:
        st.text_area("Copia tu nota aquí:", value=st.session_state.nota_generada, height=200)
    else:
        st.info("Completa los datos arriba y presiona Generar.")

if __name__ == "__main__":
    show()