import re
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# Configuration
CACHE_TTL = 3600  # 1 hour cache
IGNORED_TOKENS = {"CREDITOR", "ACCOUNT", "BALANCE", "DEBT", "AMOUNT"}

# --- Infrastructure ---

@st.cache_resource
def init_connection() -> Client:
    """Singleton connection to Supabase."""
    try:
        creds = st.secrets["connections"]["supabase"] if "connections" in st.secrets else st.secrets
        return create_client(creds["URL"], creds["KEY"])
    except Exception:
        return None

# --- Data Layer ---

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_creditor_master_list() -> pd.DataFrame:
    """
    Retrieves and caches the creditor master list (limit 10k).
    Returns normalized DataFrame with ['Code', 'Name', 'Normalized_Code'].
    """
    supabase = init_connection()
    if not supabase: return pd.DataFrame()

    try:
        res = supabase.table("Creditors")\
            .select("abreviation, name")\
            .order("abreviation")\
            .limit(10000)\
            .execute()
        
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            df = df.rename(columns={"abreviation": "Code", "name": "Name"})
            df = df.dropna(subset=['Code'])
            # Pre-compute upper case for faster matching
            df['Normalized_Code'] = df['Code'].astype(str).str.strip().str.upper().str.replace(r'\s+', ' ', regex=True)
            
        return df
    except Exception as e:
        # Silently log error in console
        print(f"[DataFetch Error] Creditors: {e}") 
        return pd.DataFrame()

def _sanitize_input(raw_text: str) -> str:
    """Parses raw copy-paste lines to extract potential creditor codes."""
    # Split by tabs or double spaces often found in CRM exports
    parts = re.split(r'\t|\s{2,}', raw_text)
    base_text = parts[0].strip()
    
    # Remove trailing amounts or digits often pasted by mistake (e.g., "CHASE 500.00")
    match = re.search(r'(\d|\$)', base_text)
    if match:
        base_text = base_text[:match.start()].strip()
        
    return re.sub(r'\s+', ' ', base_text)

# --- UI Entry Point ---

def show():
    # Load data immediately
    df_creditors = fetch_creditor_master_list()
    
    # Header & Metrics
    col_header, col_metric = st.columns([3, 1])
    with col_header:
        st.title("🏦 Buscador de Acreedores")
        st.caption("Validación y normalización de códigos bancarios.")
        
    with col_metric:
        count = len(df_creditors) if not df_creditors.empty else 0
        st.metric("Total Entidades", count, delta="Active DB" if count > 0 else "Offline")

    # Indexing for O(1) lookups
    if not df_creditors.empty:
        # Maps for exact matching
        code_map = dict(zip(df_creditors['Normalized_Code'], df_creditors['Code']))
        name_map = dict(zip(df_creditors['Normalized_Code'], df_creditors['Name']))
    else:
        st.warning("Database unavailable.")
        code_map, name_map = {}, {}

    # View Logic
    tab_manual, tab_batch = st.tabs(["🔎 Manual Search", "🚀 Batch Processing"])

    # 1. Single Lookup
    with tab_manual:
        c1, _ = st.columns([3, 1])
        query = c1.text_input("Search Code or Name:", placeholder="e.g., AMEX", label_visibility="collapsed")
        
        if query and not df_creditors.empty:
            normalized_query = re.sub(r'\s+', ' ', query.strip().upper())
            
            # Fuzzy match (Contains)
            mask = (df_creditors['Normalized_Code'].str.contains(normalized_query, regex=False)) | \
                   (df_creditors['Name'].str.upper().str.contains(normalized_query, regex=False))
            
            results = df_creditors[mask]

            if not results.empty:
                st.success(f"{len(results)} matches found.")
                st.dataframe(results[['Code', 'Name']], use_container_width=True, hide_index=True)
            else:
                st.warning(f"No results for '{query}'")

    # 2. Bulk Processing
    with tab_batch:
        st.info("Batch Validator: Paste list from Excel/CRM.")
        raw_input = st.text_area("Input Data:", height=150)
        
        if st.button("⚡ Process Batch", type="primary"):
            if not raw_input: return

            lines = raw_input.split('\n')
            valid_hits = []
            unknowns = []

            for line in lines:
                clean_line = line.strip()
                if not clean_line: continue
                
                parsed_code = _sanitize_input(clean_line).upper()
                
                # Noise filtering
                if parsed_code in IGNORED_TOKENS or len(parsed_code) < 2:
                    continue

                # Exact Match Check
                if parsed_code in code_map:
                    valid_hits.append({
                        "Input": parsed_code,
                        "DB Code": code_map[parsed_code],
                        "Entity Name": name_map[parsed_code]
                    })
                else:
                    unknowns.append(parsed_code)

            # Render Results
            st.divider()
            c_hits, c_miss = st.columns([2, 1])
            
            with c_hits:
                if valid_hits:
                    st.success(f"✅ {len(valid_hits)} Valid Codes")
                    st.dataframe(pd.DataFrame(valid_hits)[["DB Code", "Entity Name"]], hide_index=True, use_container_width=True)
                else:
                    st.info("No valid codes found in batch.")

            with c_miss:
                if unknowns:
                    st.error(f"⚠️ {len(unknowns)} Unrecognized")
                    st.text_area("Review Required:", value="\n".join(unknowns), height=200)

if __name__ == "__main__":
    show()
