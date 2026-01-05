# vistas/notas.py
import time
import streamlit as st
import streamlit.components.v1 as components

# --- IMPORTACIONES MODULARIZADAS ---
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

# Importamos la lógica de negocio y los datos estáticos
import services.notes_service as note_service
from config.templates import REASON_TEMPLATES

# --- Utils de Interfaz (UI Only) ---

def _is_duplicate_submission(record_id: str, cooldown: int = 60) -> bool:
    """Evita doble clic en el botón de guardar (Frontend logic)."""
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
    """Componente visual de botón de copia."""
    if not text_content: return
    safe_text = (text_content.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("{", "\\{").replace("}", "\\}"))
    html = f"""
    <script>
    function copyToClipboard() {{
        const text = `{safe_text}`;
        const updateBtn = () => {{
            const btn = document.getElementById('btn_{unique_key}');
            btn.innerHTML = '✅ Copied!';
            btn.style.backgroundColor = '#d1e7dd';
            setTimeout(() => {{ btn.innerHTML = '📋 Copiar Nota'; btn.style.backgroundColor = '#f0f2f6'; }}, 2000);
        }};
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(text).then(updateBtn);
        }} else {{
            const textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            updateBtn();
        }}
    }}
    </script>
    <button id="btn_{unique_key}" onclick="copyToClipboard()" style="
        width: 100%; background-color: #f0f2f6; color: #31333F; border: 1px solid #d6d6d8; 
        padding: 0.6rem; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; margin-top: 8px;">
        📋 Copiar Nota
    </button>
    """
    components.html(html, height=60)

# --- Callbacks de Limpieza ---

def limpiar_form_completed():
    keys = ["c_name", "c_id", "c_aff", "nota_c_texto", "area_c_edit"]
    for k in keys:
        if k in st.session_state: st.session_state[k] = ""

def limpiar_form_not_completed():
    keys = ["nc_name", "nc_id", "nc_aff", "nc_reason", "nota_nc_texto", "area_nc_edit"]
    for k in keys:
        if k in st.session_state: st.session_state[k] = ""

# --- Modales ---

@st.dialog("🛡️ Confirm Submission")
def render_confirm_modal(conn, payload: dict):
    st.write("Please verify details before committing to database.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Cordoba ID")
        st.info(payload['cordoba_id'])
        st.caption("Customer Name")
        st.info(payload['customer'])
    with c2:
        st.caption("Result")
        if "Completed" in payload['result'] and "Not" not in payload['result']:
            st.success(f"🏆 {payload['result']}")
        else:
            st.error(f"❌ {payload['result']}")
        st.caption("Agent")
        st.text(payload['username'])

    st.divider()
    
    col_cancel, col_ok = st.columns([1, 1])
    if col_cancel.button("Cancel", use_container_width=True):
        st.rerun()
            
    if col_ok.button("✅ Confirm & Save", type="primary", use_container_width=True):
        # LLAMADA AL SERVICIO (Lógica separada)
        if note_service.commit_log(conn, payload):
            _register_successful_save(payload['cordoba_id'])
            
            if "Completed" in payload['result'] and "Not" not in payload['result']:
                st.balloons()
            else:
                st.toast("Record saved successfully", icon="💾")
            
            time.sleep(1.0)
            st.rerun()

# --- Vista Principal ---

def show():
    st.title("📝 Notes Generator")
    
    conn = get_db_connection()

    # Initialization
    keys_defaults = {
        "nota_c_texto": "", "nota_nc_texto": "", "nota_tp_texto": "", 
        "nc_reason": "", "area_c_edit": "", "area_nc_edit": "",
        "c_name": "", "c_id": "", "c_aff": "", 
        "nc_name": "", "nc_id": "", "nc_aff": ""
    }
    for k, default in keys_defaults.items():
        if k not in st.session_state: st.session_state[k] = default
    
    user_id = st.session_state.get("user_id", None)
    username = st.session_state.get("username", "Unknown")

    # CARGA DE DATOS DESDE SERVICIO
    affiliates_list = note_service.fetch_affiliates_list(conn)
    if not affiliates_list:
        affiliates_list = ["Error loading list", "Patriot", "Cordoba Legal"]
    
    t_comp, t_not_comp, t_legal = st.tabs(["✅ WC Completed", "❌ WC Not Completed", "👥 Third Party"])

    # 1. COMPLETED FLOW
    with t_comp:
        c1, c2 = st.columns([1, 1])
        with c1:
            head_col, btn_col = st.columns([3, 1])
            with head_col: st.markdown("##### 🟢 Sale Data")
            with btn_col: st.button("🔄 Reset", key="reset_c_top", on_click=limpiar_form_completed, use_container_width=True)

            row_a1, row_a2 = st.columns(2)
            c_name = row_a1.text_input("Cx Name", key="c_name").strip()
            c_id = row_a2.text_input("Cordoba ID", key="c_id", max_chars=10).strip()
            
            row_b1, row_b2 = st.columns(2)
            c_aff = row_b1.selectbox("Affiliate", options=affiliates_list, key="c_aff")
            c_lang = row_b2.selectbox("Language", ["English", "Spanish"], key="c_lang")
            
            st.markdown("---")
            btn_prev, btn_save = st.columns(2)
            
            with btn_prev:
                if st.button("👀 Preview", use_container_width=True, key="vis_comp"):
                    if c_name and c_id:
                        clean_id = ''.join(filter(str.isdigit, c_id))
                        txt = f"✅ WC Completed\nCX: {c_name} || CORDOBA-{clean_id}\nAffiliate: {c_aff}"
                        st.session_state.nota_c_texto = txt
                        st.session_state.area_c_edit = txt 
                        st.rerun() 
                    else: st.toast("Missing required fields", icon="⚠️")

            with btn_save:
                ready = bool(c_name and c_id and st.session_state.nota_c_texto)
                if st.button("💾 Save Log", type="primary", use_container_width=True, key="save_comp", disabled=not ready):
                    clean_id = ''.join(filter(str.isdigit, c_id))
                    
                    if len(clean_id) != 10:
                        st.error(f"❌ Error: ID must have 10 digits. (Actual: {len(clean_id)})")
                    elif _is_duplicate_submission(clean_id):
                        st.warning(f"⚠️ Duplicate detected for ID {clean_id}.")
                    else:
                        payload = {
                            "user_id": user_id, "username": username,
                            "customer": c_name, "cordoba_id": clean_id, 
                            "result": "Completed", "affiliate": c_aff, 
                            "info_until": "All info provided", "client_language": c_lang, "comments": "" 
                        }
                        render_confirm_modal(conn, payload)

        with c2:
            st.markdown("##### 📋 Final Note")
            st.text_area("Edit & Copy:", height=200, key="area_c_edit", 
                         on_change=lambda: st.session_state.update(nota_c_texto=st.session_state.area_c_edit))
            if st.session_state.nota_c_texto:
                _inject_copy_button(st.session_state.nota_c_texto, "copy_comp")

    # 2. NOT COMPLETED FLOW
    with t_not_comp:
        nc_left, nc_right = st.columns([2, 1])
        with nc_left:
            head_col_nc, btn_col_nc = st.columns([3, 1])
            with head_col_nc: st.markdown("##### 🔴 Failure Data")
            with btn_col_nc: st.button("🔄 Reset", key="reset_nc_top", on_click=limpiar_form_not_completed, use_container_width=True)

            r1a, r1b = st.columns(2) 
            nc_name = r1a.text_input("Cx Name", key="nc_name").strip()
            nc_id = r1b.text_input("Cordoba ID", key="nc_id", max_chars=10).strip()
            
            r2a, r2b = st.columns(2)
            nc_aff = r2a.selectbox("Affiliate", options=affiliates_list, key="nc_aff")
            nc_lang = r2b.selectbox("Language", ["English", "Spanish"], key="nc_lang")

            progress_opts = [
                "All info provided", "No info provided", "the text message of the VCF", 
                "the contact info verification", "the banking info verification", 
                "the enrollment plan verification", "the Yes/No verification questions", 
                "the creditors verification", "the right of offset",
                "1st agreement (settlement)", "2nd agreement (credit affected)", 
                "3rd agreement (not gov program)", "4th agreement (lawsuit)", 
                "5th agreement (not loan)", "recent statements request",
                "harassing calls info", "additional legal services info"
            ]
            script_stage = st.selectbox("Info Until / Progress:", progress_opts, key="nc_script")

            r3a, r3b = st.columns(2)
            with r3a:
                transfer = st.radio("Transfer Status:", ["Successful", "Unsuccessful"], horizontal=True, key="nc_trans")
                fail_reason = ""
                if transfer == "Unsuccessful":
                    fail_reason = st.selectbox("Reason:", ["Voicemail", "Line Busy", "Refused", "Gatekeeper", "Hold Time"], label_visibility="collapsed")
            with r3b:
                return_call = st.radio("Return Call?", ["Yes", "No"], horizontal=True, key="nc_ret")

            st.divider()

            # USO DE TEMPLATES DESDE CONFIG
            with st.container(border=True):
                cat_col, reason_col = st.columns([1, 2])
                with cat_col:
                    cat_sel = st.selectbox("Category:", list(REASON_TEMPLATES.keys()), label_visibility="collapsed")
                with reason_col:
                    templates = REASON_TEMPLATES[cat_sel]
                    labels = [t["label"] for t in templates]
                    lbl_sel = st.selectbox("Reason:", labels, label_visibility="collapsed")
                
                tmpl_data = next(t for t in templates if t["label"] == lbl_sel)
                
                if tmpl_data["inputs"]:
                    in_cols = st.columns(len(tmpl_data["inputs"]) + 1)
                    usr_inputs = []
                    for i, label in enumerate(tmpl_data["inputs"]):
                        with in_cols[i]:
                            val = st.text_input(label, key=f"in_{lbl_sel}_{i}")
                            usr_inputs.append(val)
                    with in_cols[-1]:
                        st.write(""); st.write("")
                        if st.button("➕ Add", use_container_width=True):
                            if all(usr_inputs):
                                new_txt = tmpl_data["template"].format(*usr_inputs)
                                st.session_state.nc_reason += ("\n" + new_txt) if st.session_state.nc_reason else new_txt
                                st.rerun()
                            else: st.toast("Missing inputs", icon="⚠️")
                else:
                    if st.button(f"➕ Add '{lbl_sel}'"):
                        new_txt = tmpl_data["template"]
                        st.session_state.nc_reason += ("\n" + new_txt) if st.session_state.nc_reason else new_txt
                        st.rerun()

            st.text_area("Final Reason:", key="nc_reason", height=100)
            
            nb_prev, nb_save = st.columns(2)
            with nb_prev:
                if st.button("👀 Preview", use_container_width=True, key="vis_nc"):
                    if nc_name and st.session_state.nc_reason:
                        clean_id = ''.join(filter(str.isdigit, nc_id))
                        stat_title = "Returned" if return_call == "Yes" else "Not Returned"
                        tx_status = f"Unsuccessful ({fail_reason})" if transfer == "Unsuccessful" else transfer

                        txt = f"""❌ WC Not Completed – {stat_title}\nCX: {nc_name} || CORDOBA-{clean_id}\n\n• Reason: {st.session_state.nc_reason}\n\n• Call Progress: {script_stage}\n• Transfer Status: {tx_status}\nAffiliate: {nc_aff}"""
                        st.session_state.nota_nc_texto = txt
                        st.session_state.area_nc_edit = txt
                        st.rerun()
                    else: st.toast("Missing Name or Reason", icon="⚠️")

            with nb_save:
                ready_nc = bool(nc_name and nc_id and st.session_state.nc_reason and st.session_state.nota_nc_texto)
                if st.button("💾 Save Log", type="primary", use_container_width=True, key="save_nc", disabled=not ready_nc):
                    clean_id = ''.join(filter(str.isdigit, nc_id))
                    
                    if len(clean_id) != 10:
                        st.error(f"❌ Error: ID must have 10 digits. (Actual: {len(clean_id)})")
                    elif _is_duplicate_submission(clean_id):
                        st.warning(f"⚠️ Duplicate detected for ID {clean_id}.")
                    else:
                        stat_title = "Returned" if return_call == "Yes" else "Not Returned"
                        payload = {
                            "user_id": user_id, "username": username,
                            "customer": nc_name, "cordoba_id": clean_id, 
                            "result": f"Not Completed - {stat_title}", "affiliate": nc_aff, 
                            "info_until": script_stage, "client_language": nc_lang, 
                            "comments": st.session_state.nc_reason
                        }
                        render_confirm_modal(conn, payload)

        with nc_right:
            st.markdown("##### 📋 Final Note")
            st.text_area("Edit & Copy:", height=450, key="area_nc_edit",
                         on_change=lambda: st.session_state.update(nota_nc_texto=st.session_state.area_nc_edit))
            if st.session_state.nota_nc_texto:
                _inject_copy_button(st.session_state.nota_nc_texto, "copy_nc")

    # 3. THIRD PARTY FLOW
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
                    st.rerun()

        with tp_r:
            st.subheader("⚖️ Legal Text")
            st.text_area("Script:", value=st.session_state.nota_tp_texto, height=200)
            if st.session_state.nota_tp_texto:
                _inject_copy_button(st.session_state.nota_tp_texto, "copy_tp")

    # --- HISTORIAL DESDE SERVICIO ---
    st.markdown("---")
    st.subheader(f"📜 Recent Activity ({username})")
    
    df_hist = note_service.fetch_agent_history(conn, username)
    if not df_hist.empty:
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
    else:
        st.info("No records found for today.")

if __name__ == "__main__":
    show()