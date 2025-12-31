import pytz
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime, timedelta
# Quitamos text() para evitar problemas de hash/cache
# from sqlalchemy import text 

# --- IMPORTACIÓN DE CONEXIÓN ---
try:
    from conexion import get_db_connection
except ImportError:
    from conexion import get_db_connection

# --- Configuration & Constants ---

US_HOLIDAYS_2025 = {
    (1, 1), (5, 26), (9, 1), (11, 27), (12, 25)
}

TZ_ET = pytz.timezone('US/Eastern')
TZ_BO = pytz.timezone('America/La_Paz')
TZ_CO = pytz.timezone('America/Bogota')

# --- Business Logic (Dates) ---

def _is_holiday(date_obj) -> bool:
    return (date_obj.month, date_obj.day) in US_HOLIDAYS_2025

def calculate_business_date(start_date, target_days):
    """Calculates future business date skipping weekends and US holidays."""
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

# --- Data Layer (SQL Version) ---

def fetch_active_news(conn) -> pd.DataFrame:
    if not conn: return pd.DataFrame()
    try:
        query = 'SELECT * FROM "Updates" WHERE active = TRUE ORDER BY date DESC'
        return conn.query(query, ttl=60)
    except Exception:
        return pd.DataFrame()

def fetch_agent_metrics(conn, agent_name: str, start_date_utc: str) -> pd.DataFrame:
    if not conn: return pd.DataFrame()
    try:
        # CORRECCIÓN ROBUSTA:
        # 1. Usamos string normal (sin text()) para evitar errores de cache.
        # 2. Usamos TRIM() y LOWER() para ignorar espacios y mayúsculas.
        # 3. Casteamos created_at para asegurar comparación correcta.
        query = """
            SELECT * FROM "Logs" 
            WHERE LOWER(TRIM(agent)) = :agent 
            AND created_at >= :start_date 
            ORDER BY created_at DESC
        """
        
        # Limpiamos el input también
        clean_agent = agent_name.strip().lower()
        
        return conn.query(query, params={"agent": clean_agent, "start_date": start_date_utc}, ttl=0)
    except Exception as e:
        print(f"Error metrics: {e}") # Log para debug en consola Docker
        return pd.DataFrame()

# --- UI Components ---

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
    conn = get_db_connection()
    
    # 1. Time & Context Setup
    now_et = datetime.now(TZ_ET)
    today = now_et.date()
    
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    start_of_month_utc = datetime.combine(start_of_month, datetime.min.time()).replace(tzinfo=TZ_ET).astimezone(pytz.utc).isoformat()

    agent_name = st.session_state.get("username")
    if not agent_name:
        st.error("⚠️ Sesión inválida. Recarga la página.")
        st.stop()

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
        ("Standard (3 Business Days)", date_std, "%m/%d/%Y"),
        ("California (5 Business Days)", date_ext, "%m/%d/%Y"),
        ("⛔ Max Date (35 Calendar Days)", date_max, "%m/%d/%Y")
    ]

    for col, (label, val, fmt) in zip(cols, metrics):
        with col:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"<p style='{card_style}'>{val.strftime(fmt)}</p>", unsafe_allow_html=True)

    st.write("") 

    # 4. Performance Dashboard
    df_logs = fetch_agent_metrics(conn, agent_name, start_of_month_utc)
    
    if not df_logs.empty and 'created_at' in df_logs.columns:
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at'], utc=True)
        df_logs['date_et'] = df_logs['created_at'].dt.tz_convert(TZ_ET).dt.date
        
    st.subheader("📊 Performance Tracker")
    tabs = st.tabs(["📅 Today", "🗓️ This Week", "🏆 This Month"])

    def _render_tab_metrics(filter_date, tag):
        if df_logs.empty:
            subset = pd.DataFrame(columns=['result'])
        else:
            subset = df_logs[df_logs['date_et'] >= filter_date].copy()
        
        total_interactions = len(subset)
        completed_df = subset[subset['result'].str.contains('Completed', case=False, na=False) & ~subset['result'].str.contains('Not', case=False, na=False)]
        sales_count = len(completed_df)
        conversion_rate = (sales_count / total_interactions * 100) if total_interactions > 0 else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("📞 Total Calls", total_interactions)
        k2.metric("✅ WC Completed", sales_count)
        k3.metric("📈 Conversion Rate", f"{conversion_rate:.1f}%")

        st.divider()

        if total_interactions > 0:
            c_donut, c_fail = st.columns([1, 1])
            with c_donut:
                st.markdown("###### 🟢 Success vs Failure")
                subset['Status'] = subset['result'].apply(lambda x: 'Completed' if 'Completed' in x and 'Not' not in x else 'Not Completed')
                base = alt.Chart(subset).encode(theta=alt.Theta("count()", stack=True))
                pie = base.mark_arc(outerRadius=80, innerRadius=45).encode(
                    color=alt.Color("Status", scale=alt.Scale(domain=['Completed', 'Not Completed'], range=['#2ecc71', '#e74c3c']), legend=None),
                    tooltip=["Status", "count()"]
                )
                text = base.mark_text(radius=100).encode(
                    text="count()", order=alt.Order("Status"), color=alt.value("black")  
                )
                st.altair_chart(pie + text, use_container_width=True)

            with c_fail:
                failures = subset[subset['Status'] == 'Not Completed']
                if not failures.empty:
                    st.markdown("###### 🔴 Why Not Completed?")
                    failures['Reason'] = failures['result'].str.replace('Not Completed - ', '', regex=False)
                    fail_chart = alt.Chart(failures).mark_bar().encode(
                        x=alt.X('count()', title=None),
                        y=alt.Y('Reason', sort='-x', title=None),
                        color=alt.value('#e74c3c'),
                        tooltip=['Reason', 'count()']
                    ).properties(height=180)
                    st.altair_chart(fail_chart, use_container_width=True)
                elif total_interactions > 0:
                    st.success("🎉 Perfect Score! No failures in this period.")
        else:
            st.info(f"Waiting for calls... (No activity for {tag})")

    with tabs[0]: _render_tab_metrics(today, "Today")
    with tabs[1]: _render_tab_metrics(start_of_week, "This Week")
    with tabs[2]: _render_tab_metrics(start_of_month, "This Month")

    # 5. News Feed
    st.divider()
    df_news = fetch_active_news(conn)
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