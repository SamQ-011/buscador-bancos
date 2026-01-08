import time
import re
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import pytz

# --- IMPORTACIONES ---
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

import services.notes_service as note_service

# ==============================================================================
# 0. CONSTANTES & CONFIGURACIÓN
# ==============================================================================

# Lista de motivos de fallo en transferencia (Solicitado por el usuario)
TRANSFER_FAIL_REASONS = [
    "Unsuccessful, number was not in service.",
    "Unsuccessful, attempted to contact sales back with no success.",
    "Unsuccessful, the SA was unavailable.",
    "Unsuccessful, the call was concluded before the verification outcome was completed.",
    "Unsuccessful, the Cx disconnected the call before I could transfer the call back to Sales.",
    "Unsuccessful, the Cx disconnected the call and requested for a call back later.",
    "Unsuccessful, I tried to transfer the client to their representative by calling the company’s extension, but no one answered.",
    "Unsuccessful, I tried to transfer the client to their representative by calling the company’s extension, but it goes straight to voicemail.",
    "Unsuccesful, the client is busy and will be waiting for their representative’s call."
]

# ==============================================================================
# 1. UTILS & HELPERS
# ==============================================================================

def _is_duplicate_submission(record_id: str, cooldown: int = 60) -> bool:
    now = time.time()
    if "last_save_time" in st.session_state:
        elapsed = now - st.session_state.last_save_time
        if elapsed < cooldown and st.session_state.get("last_save_id") == record_id:
            return True
    return False

def _register_successful_save(record_id: str):
    st.session_state.last_save_time = time.time()
    st.session_state.last_save_id = record_id

def _inject_copy_button(text_content: str, unique_key: str):
    """
    Botón robusto para copiar (Versión Lab Parser).
    """
    if not text_content: return
    safe_text = (text_content.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("{", "\\{").replace("}", "\\}"))
    
    html = f"""
    <script>
    function copyToClipboard_{unique_key}() {{
        const text = `{safe_text}`;
        const btn = document.getElementById('btn_{unique_key}');
        const updateBtn = () => {{
            btn.innerHTML = '✅ Copied!';
            btn.style.backgroundColor = '#d1e7dd';
            btn.style.color = '#0f5132';
            btn.style.borderColor = '#badbcc';
            setTimeout(() => {{ 
                btn.innerHTML = '📋 Copy Note'; 
                btn.style.backgroundColor = '#f0f2f6'; 
                btn.style.color = '#31333F'; 
                btn.style.borderColor = '#d6d6d8';
            }}, 2000);
        }};
        
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {{
            document.execCommand('copy');
            updateBtn();
        }} catch (err) {{
            console.error('Fallback copy failed', err);
        }}
        document.body.removeChild(textArea);
    }}
    </script>
    <button id="btn_{unique_key}" onclick="copyToClipboard_{unique_key}()" style="
        width: 100%; background-color: #f0f2f6; color: #31333F; border: 1px solid #d6d6d8; 
        padding: 0.6rem; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; margin-top: 0px;">
        📋 Copy Note
    </button>
    """
    components.html(html, height=50)

# ==============================================================================
# 2. LOGIC (Parser & Recalculator del Lab)
# ==============================================================================

def parse_crm_text(raw_text):
    data = {}
    
    # --- 1. ID EXTRACTION ---
    match_specific_id = re.search(r"Customer ID\s*(CORDOBA-\d+)", raw_text, re.IGNORECASE)
    match_any_id = re.search(r"(CORDOBA-\d+)", raw_text)

    if match_specific_id:
        data['cordoba_id'] = match_specific_id.group(1)
    elif match_any_id:
        data['cordoba_id'] = match_any_id.group(1)

    # --- 2. NAME EXTRACTION ---
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    if lines:
        raw_line = lines[0]
        clean_name = re.sub(r"\s*Purchaser\s+\d+\s+Eligible.*", "", raw_line, flags=re.IGNORECASE)
        clean_name = re.sub(r"Co-Applicant:.*", "", clean_name, flags=re.IGNORECASE)
        data['raw_name_guess'] = clean_name.strip().title()

    # --- 3. AFFILIATE EXTRACTION ---
    affiliate_patterns = [
        r"Affiliate Marketing Company\s*(.*)",
        r"Marketing Company\s*(.*)",
        r"Assigned Company\s*(.*)" 
    ]

    for pattern in affiliate_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match and len(match.group(1).strip()) > 1:
            data['marketing_company'] = match.group(1).strip()
            break 
    
    # --- 4. LANGUAGE ---
    match_lang = re.search(r"Language:\s*(\w+)", raw_text, re.IGNORECASE)
    if match_lang: data['language'] = match_lang.group(1)

    return data

def match_affiliate(parsed_affiliate, db_options):
    if not parsed_affiliate: return None
    parsed_clean = parsed_affiliate.lower().strip()
    for op in db_options:
        if op.lower().strip() == parsed_clean: return op
    for op in db_options:
        if parsed_clean in op.lower(): return op
    return None

# --- RECALCULAR NOTA (Lógica Reactiva) ---
def recalc_note():
    """Genera el texto de la nota basado en los inputs actuales."""
    # 1. Parsear datos
    raw_text = st.session_state.get("lp_text", "")
    parsed = parse_crm_text(raw_text) if raw_text else {}
    
    # 2. Obtener valores de inputs
    outcome = st.session_state.get("lp_outcome", "❌ Not Completed")
    reason = st.session_state.get("lp_reason", "")
    
    # 3. Afiliado (Auto-detect)
    try:
        conn = get_db_connection()
        affiliates_list = sorted(note_service.fetch_affiliates_list(conn))
    except:
        affiliates_list = []

    raw_aff = parsed.get('marketing_company', '')
    suggested_aff = match_affiliate(raw_aff, affiliates_list)
    final_aff = suggested_aff if suggested_aff else (raw_aff if raw_aff else "Unknown Affiliate")
    
    # Datos básicos
    name = parsed.get('raw_name_guess', 'unknown')
    cid = parsed.get('cordoba_id', 'unknown')

    # 4. Construir String
    if "Not Completed" in outcome:
        stage = st.session_state.get("lp_stage", "All info provided")
        ret = st.session_state.get("lp_return", "No")
        
        # --- LÓGICA DE TRANSFERENCIA (NUEVA) ---
        base_trans = st.session_state.get("lp_trans", "Unsuccessful")
        
        if base_trans == "Unsuccessful":
            # Si es Unsuccessful, buscamos el motivo detallado en la sesión
            # Si aún no existe en sesión (primera carga), usamos el primero de la lista
            detailed_reason = st.session_state.get("lp_trans_reason", TRANSFER_FAIL_REASONS[0])
            final_trans_status = detailed_reason
        else:
            final_trans_status = "Successful"

        stat_title = "Returned" if ret == "Yes" else "Not Returned"
        
        # Construcción final usando el motivo detallado
        final_note = f"❌ WC Not Completed – {stat_title}\nCX: {name} || {cid}\n\n• Reason: {reason}\n\n• Call Progress: {stage}\n• Transfer Status: {final_trans_status}\nAffiliate: {final_aff}"
    else:
        final_note = f"✅ WC Completed\nCX: {name} || {cid}\nAffiliate: {final_aff}"

    # 5. ACTUALIZAR EL CUADRO DE TEXTO
    st.session_state.final_note_content = final_note

def limpiar_lab():
    st.session_state.lp_text = ""
    st.session_state.lp_reason = ""
    st.session_state.final_note_content = ""

# ==============================================================================
# 3. MODAL DE CONFIRMACIÓN
# ==============================================================================

@st.dialog("🛡️ Confirm Submission")
def render_confirm_modal(conn, payload: dict):
    st.write("Verifica los detalles antes de guardar.")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Customer")
        st.info(f"{payload['customer']}\n{payload['cordoba_id']}")
    with c2:
        st.caption("Outcome")
        if "Completed" in payload['result'] and "Not" not in payload['result']:
            st.success(f"🏆 {payload['result']}")
        else:
            st.error(f"❌ {payload['result']}")
        st.caption("Affiliate")
        st.text(payload['affiliate'])

    if payload['comments']:
        st.caption("Reason")
        st.warning(payload['comments'])
        
    with st.expander("View Full Note Content"):
        st.code(payload.get('full_note_content', 'No content'))

    st.divider()
    col_cancel, col_ok = st.columns([1, 1])
    if col_cancel.button("Cancel", use_container_width=True):
        st.rerun()
    if col_ok.button("✅ Confirm & Save", type="primary", use_container_width=True):
        try:
            if note_service.commit_log(conn, payload):
                _register_successful_save(payload['cordoba_id'])
                st.balloons()
                st.toast("Saved successfully!", icon="💾")
                time.sleep(1.0)
                st.rerun()
        except Exception as e:
            st.error(f"Error saving: {e}")

# ==============================================================================
# 4. VISTA PRINCIPAL
# ==============================================================================

def show():
    st.title("📝 Notes Generator")
    conn = get_db_connection()
    
    # --- INICIALIZACIÓN DE ESTADO ---
    if "final_note_content" not in st.session_state: st.session_state.final_note_content = ""
    if "lp_text" not in st.session_state: st.session_state.lp_text = ""
    if "lp_reason" not in st.session_state: st.session_state.lp_reason = ""
    if "lp_outcome" not in st.session_state: st.session_state.lp_outcome = "❌ Not Completed"
    
    # Variables Third Party
    if "nota_tp_texto" not in st.session_state: st.session_state.nota_tp_texto = ""

    # Datos Usuario
    user_id = st.session_state.get("user_id", None)
    username = st.session_state.get("username", "Unknown")

    # --- PESTAÑAS ---
    t_gen, t_legal = st.tabs(["✨ Smart Generator", "👥 Third Party"])

    # ---------------------------------------------------------
    # TAB 1: SMART GENERATOR
    # ---------------------------------------------------------
    with t_gen:
        col_left, col_right = st.columns([1, 1.2])

        # --- IZQUIERDA: INPUT Y CONFIGURACIÓN ---
        with col_left:
            st.text_area("Paste", height=150, key="lp_text", 
                         label_visibility="collapsed", 
                         placeholder="Paste Forth Profile here...",
                         on_change=recalc_note)
            
            st.divider()

            st.radio("Outcome", ["❌ Not Completed", "✅ Completed"], 
                     horizontal=True, 
                     label_visibility="collapsed",
                     key="lp_outcome",
                     on_change=recalc_note)
            
            # Controles condicionales
            if "Not Completed" in st.session_state.lp_outcome:
                st.caption("Call Details:")
                c1, c2 = st.columns([1.5, 1])
                with c1:
                    progress_opts = [
                        "All info provided", "No info provided", "the text message of the VCF", 
                        "the contact info verification", "the banking info verification", 
                        "the enrollment plan verification", "the Yes/No verification questions", 
                        "the creditors verification", "the right of offset",
                        "1st agreement (settlement)", "2nd agreement (credit affected)", 
                        "3rd agreement (not gov program)", "4th agreement (lawsuit)", 
                        "5th agreement (not loan)", "recent statements request",
                        "harassing calls info", "additional legal services info", "Intro"
                    ]
                    st.selectbox("Progress", progress_opts, 
                                 key="lp_stage", label_visibility="collapsed", on_change=recalc_note)
                with c2:
                    st.radio("Return?", ["Yes", "No"], horizontal=True, key="lp_return", on_change=recalc_note)
                    # Selector de Transferencia
                    st.radio("Transfer?", ["Successful", "Unsuccessful"], horizontal=True, key="lp_trans", on_change=recalc_note)
                
                # --- NUEVO: SELECTOR DE RAZONES DE FALLO ---
                # Solo aparece si seleccionan "Unsuccessful"
                if st.session_state.get("lp_trans") == "Unsuccessful":
                    st.selectbox(
                        "Reason for failed transfer:", 
                        TRANSFER_FAIL_REASONS,
                        key="lp_trans_reason",
                        on_change=recalc_note,
                        help="Select the specific reason why the transfer failed."
                    )
            else:
                st.success(f"Sale Ready")

        # --- DERECHA: NOTA FINAL Y ACCIONES ---
        with col_right:
            if "Not Completed" in st.session_state.lp_outcome:
                st.text_area("Reason (Internal Comment):", key="lp_reason", height=80, 
                             placeholder="Type generic failure reason...", on_change=recalc_note)
                note_height = 250
            else:
                note_height = 150

            # CUADRO DE TEXTO EDITABLE
            st.text_area("Final Note", key="final_note_content", height=note_height, label_visibility="collapsed")

            # BOTONES
            b_save, b_reset = st.columns([2, 1])
            
            # 1. COPIAR
            _inject_copy_button(st.session_state.final_note_content, f"gen_copy_{len(st.session_state.final_note_content)}")
            
            st.write("") 

            # 2. GUARDAR
            with b_save:
                # Preparamos datos
                parsed_check = parse_crm_text(st.session_state.lp_text)
                name = parsed_check.get('raw_name_guess', 'unknown')
                cid = parsed_check.get('cordoba_id', 'unknown')
                clean_id_num = ''.join(filter(str.isdigit, cid))
                
                # Afiliado final
                affiliates_list = sorted(note_service.fetch_affiliates_list(conn))
                raw_aff = parsed_check.get('marketing_company', '')
                sug_aff = match_affiliate(raw_aff, affiliates_list)
                final_aff = sug_aff if sug_aff else (raw_aff if raw_aff else "Unknown")
                
                save_ready = bool(name != 'unknown' and cid != 'unknown' and st.session_state.final_note_content)

                if st.button("💾 Save Log", type="primary", use_container_width=True, disabled=not save_ready):
                    if _is_duplicate_submission(clean_id_num):
                        st.warning(f"⚠️ Duplicate for ID {clean_id_num}")
                    else:
                        payload = {
                            "user_id": user_id if user_id else 1,
                            "username": username,
                            "customer": name,
                            "cordoba_id": clean_id_num,
                            "result": st.session_state.lp_outcome.replace("❌ ", "").replace("✅ ", ""),
                            "affiliate": final_aff,
                            "info_until": st.session_state.get("lp_stage", "Completed"),
                            "client_language": parsed_check.get('language', 'Unknown'),
                            "comments": st.session_state.get("lp_reason", ""),
                            "full_note_content": st.session_state.final_note_content
                        }
                        render_confirm_modal(conn, payload)

            # 3. RESET
            with b_reset:
                st.button("🔄 Reset", use_container_width=True, on_click=limpiar_lab)

    # ---------------------------------------------------------
    # TAB 2: THIRD PARTY
    # ---------------------------------------------------------
    with t_legal:
        tp_l, tp_r = st.columns([1, 1])
        with tp_l:
            st.subheader("👥 Attendees")
            with st.container(border=True):
                qty = st.number_input("Count:", min_value=1, value=1, step=1)
                attendees = [] 
                for i in range(qty):
                    st.markdown(f"**Person #{i+1}**")
                    c_n, c_r = st.columns(2)
                    nm = c_n.text_input("Name", key=f"p_nom_{i}").strip()
                    rl = c_r.text_input("Relation", placeholder="e.g. Spouse", key=f"p_rel_{i}").strip()
                    if nm and rl: attendees.append({'name': nm, 'rel': rl})

            st.markdown("---")
            if st.button("Generate Legal Script", type="primary", key="btn_tp"):
                if not attendees:
                    st.warning("⚠️ Inputs empty.")
                else:
                    fmt_list = [f"{p['name']} Customer's {p['rel']}" for p in attendees]
                    joined = ", ".join(fmt_list)
                    pronoun = "these people" if len(attendees) > 1 else "this person"
                    txt = (f"✅ Third Party Authorization:\nThird party: {joined}\nThe customer authorizes {pronoun} to be present during the call.")
                    
                    st.session_state.nota_tp_texto = txt
                    st.session_state.area_tp_edit = txt 
                    st.rerun()

        with tp_r:
            st.subheader("⚖️ Legal Text")
            st.text_area("Script:", 
                         height=200, 
                         key="area_tp_edit",
                         on_change=lambda: st.session_state.update(nota_tp_texto=st.session_state.area_tp_edit))
            
            if st.session_state.area_tp_edit:
                _inject_copy_button(st.session_state.area_tp_edit, "copy_tp")

    # ---------------------------------------------------------
    # FOOTER: HISTORIAL RECIENTE
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader(f"📜 Recent Activity ({username})")
    
    df_hist = note_service.fetch_agent_history(conn, username)
    if not df_hist.empty:
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
    else:
        st.info("No records found for today.")

if __name__ == "__main__":

    show()
