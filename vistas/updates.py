import pandas as pd
import streamlit as st
from datetime import datetime
from supabase import create_client, Client

# --- Configuration ---

CATEGORY_THEMES = {
    'CRITICAL': {'border': '#DC2626', 'bg': '#DC2626', 'icon': '🚨'}, # Red-600
    'WARNING':  {'border': '#D97706', 'bg': '#D97706', 'icon': '⚠️'}, # Amber-600
    'INFO':     {'border': '#2563EB', 'bg': '#2563EB', 'icon': 'ℹ️'}  # Blue-600
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

# --- Data Layer ---

def fetch_updates(supabase: Client) -> pd.DataFrame:
    """Fetches active broadcast messages ordered by date."""
    if not supabase: return pd.DataFrame()
    
    try:
        res = supabase.table("Updates").select("*")\
            .eq("active", True)\
            .order("date", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        # Log to console in production
        print(f"[Updates Fetch Error] {e}")
        return pd.DataFrame()

# --- UI Components ---

def _render_update_card(row: pd.Series):
    """Generates HTML card for a single update entry."""
    # Data extraction with safe defaults
    cat = str(row.get('category', 'Info')).strip().upper()
    title = row.get('title', 'System Notice')
    msg = row.get('message', '')
    raw_date = str(row.get('date', ''))

    # Date formatting
    try:
        date_str = datetime.strptime(raw_date, '%Y-%m-%d').strftime('%b %d, %Y')
    except ValueError:
        date_str = raw_date

    # Theme resolution
    theme = CATEGORY_THEMES.get(cat, CATEGORY_THEMES['INFO'])

    # Component Rendering
    st.markdown(f"""
    <div style="
        background-color: #FFFFFF;
        border-radius: 6px;
        border-left: 4px solid {theme['border']};
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        padding: 1.25rem;
        margin-bottom: 1rem;
        font-family: 'Segoe UI', sans-serif;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <span style="
                background-color: {theme['bg']}; 
                color: white; 
                padding: 0.25rem 0.75rem; 
                border-radius: 9999px; 
                font-size: 0.75rem; 
                font-weight: 700;
                letter-spacing: 0.05em;
            ">
                {theme['icon']} {cat}
            </span>
            <span style="color: #6B7280; font-size: 0.85rem;">{date_str}</span>
        </div>
        <h3 style="margin: 0 0 0.5rem 0; color: #111827; font-size: 1.1rem; font-weight: 600;">
            {title}
        </h3>
        <div style="color: #374151; font-size: 0.95rem; line-height: 1.5; white-space: pre-wrap;">{msg}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Main View ---

def show():
    # Header & Controls
    c_head, c_act = st.columns([4, 1])
    with c_head:
        st.title("📢 News Center")
        st.caption("Official communications and operational updates.")
    with c_act:
        st.write("") # Spacer
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # Data Loading
    supabase = init_connection()
    df = fetch_updates(supabase)

    if df.empty:
        st.info("No active announcements at this time.")
        return

    # Filter Toolbar
    c_search, c_filter = st.columns([3, 1])
    
    with c_search:
        search_query = st.text_input("Search updates...", placeholder="Keywords...", label_visibility="collapsed")
    
    with c_filter:
        cat_filter = st.selectbox(
            "Filter by Type", 
            ["All Types", "🔴 Critical", "🟡 Warning", "🔵 Info"], 
            label_visibility="collapsed"
        )

    # Filtering Logic
    if search_query:
        # Case-insensitive search on Title OR Message
        mask = df['title'].str.contains(search_query, case=False, na=False) | \
               df['message'].str.contains(search_query, case=False, na=False)
        df = df[mask]

    if cat_filter != "All Types":
        # Extract keyword (CRITICAL, WARNING, INFO)
        target_cat = cat_filter.split(" ")[1].strip()
        df = df[df['category'].str.upper() == target_cat]

    st.write("")

    # List Rendering
    if not df.empty:
        for _, row in df.iterrows():
            _render_update_card(row)
    else:
        st.warning("No updates found matching your criteria.")

if __name__ == "__main__":
    show()
