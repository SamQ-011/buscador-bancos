import streamlit as st
import streamlit.components.v1 as components  # <--- NECESARIO PARA EL BOTÓN JS
from datetime import datetime
from sqlalchemy import text 

# --- FUNCIÓN DE BOTÓN DE COPIAR (JS LIMPIO) ---
def boton_copiar_portapapeles(texto_a_copiar, key_unica):
    """
    Botón HTML/JS que copia el texto al portapapeles sin mostrar bloques de código.
    """
    if not texto_a_copiar:
        return
        
    # Escapar caracteres para evitar errores de JS
    texto_seguro = texto_a_copiar.replace("`", "\`").replace("$", "\$").replace("{", "\{").replace("}", "\}")
    
    html_code = f"""
    <script>
    function copyToClipboard() {{
        const text = `{texto_seguro}`;
        navigator.clipboard.writeText(text).then(function() {{
            const btn = document.getElementById('btn_{key_unica}');
            btn.innerHTML = '✅ ¡Copiado!';
            btn.style.backgroundColor = '#d1e7dd';
            btn.style.borderColor = '#badbcc';
            setTimeout(() => {{
                btn.innerHTML = '📋 Copiar Nota';
                btn.style.backgroundColor = '#f0f2f6';
                btn.style.borderColor = '#d6d6d8';
            }}, 2000);
        }}, function(err) {{
            console.error('Error al copiar', err);
        }});
    }}
    </script>
    <button id="btn_{key_unica}" onclick="copyToClipboard()" style="
        width: 100%;
        background-color: #f0f2f6;
        color: #31333F;
        border: 1px solid #d6d6d8;
        padding: 0.5rem;
        border-radius: 8px;
        cursor: pointer;
        font-family: sans-serif;
        font-weight: 600;
        font-size: 14px;
        margin-top: 5px;
        transition: all 0.2s;
    ">
        📋 Copiar Nota
    </button>
    """
    components.html(html_code, height=50)

# --- BASE DE DATOS DE RAZONES ---
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

# --- FUNCIÓN DE GUARDADO ---
def guardar_log_supabase(agent_name, customer_name, cordoba_id, result_type, affiliate, info_until, client_lang):
    try:
        conn = st.connection("supabase", type="sql")
        now_iso = datetime.now().isoformat()
        
        query = """
            INSERT INTO "Logs" (created_at, agent, customer, cordoba_id, result, comments, affiliate, info_until, client_language)
            VALUES (:ts, :ag, :cu, :cid, :res, :com, :aff, :info, :lang)
        """
        params = {
            "ts": now_iso, "ag": agent_name, "cu": customer_name, "cid": cordoba_id, "res": result_type,
            "com": "", "aff": affiliate, "info": info_until, "lang": client_lang
        }
        with conn.session as s:
            s.execute(text(query), params)
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error guardando log: {e}")
        return False

def show():
    st.title("📝 Generador de Notas 2.0")

    # --- MEMORIA (INICIALIZACIÓN) ---
    if "nota_c_texto" not in st.session_state: st.session_state.nota_c_texto = ""
    if "nota_nc_texto" not in st.session_state: st.session_state.nota_nc_texto = ""
    if "nota_tp_texto" not in st.session_state: st.session_state.nota_tp_texto = ""
    if "nc_reason" not in st.session_state: st.session_state.nc_reason = ""

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
            st.markdown("##### 🟢 Datos de Venta")
            c1, c2 = st.columns(2)
            with c1: c_name = st.text_input("Cx Name", key="c_name")
            with c2: c_id = st.text_input("Cordoba ID", key="c_id")
            
            c3, c4 = st.columns(2)
            with c3: c_aff = st.text_input("Affiliate", key="c_aff")
            with c4: c_lang = st.selectbox("Language", ["English", "Spanish"], key="c_lang")
            
            st.markdown("---")
            
            b_col1, b_col2 = st.columns(2)
            
            # BOTÓN VISUALIZAR
            with b_col1:
                if st.button("👀 Previsualizar", use_container_width=True, key="vis_comp"):
                    if c_name and c_id:
                        id_clean = ''.join(filter(str.isdigit, c_id)) or "MISSING_ID"
                        texto = f"✅ WC Completed\nCX: {c_name} || CORDOBA-{id_clean}\nAffiliate: {c_aff}"
                        
                        # ACTUALIZAMOS LAS VARIABLES
                        st.session_state.nota_c_texto = texto
                        # [IMPORTANTE] FORZAMOS EL VALOR DEL WIDGET PARA QUE SE REFRESQUE
                        st.session_state.area_c_edit = texto 
                        
                        st.rerun() 
                    else:
                        st.toast("⚠️ Faltan datos")

            # BOTÓN GUARDAR
            with b_col2:
                # Se habilita solo si hay texto generado
                habilitado = True if st.session_state.nota_c_texto else False
                if st.button("💾 Guardar en BD", type="primary", use_container_width=True, key="save_comp", disabled=not habilitado):
                    id_clean = ''.join(filter(str.isdigit, c_id)) or "MISSING_ID"
                    exito = guardar_log_supabase(
                        agent_name=st.session_state.real_name,
                        customer_name=c_name, cordoba_id=id_clean, result_type="Completed",
                        affiliate=c_aff, info_until="All info provided", client_lang=c_lang
                    )
                    if exito:
                        st.toast("✅ Guardado en BD")

        with c_der:
            st.markdown("##### 📋 Nota Final")
            
            # TEXTAREA EDITABLE
            st.text_area(
                "Edita y luego copia:", 
                value=st.session_state.nota_c_texto,
                height=200,
                key="area_c_edit", # Esta llave se actualiza forzosamente arriba
                on_change=lambda: st.session_state.update(nota_c_texto=st.session_state.area_c_edit)
            )

            # BOTÓN DE COPIAR (Aparece si hay texto)
            if st.session_state.nota_c_texto:
                boton_copiar_portapapeles(st.session_state.nota_c_texto, "copy_comp")
                
            if not st.session_state.nota_c_texto:
                st.info("👈 Llena los datos y pulsa Previsualizar.")


    # ==========================================
    # PESTAÑA 2: NOT COMPLETED
    # ==========================================
    with tab_not_completed:
        nc_izq, nc_der = st.columns([2, 1])
        
        with nc_izq:
            st.markdown("##### 🔴 Datos del Fallo")
            c1, c2 = st.columns(2) 
            with c1: nc_name = st.text_input("Cx Name", key="nc_name")
            with c2: nc_id = st.text_input("Cordoba ID", key="nc_id")
            
            c3, c4 = st.columns(2)
            with c3: nc_aff = st.text_input("Affiliate", key="nc_aff")
            with c4: nc_lang = st.selectbox("Language", ["English", "Spanish"], key="nc_lang")

            st.markdown("**Progreso:**")
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
            script_stage = st.selectbox("Info Until / Progress:", opciones_script, key="nc_script")

            c5, c6 = st.columns(2)
            with c5:
                transfer = st.radio("Transfer Status:", ["Successful", "Unsuccessful"], horizontal=True, key="nc_trans")
                transfer_fail_reason = ""
                if transfer == "Unsuccessful":
                    transfer_fail_reason = st.selectbox("Razón Fallo:", ["Voicemail", "Line Busy", "Refused", "Gatekeeper", "Hold Time"], label_visibility="collapsed")
            
            with c6:
                return_call = st.radio("Return Call?", ["Yes", "No"], horizontal=True, key="nc_ret")

            st.divider()

            # --- CONSTRUCTOR DE RAZONES ---
            with st.container(border=True):
                rc_1, rc_2 = st.columns([1, 2])
                with rc_1:
                    cat_select = st.selectbox("Categoría:", list(REASON_OPTIONS.keys()), label_visibility="collapsed")
                with rc_2:
                    frases_cat = REASON_OPTIONS[cat_select]
                    frase_labels = [f["label"] for f in frases_cat]
                    frase_select = st.selectbox("Selecciona Razón:", frase_labels, label_visibility="collapsed")
                
                frase_data = next(f for f in frases_cat if f["label"] == frase_select)
                
                if frase_data["inputs"]:
                    cols = st.columns(len(frase_data["inputs"]) + 1)
                    user_inputs = []
                    for idx, label in enumerate(frase_data["inputs"]):
                        with cols[idx]:
                            val = st.text_input(label, key=f"input_{frase_select}_{idx}")
                            user_inputs.append(val)
                    with cols[-1]:
                        st.write("")
                        st.write("") 
                        if st.button("➕ Añadir", use_container_width=True):
                            if all(user_inputs):
                                texto_a_agregar = frase_data["template"].format(*user_inputs)
                                st.session_state.nc_reason += ("\n" + texto_a_agregar) if st.session_state.nc_reason else texto_a_agregar
                                st.rerun()
                            else:
                                st.toast("⚠️ Faltan datos")
                else:
                    if st.button(f"➕ Añadir '{frase_select}'"):
                        texto_a_agregar = frase_data["template"]
                        st.session_state.nc_reason += ("\n" + texto_a_agregar) if st.session_state.nc_reason else texto_a_agregar
                        st.rerun()

            st.text_area("Razón Final (Constructor):", key="nc_reason", height=100)
            st.markdown("---")
            
            nb_col1, nb_col2 = st.columns(2)
            with nb_col1:
                if st.button("👀 Previsualizar", use_container_width=True, key="vis_nc"):
                    if nc_name and st.session_state.nc_reason:
                        id_clean = ''.join(filter(str.isdigit, nc_id)) or "MISSING_ID"
                        status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
                        texto_transfer = transfer
                        if transfer == "Unsuccessful": texto_transfer = f"Unsuccessful ({transfer_fail_reason})"

                        texto = f"""❌ WC Not Completed – {status_titulo}
CX: {nc_name} || CORDOBA-{id_clean}

• Reason: {st.session_state.nc_reason}

• Call Progress: {script_stage}
• Transfer Status: {texto_transfer}
Affiliate: {nc_aff}"""
                        
                        # ACTUALIZAMOS LAS DOS VARIABLES (MEMORIA Y WIDGET)
                        st.session_state.nota_nc_texto = texto
                        st.session_state.area_nc_edit = texto 
                        st.rerun()
                    else:
                        st.toast("⚠️ Falta Nombre o Razón")

            with nb_col2:
                habilitado_nc = True if st.session_state.nota_nc_texto else False
                if st.button("💾 Guardar en BD", type="primary", use_container_width=True, key="save_nc", disabled=not habilitado_nc):
                    id_clean = ''.join(filter(str.isdigit, nc_id)) or "MISSING_ID"
                    status_titulo = "Returned" if return_call == "Yes" else "Not Returned"
                    exito = guardar_log_supabase(
                        agent_name=st.session_state.real_name,
                        customer_name=nc_name, cordoba_id=id_clean, result_type=f"Not Completed - {status_titulo}",
                        affiliate=nc_aff, info_until=script_stage, client_lang=nc_lang
                    )
                    if exito:
                        st.toast("💾 Fallo registrado")

        with nc_der:
            st.markdown("##### 📋 Nota Final")
            
            st.text_area(
                "Edita y luego copia:", 
                value=st.session_state.nota_nc_texto,
                height=450,
                key="area_nc_edit",
                on_change=lambda: st.session_state.update(nota_nc_texto=st.session_state.area_nc_edit)
            )

            if st.session_state.nota_nc_texto:
                boton_copiar_portapapeles(st.session_state.nota_nc_texto, "copy_nc")
                
                if st.button("🔄 Limpiar Campos", key="new_nc"):
                    st.session_state.nota_nc_texto = ""
                    st.session_state.nc_reason = ""
                    st.rerun()
            else:
                st.info("👈 Construye la razón y pulsa Previsualizar.")


    # ==========================================
    # PESTAÑA 3: THIRD PARTY
    # ==========================================
    with tab_third_party:
        tp_izq, tp_der = st.columns([1, 1])
        
        with tp_izq:
            st.subheader("👥 Personas Presentes")
            with st.container(border=True):
                num_terceros = st.number_input("Cantidad de personas extra:", min_value=1, value=1, step=1)
                lista_terceros = [] 
                for i in range(num_terceros):
                    st.markdown(f"**Persona #{i+1}**")
                    c_p1, c_p2 = st.columns(2)
                    with c_p1: nom = st.text_input("Nombre", key=f"p_nom_{i}").strip()
                    with c_p2: rel = st.text_input("Relación", placeholder="Ej: Father, Wife...", key=f"p_rel_{i}").strip()
                    if nom and rel: lista_terceros.append({'nombre': nom, 'relacion': rel})

            st.markdown("---")
            if st.button("Generar Párrafo Legal", type="primary", key="btn_tp"):
                if not lista_terceros:
                    st.warning("⚠️ Debes llenar los nombres y relaciones.")
                else:
                    personas_fmt = [f"{p['nombre']} Customer's {p['relacion']}" for p in lista_terceros]
                    texto_personas = ", ".join(personas_fmt)
                    sujeto = "these people" if len(lista_terceros) > 1 else "this person"
                    parrafo = (
                        f"✅ Third Party Authorization:\n"
                        f"Third party: {texto_personas}\n"
                        f"The customer authorizes {sujeto} to be present during the call."
                    )
                    st.session_state.nota_tp_texto = parrafo
                    st.rerun()

        with tp_der:
            st.subheader("⚖️ Resultado Legal")
            st.text_area("Texto Legal:", value=st.session_state.nota_tp_texto, height=200)
            if st.session_state.nota_tp_texto:
                boton_copiar_portapapeles(st.session_state.nota_tp_texto, "copy_tp")

if __name__ == "__main__":
    show()