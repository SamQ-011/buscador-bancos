import streamlit as st

# --- BASE DE DATOS DE RAZONES PREDEFINIDAS ---
# Aquí configuramos qué frases existen y qué datos piden
REASON_OPTIONS = {
    "📞 Contact / Transfer Issues": [
        {"label": "Call dropped / No answer", "template": "Call dropped. I tried to call back without answer. Please call the Cx back.", "inputs": []},
        {"label": "Transfer failed / No answer", "template": "Cx wasn't transferred to me. I tried to call back, without answer.", "inputs": []},
        {"label": "Cx requested Sales Agent", "template": "At the end of the call, the Cx expressed concern about proceeding with the enrollment process and requested to speak with the sales agent again before moving forward.", "inputs": []},
    ],
    "🆔 Identity Verification (PII)": [
        {"label": "DOB Incorrect", "template": "The DOB is incorrect, the correct one is: {}", "inputs": ["Correct DOB"]},
        {"label": "SSN Incorrect", "template": "The SSN is incorrect, the correct one is: {}", "inputs": ["Correct SSN"]},
        {"label": "Unable to verify SSN", "template": "The Cx was unable to verify the SSN.", "inputs": []},
        {"label": "Declined Personal Info", "template": "The Customer declined to provide personal information for verification.", "inputs": []},
    ],
    "🏦 Banking Information": [
        {"label": "Bank Name Incorrect", "template": "The bank name listed for the client’s account is incorrect. The correct name should be: {}", "inputs": ["Correct Bank Name"]},
        {"label": "Account # Incorrect", "template": "The account number is incorrect. The correct number is: {}", "inputs": ["Correct Account #"]},
        {"label": "Routing # Incorrect", "template": "The routing number is incorrect. The correct number is: {}", "inputs": ["Correct Routing #"]},
        {"label": "Unable to verify Bank Info", "template": "The Cx was unable to verify the account number and routing number.", "inputs": []},
        {"label": "Refused Banking Info", "template": "The Cx refused to provide their banking info.", "inputs": []},
        # Este es especial, tiene 3 inputs y saltos de línea
        {"label": "FULL Banking Correction", "template": "According to the Cx, the banking info should be:\n      Bank: {}\n      Account #: {}\n      Routing #: {}", "inputs": ["Bank Name", "Account #", "Routing #"]},
    ],
    "📅 Program Details (Payments/Dates)": [
        {"label": "Payment Amount Incorrect", "template": "According to the Cx, their payments should be {}, instead of {}.", "inputs": ["Correct Amount", "Wrong Amount"]},
        {"label": "1st Payment Date Incorrect", "template": "According to the Cx, the first payment date is incorrect. The correct date should be: {}", "inputs": ["Correct Date"]},
        {"label": "Program Length Incorrect", "template": "According to the Cx, the program length should be {} months, instead of {} months.", "inputs": ["Correct Months", "Wrong Months"]},
        {"label": "Unsure about Secured Debts", "template": "The Cx is unsure whether any of the enrolled debts are secured.", "inputs": []},
        {"label": "Insufficient Income", "template": "The Cx stated that he/she does not have sufficient income to afford the program.", "inputs": []},
    ],
    "🚫 Objections / Legal": [
        {"label": "Active Military", "template": "The Cx stated that he/she is active military, making him/her ineligible for the program.", "inputs": []},
        {"label": "Does not recognize debt", "template": "The Cx does not recognize this debt and requires clarification before enrolling in the program: {}", "inputs": ["Which debt?"]},
        {"label": "Wants to ADD debt", "template": "Cx wants to add another debt.", "inputs": []},
        {"label": "Remove specific debt", "template": "Cx doesn't want to include this debt in the program: {}", "inputs": ["Which debt?"]},
        {"label": "Right of Offset Concern", "template": "The Cx is concerned that the right of offset may apply.", "inputs": []},
        {"label": "Immediate Payments Misconception", "template": "The Cx believed we would begin making payments to the creditors immediately. We clarified that, under the program, payments are only made once an agreement has been reached with the creditors. However, the Cx disagreed.", "inputs": []},
        {"label": "Credit Score Concern", "template": "The Cx is concerned about their credit score being negatively affected. We explained that credit may be impacted during the program, but the Cx disagreed.", "inputs": []},
        {"label": "Government Program Misconception", "template": "The Cx believed we were a government program. We clarified that we are a private legal firm, not a government program. However, the Cx chose not to continue with us.", "inputs": []},
        {"label": "Lawsuit/Sued Concern", "template": "The Cx expressed concern about the possibility of being sued by their creditors. We explained that, if this occurs, they will have our legal representation. However, the Cx was not comfortable with this.", "inputs": []},
        {"label": "Loan Misconception", "template": "The Cx thought that we were going to loan him money so that the Cx won't have to pay their creditors no more and pay to us instead.", "inputs": []},
        {"label": "Consolidation Misconception", "template": "The Cx believed we were a consolidation program. We clarified that we are a settlement program, where the Cx makes payments to us and we use those funds to settle their debts. However, the Cx chose not to continue with us.", "inputs": []},
    ]
}

def show():
    st.title("📝 Generador de Notas 2.0")

    # --- GESTIÓN DE MEMORIA ---
    if "nota_completed" not in st.session_state:
        st.session_state.nota_completed = ""
    if "nota_not_completed" not in st.session_state:
        st.session_state.nota_not_completed = ""
    if "nota_third_party" not in st.session_state:
        st.session_state.nota_third_party = ""
    
    # Memoria específica para el cajón de Reason (para que el constructor funcione)
    if "nc_reason" not in st.session_state:
        st.session_state.nc_reason = ""

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
        c_izq, c_der = st.columns([1, 1])
        with c_izq:
            st.subheader("📝 Datos")
            c_name = st.text_input("Cx Name", key="c_name")
            c_id = st.text_input("Cordoba ID", key="c_id")
            c_aff = st.text_input("Affiliate", key="c_aff")
            st.markdown("---")
            
            if st.button("Generar Nota COMPLETED", type="primary", key="btn_comp"):
                id_clean = ''.join(filter(str.isdigit, c_id)) or "MISSING_ID"
                texto = f"✅ WC Completed\nCX: {c_name} CORDOBA-{id_clean}\nAffiliate: {c_aff}"
                st.session_state.nota_completed = texto
                st.rerun()

        with c_der:
            st.subheader("📋 Resultado")
            st.text_area("Copia aquí:", key="nota_completed", height=300)


    # ==========================================
    # PESTAÑA 2: NOT COMPLETED (CONSTRUCTOR INTELIGENTE)
    # ==========================================
    with tab_not_completed:
        # Usamos columnas con proporción 2:1 para dar más espacio a los inputs
        nc_izq, nc_der = st.columns([2, 1])
        
        with nc_izq:
            st.markdown("##### 👤 Datos del Cliente")
            
            # --- FILA 1: DATOS PERSONALES (Horizontal) ---
            col1, col2, col3 = st.columns([2, 1, 1]) 
            with col1:
                nc_name = st.text_input("Cx Name", key="nc_name")
            with col2:
                nc_id = st.text_input("Cordoba ID", key="nc_id")
            with col3:
                nc_aff = st.text_input("Affiliate", key="nc_aff")

            st.markdown("##### 📞 Logística de la Llamada")

            # --- FILA 2: DATOS DE LA LLAMADA (Horizontal) ---
            col4, col5, col6 = st.columns(3)
            with col4:
                opciones_script = [
                    "All info provided", "No info provided", "the text message of the VCF", 
                    "the contact info verification", "the banking info verification", 
                    "the enrollment plan verification", "the Yes/No verification questions", 
                    "the creditors verification", "the right of offset",
                    "1st agreement (settlement)", "2nd agreement (credit affected)", 
                    "3rd agreement (not gov program)", "4th agreement (lawsuit)", 
                    "5th agreement (not loan)", "recent statements request",
                    "harassing calls info", "additional legal services info"
                ]
                script_stage = st.selectbox("Call Progress:", opciones_script, key="nc_script")
            
            with col5:
                # Usamos radio horizontal para ahorrar clics (un clic es más rápido que abrir selectbox)
                transfer = st.radio("Transfer Status:", ["Successful", "Unsuccessful"], horizontal=True, key="nc_trans")
                if transfer == "Unsuccessful":
                    transfer_fail_reason = st.selectbox("Razón Fallo:", ["Voicemail", "Line Busy", "Refused", "Gatekeeper", "Hold Time"], label_visibility="collapsed")
            
            with col6:
                return_call = st.radio("Return Call?", ["Yes", "No"], horizontal=True, key="nc_ret")

            st.divider() # Línea visual suave

            # --- FILA 3: LA RAZÓN (El Constructor) ---
            st.markdown("##### 📝 Razón del 'Not Completed'")
            
            # CONSTRUCTOR (Dentro de un contenedor para darle orden visual)
            with st.container(border=True):
                # 1. Selector de Categoría y Frase en una línea
                rc_1, rc_2 = st.columns([1, 2])
                with rc_1:
                    cat_select = st.selectbox("Categoría:", list(REASON_OPTIONS.keys()), label_visibility="collapsed")
                with rc_2:
                    frases_cat = REASON_OPTIONS[cat_select]
                    frase_labels = [f["label"] for f in frases_cat]
                    frase_select = st.selectbox("Selecciona Razón:", frase_labels, label_visibility="collapsed")
                
                # Datos de la frase seleccionada
                frase_data = next(f for f in frases_cat if f["label"] == frase_select)
                
                # Inputs dinámicos y Botón en la misma fila si es posible
                if frase_data["inputs"]:
                    cols = st.columns(len(frase_data["inputs"]) + 1) # +1 para el botón
                    user_inputs = []
                    
                    # Generar inputs
                    for idx, label in enumerate(frase_data["inputs"]):
                        with cols[idx]:
                            val = st.text_input(label, key=f"input_{frase_select}_{idx}")
                            user_inputs.append(val)
                    
                    # Botón al final de los inputs
                    with cols[-1]:
                        st.write("") # Espaciador para alinear verticalmente
                        st.write("") 
                        if st.button("➕ Añadir", use_container_width=True):
                            try:
                                if all(user_inputs): # Verificar que no estén vacíos
                                    texto_a_agregar = frase_data["template"].format(*user_inputs)
                                    if st.session_state.nc_reason:
                                        st.session_state.nc_reason += "\n" + texto_a_agregar
                                    else:
                                        st.session_state.nc_reason = texto_a_agregar
                                    st.rerun()
                                else:
                                    st.toast("⚠️ Faltan datos por llenar")
                            except IndexError:
                                pass
                else:
                    # Si no hay inputs, botón directo
                    if st.button(f"➕ Añadir '{frase_select}'"):
                        texto_a_agregar = frase_data["template"]
                        if st.session_state.nc_reason:
                            st.session_state.nc_reason += "\n" + texto_a_agregar
                        else:
                            st.session_state.nc_reason = texto_a_agregar
                        st.rerun()

            # Area de Texto Final (Donde se acumula todo)
            st.text_area("Texto Final de la Razón (Editable):", key="nc_reason", height=100)

            # --- BOTÓN GENERAR FINAL ---
            st.markdown("---")
            if st.button("🚀 Generar Nota Final", type="primary", use_container_width=True, key="btn_not"):
                id_clean = ''.join(filter(str.isdigit, nc_id)) or "MISSING_ID"
                status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
                
                texto_transfer = transfer
                if transfer == "Unsuccessful":
                    texto_transfer = f"Unsuccessful ({transfer_fail_reason})"

                texto = f"""❌ WC Not Completed – {status_titulo}
CX: {nc_name} CORDOBA-{id_clean}

• Reason: {st.session_state.nc_reason}

• Call Progress: {script_stage}
• Transfer Status: {texto_transfer}
Affiliate: {nc_aff}"""
                
                st.session_state.nota_not_completed = texto
                st.rerun()

        with nc_der:
            st.subheader("📋 Copiar:")
            st.text_area("Resultado:", key="nota_not_completed", height=550)
            if st.session_state.nota_not_completed:
                st.info("👆 Selecciona todo (Ctrl+A) y copia (Ctrl+C)")


    # ==========================================
    # PESTAÑA 3: THIRD PARTY
    # ==========================================
    with tab_third_party:
        tp_izq, tp_der = st.columns([1, 1])
        with tp_izq:
            st.subheader("👥 Personas Presentes")
            num_terceros = st.number_input("Cantidad de personas extra:", min_value=1, value=1, step=1)
            lista_terceros = [] 
            for i in range(num_terceros):
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    nom = st.text_input(f"Nombre", key=f"p_nom_{i}")
                with c_p2:
                    rel = st.text_input(f"Relación", placeholder="Mother...", key=f"p_rel_{i}")
                lista_terceros.append({'nombre': nom, 'relacion': rel})

            st.markdown("---")
            if st.button("Generar Párrafo Legal", type="primary", key="btn_tp"):
                if num_terceros == 1:
                    nombre_p = lista_terceros[0]['nombre']
                    relacion_p = lista_terceros[0]['relacion']
                    parrafo = f"Third party: \nThe customer's {relacion_p} {nombre_p}.\nThe customer authorizes his wife to be present during the call."
                else:
                    nombres = ", ".join([p['nombre'] for p in lista_terceros])
                    relaciones = ", ".join([p['relacion'] for p in lista_terceros])
                    parrafo = f"Third party: \nThe customer's {relaciones} {nombres}./nThe customer authorizes his wife to be present during the call."
                st.session_state.nota_third_party = parrafo
                st.rerun()

        with tp_der:
            st.subheader("⚖️ Third party")
            st.text_area("Nota:", key="nota_third_party", height=300)

if __name__ == "__main__":
    show()