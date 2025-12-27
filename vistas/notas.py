import time
import pytz
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from supabase import create_client, Client

# --- Configuration & Templates ---

REASON_TEMPLATES = {
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
    "📅 Program Details": [
        {"label": "Payment Amount Incorrect", "template": "According to the Cx, their payments should be {}, instead of {}.", "inputs": ["Correct Amount", "Wrong Amount"]},
        {"label": "1st Payment Date Incorrect", "template": "According to the Cx, the first payment date is incorrect. The correct date should be: {}", "inputs": ["Correct Date"]},
        {"label": "Program Length Incorrect", "template": "According to the Cx, the program length should be {} months, instead of {} months.", "inputs": ["Correct Months", "Wrong Months"]},
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

# --- Infrastructure ---

@st.cache_resource
def init_connection() -> Client:
    """Singleton connection to Supabase."""
    try:
        creds = st.secrets["connections"]["supabase"] if "connections" in st.secrets else st.secrets
        return create_client(creds["URL"], creds["KEY"])
    except Exception:
        return None

# --- Utils & Security ---

def _mask_pii(text: str) -> str:
    """Masks names to First Name + Initial (e.g., 'John Doe' -> 'John D.')."""
    if not text: return "Unknown"
    clean_text = text.strip()
    parts = clean_text.split()
    if len(parts) >= 2:
        return f"{parts[0]} {partes[-1][0]}." if 'partes' in locals() else f"{parts[0]} {parts[-1][0]}."
    return clean_text

def _is_duplicate_submission(record_id: str, cooldown: int = 60) -> bool:
    """Prevents double submissions by checking ID against session timestamp."""
    now = time.time()
    if "last_save_time" in st.session_state:
        elapsed = now - st.session_state.last_save_time
        if elapsed < cooldown and st.session_state.get("last_save_id") == record_id:
            return True
    return False

def _register_successful_save(record_id: str):
    """Updates session state with last save timestamp."""
    st.session_state.last_save_time = time.time()
    st.session_state.last_save_id = record_id

def _inject_copy_button(text_content: str, unique_key: str):
    """Injects JS component to copy text to clipboard."""
    if not text_content: return
    
    # Escape special JS characters
    safe_text = (text_content.replace("\\", "\\\\")
                             .replace("`", "\\`")
                             .replace("$", "\\$")
                             .replace("{", "\\{")
                             .replace("}", "\\}"))
    
    html = f"""
    <script>
    function copyToClipboard() {{
        const text = `{safe_text}`;
        navigator.clipboard.writeText(text).then(function() {{
            const btn = document.getElementById('btn_{unique_key}');
            btn.innerHTML = '✅ Copied!';
            btn.style.backgroundColor = '#d1e7dd';
            setTimeout(() => {{ btn.innerHTML = '📋 Copiar Nota'; btn.style.backgroundColor = '#f0f2f6'; }}, 2000);
        }}, function(err) {{ console.error('Clipboard Error', err); }});
    }}
    </script>
    <button id="btn_{unique_key}" onclick="copyToClipboard()" style="
        width: 100%; background-color: #f0f2f6; color: #31333F; border: 1px solid #d6d6d8; 
        padding: 0.6rem; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; margin-top: 8px;">
        📋 Copiar Nota
    </button>
    """
    components.html(html, height=60)

# --- Database Logic ---

def fetch_agent_history(username: str, limit: int = 5) -> pd.DataFrame:
    """Retrieves recent logs for the current agent."""
    supabase = init_connection()
    if not supabase: return pd.DataFrame()
    
    try:
        res = supabase.table("Logs")\
            .select("created_at, customer, result, cordoba_id")\
            .eq("agent", username)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
            
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
            # Convert to Eastern Time for display
            df['Time (ET)'] = df['created_at'].dt.tz_convert('US/Eastern').dt.strftime('%I:%M %p')
            return df[['Time (ET)', 'customer', 'result', 'cordoba_id']]
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def commit_log(payload: dict) -> bool:
    """Persists the log entry to Supabase with PII masking."""
    supabase = init_connection()
    if not supabase:
        st.error("Database unavailable.")
        return False

    try:
        data = {
            "created_at": datetime.now(pytz.utc).isoformat(),
            "agent": payload['agent'],
            "customer": _mask_pii(payload['customer']), # PII Protection
            "cordoba_id": payload['cordoba_id'],
            "result": payload['result'],
            "comments": payload['comments'],
            "affiliate": payload['affiliate'],
            "info_until": payload['info_until'],
            "client_language": payload['client_language']
        }
        
        supabase.table("Logs").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Commit Error: {e}")
        return False

# --- UI Components ---

@st.dialog("🛡️ Confirm Submission")
def render_confirm_modal(payload: dict):
    st.write("Please verify details before committing to database.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Customer")
        st.info(payload['customer'])
        st.caption("Cordoba ID")
        st.info(payload['cordoba_id'])
    with c2:
        st.caption("Result")
        if "Completed" in payload['result'] and "Not" not in payload['result']:
            st.success(f"🏆 {payload['result']}")
        else:
            st.error(f"❌ {payload['result']}")
        st.caption("Agent")
        st.text(payload['agent'])

    st.divider()
    
    col_cancel, col_ok = st.columns([1, 1])
    if col_cancel.button("Cancel", use_container_width=True):
        st.rerun()
            
    if col_ok.button("✅ Confirm & Save", type="primary", use_container_width=True):
        if commit_log(payload):
            _register_successful_save(payload['cordoba_id'])
            
            # Visual Feedback
            if "Completed" in payload['result'] and "Not" not in payload['result']:
                st.balloons()
            else:
                st.toast("Record saved successfully", icon="💾")
            
            time.sleep(1.0)
            st.rerun()

# --- Main View ---

def show():
    st.title("📝 Note Generator")

    # Session State Initialization
    keys = ["nota_c_texto", "nota_nc_texto", "nota_tp_texto", "nc_reason"]
    for k in keys:
        if k not in st.session_state: st.session_state[k] = ""
    
    agent_name = st.session_state.get("real_name", "Unknown Agent")

    # Tabs
    t_comp, t_not_comp, t_legal = st.tabs(["✅ WC Completed", "❌ WC Not Completed", "👥 Third Party"])

    # 1. COMPLETED FLOW
    with t_comp:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("##### 🟢 Sale Data")
            row_a1, row_a2 = st.columns(2)
            c_name = row_a1.text_input("Cx Name", key="c_name").strip()
            c_id = row_a2.text_input("Cordoba ID", key="c_id").strip()
            
            row_b1, row_b2 = st.columns(2)
            c_aff = row_b1.text_input("Affiliate", key="c_aff").strip()
            c_lang = row_b2.selectbox("Language", ["English", "Spanish"], key="c_lang")
            
            st.markdown("---")
            btn_prev, btn_save = st.columns(2)
            
            with btn_prev:
                if st.button("👀 Preview", use_container_width=True, key="vis_comp"):
                    if c_name and c_id:
                        clean_id = ''.join(filter(str.isdigit, c_id)) or "MISSING"
                        txt = f"✅ WC Completed\nCX: {c_name} || CORDOBA-{clean_id}\nAffiliate: {c_aff}\nLanguage: {c_lang}"
                        st.session_state.nota_c_texto = txt
                        st.session_state.area_c_edit = txt 
                        st.rerun() 
                    else:
                        st.toast("Missing required fields", icon="⚠️")

            with btn_save:
                ready = bool(c_name and c_id and st.session_state.nota_c_texto)
                if st.button("💾 Save Log", type="primary", use_container_width=True, key="save_comp", disabled=not ready):
                    clean_id = ''.join(filter(str.isdigit, c_id)) or "MISSING"
                    
                    if _is_duplicate_submission(clean_id):
                        st.warning(f"⚠️ Duplicate detected for ID {clean_id}. Please wait.")
                    else:
                        payload = {
                            "agent": agent_name, "customer": c_name, "cordoba_id": clean_id, 
                            "result": "Completed", "affiliate": c_aff, 
                            "info_until": "All info provided", "client_language": c_lang, "comments": "" 
                        }
                        render_confirm_modal(payload)

        with c2:
            st.markdown("##### 📋 Final Note")
            st.text_area("Edit & Copy:", value=st.session_state.nota_c_texto, height=200, key="area_c_edit", 
                         on_change=lambda: st.session_state.update(nota_c_texto=st.session_state.area_c_edit))
            if st.session_state.nota_c_texto:
                _inject_copy_button(st.session_state.nota_c_texto, "copy_comp")

    # 2. NOT COMPLETED FLOW
    with t_not_comp:
        nc_left, nc_right = st.columns([2, 1])
        with nc_left:
            st.markdown("##### 🔴 Failure Data")
            r1a, r1b = st.columns(2) 
            nc_name = r1a.text_input("Cx Name", key="nc_name").strip()
            nc_id = r1b.text_input("Cordoba ID", key="nc_id").strip()
            
            r2a, r2b = st.columns(2)
            nc_aff = r2a.text_input("Affiliate", key="nc_aff").strip()
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

            # Dynamic Script Builder
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
                        clean_id = ''.join(filter(str.isdigit, nc_id)) or "MISSING"
                        stat_title = "Returned" if return_call == "Yes" else "Not Returned"
                        tx_status = f"Unsuccessful ({fail_reason})" if transfer == "Unsuccessful" else transfer

                        txt = f"""❌ WC Not Completed – {stat_title}\nCX: {nc_name} || CORDOBA-{clean_id}\n\n• Reason: {st.session_state.nc_reason}\n\n• Call Progress: {script_stage}\n• Transfer Status: {tx_status}\nAffiliate: {nc_aff}\nLanguage: {nc_lang}"""
                        st.session_state.nota_nc_texto = txt
                        st.session_state.area_nc_edit = txt 
                        st.rerun()
                    else: st.toast("Missing Name or Reason", icon="⚠️")

            with nb_save:
                ready_nc = bool(nc_name and nc_id and st.session_state.nc_reason and st.session_state.nota_nc_texto)
                if st.button("💾 Save Log", type="primary", use_container_width=True, key="save_nc", disabled=not ready_nc):
                    clean_id = ''.join(filter(str.isdigit, nc_id)) or "MISSING"
                    if _is_duplicate_submission(clean_id):
                        st.warning(f"⚠️ Duplicate detected for ID {clean_id}.")
                    else:
                        stat_title = "Returned" if return_call == "Yes" else "Not Returned"
                        payload = {
                            "agent": agent_name, "customer": nc_name, "cordoba_id": clean_id, 
                            "result": f"Not Completed - {stat_title}", "affiliate": nc_aff, 
                            "info_until": script_stage, "client_language": nc_lang, 
                            "comments": st.session_state.nc_reason
                        }
                        render_confirm_modal(payload)

        with nc_right:
            st.markdown("##### 📋 Final Note")
            st.text_area("Edit & Copy:", value=st.session_state.nota_nc_texto, height=450, key="area_nc_edit",
                         on_change=lambda: st.session_state.update(nota_nc_texto=st.session_state.area_nc_edit))
            if st.session_state.nota_nc_texto:
                _inject_copy_button(st.session_state.nota_nc_texto, "copy_nc")
                if st.button("🔄 Clear All", key="new_nc"):
                    st.session_state.nota_nc_texto = ""
                    st.session_state.nc_reason = ""
                    st.rerun()

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

    # --- RECENT HISTORY ---
    st.markdown("---")
    st.subheader(f"📜 Recent Activity ({agent_name})")
    
    df_hist = fetch_agent_history(agent_name)
    if not df_hist.empty:
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
    else:
        st.info("No records found for today.")

if __name__ == "__main__":
    show()
