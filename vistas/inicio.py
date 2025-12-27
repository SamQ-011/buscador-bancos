import pytz
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- Configuration & Constants ---

US_HOLIDAYS_2025 = {
    (1, 1), (1, 20), (2, 17), (5, 26), (6, 19), 
    (7, 4), (9, 1), (10, 13), (11, 11), (11, 27), (12, 25)
}

TZ_ET = pytz.timezone('US/Eastern')
TZ_BO = pytz.timezone('America/La_Paz')
TZ_CO = pytz.timezone('America/Bogota')

# --- Infrastructure ---

@st.cache_resource
def init_connection() -> Client:
    """Singleton connection to Supabase."""
    try:
        creds = st.secrets["connections"]["supabase"] if "connections" in st.secrets else st.secrets
        return create_client(creds["URL"], creds["KEY"])
    except Exception:
        return None

# --- Business Logic (Dates) ---

def _is_holiday(date_obj) -> bool:
    return (date_obj.month, date_obj.day) in US_HOLIDAYS_2025

def calculate_business_date(start_date, target_days):
    """
    Calculates future business date skipping weekends and US holidays.
    Counts 'start_date' as Day 1 if it's a valid business day.
    """
    current_date = start_date
    days_counted = 0
    
    while days_counted < target_days:
        is_weekend = current_date.weekday() >= 5
        is_holiday = _is_holiday(current_date)
        
        if not is_weekend and not is_holiday:
            days_counted += 1
            if days_counted == target_days:
                return current_date
        
        current_date += timedelta(days=1)
            
    return current_date

# --- Data Layer ---

def fetch_active_news(supabase: Client) -> pd.DataFrame:
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table("Updates").select("*")\
            .eq("active", True).order("date", desc=True).execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

def fetch_agent_metrics(supabase: Client, agent_name: str, start_date_utc: str) -> pd.DataFrame:
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table("Logs").select("*")\
            .eq("agent", agent_name)\
            .gte("created_at", start_date_utc)\
            .order("created_at", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

# --- UI Components ---

def render_kpi_card(title, current, target):
    progress = min(current / target, 1.0) if target > 0 else 0
    pct = int(progress * 100)
    
    # Dynamic coloring based on performance
    color = "#ff4444" # Red
    if pct >= 50: color = "#ffbb33" # Orange
    if pct >= 100: color = "#00C851" # Green
    
    with st.container(border=True):
        st.caption(title)
        c1, c2 = st.columns([2, 1])
        c1.markdown(f"<h2 style='margin:0;'>{current} <small style='color:#aaa; font-size:0.5em'>/ {target}</small></h2>", unsafe_allow_html=True)
        c2.markdown(f"<h3 style='text-align:right; color:{color}; margin:0;'>{pct}%</h3>", unsafe_allow_html=True)
        st.progress(progress)

def render_clock_widget():
    now_et = datetime.now(TZ_ET)
    now_bo = datetime.now(TZ_BO)
    now_co = datetime.now(TZ_CO)
    
    st.markdown(f"""
        <div style='text-align: right; color: #444; font-family: monospace; line-height: 1.2;'>
            <div style='font-weight: bold; color: #222;'>ET  {now_et.strftime('%H:%M')}</div>
            <div style='color: #666; font-size: 0.9em;'>BOL {now_bo.strftime('%H:%M')}</div>
            <div style='color: #666; font-size: 0.9em;'>COL {now_co.strftime('%H:%M')}</div>
        </div>
    """, unsafe_allow_html=True)

# --- Main View ---

def show():
    supabase = init_connection()
    
    # 1. Time & Context Setup
    now_et = datetime.now(TZ_ET)
    today = now_et.date()
    
    # Date Anchors
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    # Full datetime for DB filtering (Beginning of Month UTC conversion handled later or implicitly)
    start_of_month_utc = datetime.combine(start_of_month, datetime.min.time()).replace(tzinfo=TZ_ET).astimezone(pytz.utc).isoformat()

    agent_name = st.session_state.get("real_name", "Agent")

    # 2. Header
    c_head, c_clock = st.columns([3, 1])
    with c_head:
        st.markdown(f"### 🚀 Workspace: {agent_name}")
    with c_clock:
        render_clock_widget()
    
    st.divider()

    # 3. Date Calculator Module
    st.subheader("📅 First Payment Dates")
    
    date_std = calculate_business_date(now_et, 3) 
    date_ext = calculate_business_date(now_et, 5)  
    date_max = now_et + timedelta(days=35)

    cols = st.columns(3)
    card_style = "font-size: 1.4rem; font-weight: 700; color: #2C3E50; margin: 0;"
    
    metrics = [
        ("Standard (3 Days)", date_std, "%b %d"),
        ("California (5 Days)", date_ext, "%b %d"),
        ("⛔ Max Date (35 Days)", date_max, "%m/%d/%Y")
    ]

    for col, (label, val, fmt) in zip(cols, metrics):
        with col:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"<p style='{card_style}'>{val.strftime(fmt)}</p>", unsafe_allow_html=True)

    st.write("") 

    # 4. Performance Dashboard
    df_logs = fetch_agent_metrics(supabase, agent_name, start_of_month_utc)
    
    # Pre-process dates if data exists
    if not df_logs.empty and 'created_at' in df_logs.columns:
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at'])
        # Normalize to ET date for filtering
        df_logs['date_et'] = df_logs['created_at'].apply(
            lambda x: x.tz_convert(TZ_ET) if x.tzinfo else x.tz_localize('UTC').tz_convert(TZ_ET)
        ).dt.date

    st.subheader("📊 Performance Tracker")
    tabs = st.tabs(["📅 Today", "🗓️ This Week", "🏆 This Month"])

    def _render_tab_metrics(filter_date, sales_target, tag):
        if df_logs.empty:
            subset = pd.DataFrame(columns=['result'])
        else:
            subset = df_logs[df_logs['date_et'] >= filter_date]
        
        total_interactions = len(subset)
        sales_count = len(subset[subset['result'].str.contains('Completed', case=False, na=False)]) if total_interactions > 0 else 0
        conversion_rate = (sales_count / total_interactions * 100) if total_interactions > 0 else 0

        c_kpi, c_viz = st.columns([1, 2])
        
        with c_kpi:
            render_kpi_card("Completed Sales", sales_count, sales_target)
            st.write("")
            k1, k2 = st.columns(2)
            k1.metric("Total Calls", total_interactions)
            k2.metric("Conversion", f"{conversion_rate:.0f}%")
        
        with c_viz:
            if total_interactions > 0:
                chart_data = subset['result'].value_counts().reset_index()
                chart_data.columns = ['Result', 'Count']
                
                chart = alt.Chart(chart_data).mark_bar(cornerRadius=4).encode(
                    x=alt.X('Count', title=None),
                    y=alt.Y('Result', sort='-x', title=None),
                    color=alt.Color('Result', legend=None, scale=alt.Scale(scheme='blues')),
                    tooltip=['Result', 'Count']
                ).properties(height=180)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info(f"No activity recorded for: {tag}")

    with tabs[0]: _render_tab_metrics(today, 5, "Today")
    with tabs[1]: _render_tab_metrics(start_of_week, 25, "This Week")
    with tabs[2]: _render_tab_metrics(start_of_month, 100, "This Month")

    # 5. News Feed
    st.divider()
    df_news = fetch_active_news(supabase)
    
    if not df_news.empty:
        st.subheader("🔔 Team Updates")
        for _, row in df_news.iterrows():
            cat = str(row.get('category', 'INFO')).upper()
            theme = {
                'CRITICAL': {'bg': '#FFEBEE', 'bd': '#D32F2F', 'icon': '🚨'},
                'WARNING':  {'bg': '#FFF8E1', 'bd': '#FFA000', 'icon': '⚠️'},
                'INFO':     {'bg': '#F1F5F9', 'bd': '#475569', 'icon': 'ℹ️'}
            }.get(cat, {'bg': '#F1F5F9', 'bd': '#475569', 'icon': 'ℹ️'})
            
            st.markdown(f"""
                <div style='background-color: {theme['bg']}; border-left: 4px solid {theme['bd']}; padding: 12px; border-radius: 4px; margin-bottom: 10px;'>
                    <div style='display:flex; justify-content:space-between; color: #666; font-size: 0.8em; margin-bottom: 4px;'>
                        <span>{theme['icon']} <b>{row.get('title')}</b></span>
                        <span>{row.get('date')}</span>
                    </div>
                    <div style='color: #334155; font-size: 0.95em;'>{row.get('message')}</div>
                </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    show()
