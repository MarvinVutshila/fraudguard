"""
FraudGuard Command Centre – Final Optimised Edition
====================================================
Configurable table mapping, live Athena table discovery, real error
surfacing (no swallowed AWS errors), and a fuller analytics story.

Run: streamlit run dashboard.py
"""

import logging
import os
import time
from datetime import datetime, timedelta, date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pyathena import connect
from pyathena.error import OperationalError, DatabaseError

# =============================================================================
# LOGGING – real errors land in the console, not just a vague banner
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("fraudguard_dashboard")

# =============================================================================
# CONFIGURATION
# =============================================================================

DATABASE = "fraudguard_dwh"
S3_STAGING_DIR = "s3://fraudguard-warehouse-2026/athena-results/"
AWS_REGION = "eu-west-2"
WORKGROUP = "primary"
CATALOG = "AwsDataCatalog"

# ---- Credentials pulled from env vars first; fallback keeps this runnable
# ---- as-is, but SWAP THESE TO REAL ENV VARS before sharing this file. ----
AUTH_USERNAME = os.environ.get("FRAUDGUARD_USER", "admin")
AUTH_PASSWORD = os.environ.get("FRAUDGUARD_PASSWORD", "Marvin@044")
AUTH_EMAIL = os.environ.get("FRAUDGUARD_EMAIL", "marvinmakhubela04@gmail.com")

# =============================================================================
# TABLE MAPPING – single source of truth for every table this dashboard uses.
# Change a table name here once; every query below picks it up automatically.
# =============================================================================

TABLE_MAPPING = {
    "transactions": {
        "primary": f"{DATABASE}.transactions",
        "fallback": f"{DATABASE}.silver_transactions",
    },
    "overrides": {
        "primary": f"{DATABASE}.silver_transaction_overrides",
        "fallback": None,
    },
    "login_logs": {
        "primary": f"{DATABASE}.silver_login_logs",
        "fallback": None,
    },
    "api_requests": {
        "primary": f"{DATABASE}.silver_api_requests",
        "fallback": None,
    },
    "user_activity": {
        "primary": f"{DATABASE}.user_activity",
        "fallback": None,
    },
}

RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
DECISIONS = ["REVIEW", "APPROVE", "BLOCK"]

COLOR_MAP_DECISION = {"REVIEW": "#F2A900", "APPROVE": "#2E8B57", "BLOCK": "#C0392B"}
COLOR_MAP_RISK = {"LOW": "#2E8B57", "MEDIUM": "#F2A900", "HIGH": "#C0392B"}
ACCENT = "#1F4E79"

st.set_page_config(page_title="FraudGuard Command Centre", page_icon="🛡️", layout="wide")

# =============================================================================
# GLOBAL STYLING
# =============================================================================

st.markdown(
    """
    <style>
        .block-container {padding-top: 1rem; max-width: 100%;}
        div[data-testid="stMetric"] {
            background: #1E293B;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover { transform: translateY(-2px); }
        div[data-testid="stMetricLabel"] { color: #94A3B8; font-weight: 500; font-size: 14px; letter-spacing: 0.3px; }
        div[data-testid="stMetricValue"] { color: #F8FAFC; font-weight: 700; font-size: 28px; line-height: 1.2; }
        h1, h2, h3 { color: #F8FAFC; }
        .stAlert { border-radius: 8px; }
        .dataframe { font-size: 14px; }
        .stDownloadButton button { background-color: #1F4E79; color: white; border: none; border-radius: 6px; padding: 0.5rem 1rem; }
        .sidebar-user-card { background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 12px 14px; margin-bottom: 14px; }
        .sidebar-user-card .label { color: #94A3B8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.3px; }
        .sidebar-user-card .value { color: #F8FAFC; font-size: 14px; font-weight: 600; }
        .login-container { display: flex; justify-content: center; align-items: center; min-height: 80vh; }
        .login-box {
            background: rgba(30, 41, 59, 0.9);
            backdrop-filter: blur(12px);
            border: 1px solid #334155;
            border-radius: 20px;
            padding: 40px 32px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 12px 40px rgba(0,0,0,0.4);
            text-align: center;
        }
        .login-box h1 { color: #F8FAFC; font-size: 28px; margin-bottom: 8px; }
        .login-box .subtitle { color: #94A3B8; font-size: 14px; margin-bottom: 28px; }
        .login-box .stTextInput input { background: #0F172A; border: 1px solid #334155; color: #F8FAFC; border-radius: 8px; padding: 12px 16px; }
        .login-box .stButton button { background: #1F4E79; color: white; border: none; width: 100%; border-radius: 8px; padding: 12px; font-weight: 600; font-size: 16px; }
        .login-box .stButton button:hover { background: #2563EB; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { background-color: #1E293B; border-radius: 8px 8px 0 0; padding: 10px 20px; color: #94A3B8; font-weight: 500; }
        .stTabs [aria-selected="true"] { background-color: #1F4E79; color: white; }
        .main { overflow-x: hidden; }
        section.main > div { max-width: 100%; }
        .table-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }
        .badge-found { background: rgba(46,139,87,0.15); color: #4ADE80; border: 1px solid #2E8B57; }
        .badge-missing { background: rgba(192,57,43,0.15); color: #F87171; border: 1px solid #C0392B; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# AUTH GATE
# =============================================================================

def login_screen():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    with st.container():
        st.markdown(
            """
            <div class="login-box">
                <h1>🛡️ FraudGuard</h1>
                <div class="subtitle">Sign in to continue</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                if username == AUTH_USERNAME and password == AUTH_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = AUTH_EMAIL
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")
    st.markdown('</div>', unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# =============================================================================
# CONNECTION
# =============================================================================

@st.cache_resource(show_spinner=False)
def get_connection():
    return connect(
        s3_staging_dir=S3_STAGING_DIR,
        region_name=AWS_REGION,
        work_group=WORKGROUP,
        catalog_name=CATALOG,
        schema_name=DATABASE,
    )

def format_athena_error(e: Exception) -> str:
    """Surface the real AWS/Athena error text instead of a generic message."""
    msg = str(e)
    if hasattr(e, "response") and isinstance(getattr(e, "response", None), dict):
        err = e.response.get("Error", {})
        code = err.get("Code", "")
        message = err.get("Message", "")
        if code or message:
            msg = f"{code}: {message}"
    return msg

try:
    conn = get_connection()
    pd.read_sql("SELECT 1", conn)
except (OperationalError, DatabaseError, Exception) as e:
    err_text = format_athena_error(e)
    logger.error("Athena connection failed: %s", err_text)
    st.error(f"❌ Could not connect to Athena.\n\n**AWS error:** `{err_text}`")
    st.stop()

# =============================================================================
# TABLE DISCOVERY – SHOW TABLES IN <database>, cached, drives the badges
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def discover_tables(database: str):
    try:
        df = pd.read_sql(f"SHOW TABLES IN {database}", conn)
        # pyathena/Athena returns a single unlabeled column of table names
        col = df.columns[0]
        return set(df[col].str.strip().tolist()), None
    except Exception as e:
        return set(), format_athena_error(e)

available_tables, discovery_error = discover_tables(DATABASE)

if discovery_error:
    logger.warning("SHOW TABLES failed: %s", discovery_error)
    st.warning(f"⚠️ Could not run `SHOW TABLES IN {DATABASE}` — falling back to per-table probing. AWS error: `{discovery_error}`")

def short_name(full_table: str) -> str:
    return full_table.split(".", 1)[-1]

def resolve_table(key: str):
    """Resolve a logical table key to an actual table name using TABLE_MAPPING,
    preferring the primary name, falling back if defined, verified against
    the live SHOW TABLES result (or a direct probe if discovery failed)."""
    cfg = TABLE_MAPPING[key]
    primary, fallback = cfg["primary"], cfg["fallback"]

    def exists(full_name):
        if available_tables:
            return short_name(full_name) in available_tables
        try:
            pd.read_sql(f"SELECT 1 FROM {full_name} LIMIT 1", conn)
            return True
        except Exception:
            return False

    if exists(primary):
        return primary, True
    if fallback and exists(fallback):
        return fallback, True
    return primary, False  # keep the primary name for display even if missing

TXN_TABLE, has_txn = resolve_table("transactions")
OVR_TABLE, has_override = resolve_table("overrides")
LOGIN_TABLE, has_login = resolve_table("login_logs")
API_TABLE, has_api = resolve_table("api_requests")
ACTIVITY_TABLE, has_activity = resolve_table("user_activity")

def badge_html(label: str, found: bool, table_name: str) -> str:
    cls = "badge-found" if found else "badge-missing"
    text = "✅ Found" if found else "❌ Missing"
    return f'<span>{label}: <code>{short_name(table_name)}</code></span><span class="table-badge {cls}">{text}</span>'

st.markdown("#### Data Source Status")
status_cols = st.columns(5)
for col, (label, table, found) in zip(
    status_cols,
    [
        ("Transactions", TXN_TABLE, has_txn),
        ("Overrides", OVR_TABLE, has_override),
        ("Logins", LOGIN_TABLE, has_login),
        ("API", API_TABLE, has_api),
        ("Activity", ACTIVITY_TABLE, has_activity),
    ],
):
    with col:
        st.markdown(badge_html(label, found, table), unsafe_allow_html=True)

if not has_txn:
    st.error("Transactions table is missing entirely — the dashboard can't function without it. Check `TABLE_MAPPING`.")
    st.stop()

# =============================================================================
# QUERY HELPERS
# =============================================================================

def sql_quote_list(values):
    escaped = [str(v).replace("'", "''") for v in values]
    return ", ".join(f"'{v}'" for v in escaped)

@st.cache_data(ttl=60, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, conn)

def safe_run_query(sql: str, empty_cols=None) -> pd.DataFrame:
    try:
        return run_query(sql)
    except Exception as e:
        err_text = format_athena_error(e)
        logger.error("Query failed: %s\nSQL: %s", err_text, sql)
        st.error(f"❌ Query failed — **AWS error:** `{err_text}`")
        with st.expander("🔍 Show SQL"):
            st.code(sql, language="sql")
        return pd.DataFrame(columns=empty_cols or [])

# =============================================================================
# SIDEBAR – User Info & Global Filters
# =============================================================================

st.sidebar.markdown(
    f"""
    <div class="sidebar-user-card">
        <div class="label">Signed in as</div>
        <div class="value">👤 {AUTH_USERNAME}</div>
        <div class="label" style="margin-top:8px;">Email</div>
        <div class="value">✉️ {st.session_state.get('user_email', AUTH_EMAIL)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.sidebar.button("🚪 Log out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.divider()
st.sidebar.header("🔎 Global Filters")

enable_date_filter = st.sidebar.checkbox("Enable date filter", value=False)

if enable_date_filter:
    bounds_sql = f"SELECT MIN(DATE(timestamp)) AS min_date, MAX(DATE(timestamp)) AS max_date FROM {TXN_TABLE}"
    df_bounds = safe_run_query(bounds_sql, empty_cols=["min_date", "max_date"])
    if not df_bounds.empty and df_bounds.iloc[0]["min_date"] is not None:
        min_date = pd.to_datetime(df_bounds.iloc[0]["min_date"]).date()
        max_date = pd.to_datetime(df_bounds.iloc[0]["max_date"]).date()
    else:
        min_date = date.today() - timedelta(days=30)
        max_date = date.today()

    if "range_start" not in st.session_state:
        st.session_state["range_start"] = min_date
        st.session_state["range_end"] = max_date

    date_range = st.sidebar.date_input(
        "Date range",
        value=(st.session_state["range_start"], st.session_state["range_end"]),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        st.session_state["range_start"] = start_date
        st.session_state["range_end"] = end_date
    else:
        start_date = st.session_state["range_start"]
        end_date = st.session_state["range_end"]

    date_filter = f"DATE(timestamp) BETWEEN DATE('{start_date.isoformat()}') AND DATE('{end_date.isoformat()}')"
else:
    date_filter = "1=1"

selected_risks = st.sidebar.multiselect("Risk level", RISK_LEVELS, default=RISK_LEVELS)
selected_decisions = st.sidebar.multiselect("Decision", DECISIONS, default=DECISIONS)

risk_filter = f"risk_level IN ({sql_quote_list(selected_risks)})" if selected_risks else "1=1"
decision_filter = f"decision IN ({sql_quote_list(selected_decisions)})" if selected_decisions else "1=1"

st.sidebar.divider()
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if st.sidebar.button("🔄 Refresh data (clear cache)"):
    run_query.clear()
    discover_tables.clear()
    st.rerun()

# =============================================================================
# MAIN DASHBOARD – TABS
# =============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Overview", "💳 Transactions", "👤 Users", "⚙️ API & System", "📋 Audit"]
)

# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW
# -----------------------------------------------------------------------------
with tab1:
    st.header("System Overview")
    col1, col2, col3, col4 = st.columns(4)

    txn_sql = f"SELECT COUNT(*) as cnt FROM {TXN_TABLE} WHERE {date_filter}"
    df_txn = safe_run_query(txn_sql)
    total_txns = int(df_txn.iloc[0]['cnt']) if not df_txn.empty else 0
    col1.metric("💳 Transactions", f"{total_txns:,}")

    if has_login:
        login_sql = f"SELECT COUNT(*) as cnt FROM {LOGIN_TABLE} WHERE {date_filter}"
        df_login = safe_run_query(login_sql)
        total_logins = int(df_login.iloc[0]['cnt']) if not df_login.empty else 0
    else:
        total_logins = 0
    col2.metric("🔑 Logins", f"{total_logins:,}")

    if has_api:
        api_sql = f"SELECT COUNT(*) as cnt FROM {API_TABLE} WHERE {date_filter}"
        df_api = safe_run_query(api_sql)
        total_api = int(df_api.iloc[0]['cnt']) if not df_api.empty else 0
    else:
        total_api = 0
    col3.metric("⚡ API Calls", f"{total_api:,}")

    if has_login:
        users_sql = f"SELECT COUNT(DISTINCT username) as cnt FROM {LOGIN_TABLE} WHERE {date_filter}"
        df_users = safe_run_query(users_sql)
        total_users = int(df_users.iloc[0]['cnt']) if not df_users.empty else 0
    else:
        total_users = 0
    col4.metric("👤 Active Users", f"{total_users:,}")

    # Row 2: risk pie + decision funnel
    col1, col2 = st.columns(2)
    with col1:
        risk_sql = f"SELECT risk_level, COUNT(*) as cnt FROM {TXN_TABLE} WHERE {date_filter} AND {risk_filter} GROUP BY risk_level"
        df_risk = safe_run_query(risk_sql)
        if not df_risk.empty:
            fig_risk = px.pie(df_risk, names='risk_level', values='cnt', hole=0.4,
                              color='risk_level', color_discrete_map=COLOR_MAP_RISK)
            fig_risk.update_layout(title="Transaction Risk Distribution", height=320, template="plotly_white")
            st.plotly_chart(fig_risk, use_container_width=True)

    with col2:
        dec_sql = f"SELECT decision, COUNT(*) as cnt FROM {TXN_TABLE} WHERE {date_filter} AND {risk_filter} GROUP BY decision"
        df_dec_funnel = safe_run_query(dec_sql)
        if not df_dec_funnel.empty:
            order = {"REVIEW": 0, "APPROVE": 1, "BLOCK": 2}
            df_dec_funnel = df_dec_funnel.sort_values(by="decision", key=lambda s: s.map(order))
            fig_funnel = go.Figure(go.Funnel(
                y=df_dec_funnel['decision'],
                x=df_dec_funnel['cnt'],
                marker={"color": [COLOR_MAP_DECISION.get(d, ACCENT) for d in df_dec_funnel['decision']]},
                textinfo="value+percent initial",
            ))
            fig_funnel.update_layout(title="Decision Funnel", height=320, template="plotly_white")
            st.plotly_chart(fig_funnel, use_container_width=True)

    # Row 3: risk trend over time (stacked area) — the story of how risk is moving
    st.subheader("Risk Trend Over Time")
    trend_sql = f"""
        SELECT DATE(timestamp) as date, risk_level, COUNT(*) as cnt
        FROM {TXN_TABLE}
        WHERE {date_filter}
        GROUP BY DATE(timestamp), risk_level
        ORDER BY date
    """
    df_trend = safe_run_query(trend_sql)
    if not df_trend.empty:
        fig_trend = px.area(df_trend, x='date', y='cnt', color='risk_level',
                            color_discrete_map=COLOR_MAP_RISK,
                            category_orders={"risk_level": ["LOW", "MEDIUM", "HIGH"]})
        fig_trend.update_layout(height=320, template="plotly_white", legend_title="Risk Level")
        st.plotly_chart(fig_trend, use_container_width=True)

    # Recent activity
    st.subheader("Recent Activity")
    recent_sql = f"""
        SELECT transaction_id, amount, decision, risk_level, timestamp, 'Transaction' as type
        FROM {TXN_TABLE}
        WHERE {date_filter}
        ORDER BY timestamp DESC
        LIMIT 20
    """
    df_recent = safe_run_query(recent_sql)
    if not df_recent.empty:
        st.dataframe(df_recent[['type', 'transaction_id', 'amount', 'decision', 'risk_level', 'timestamp']],
                     use_container_width=True, height=250)

# -----------------------------------------------------------------------------
# TAB 2: TRANSACTIONS
# -----------------------------------------------------------------------------
with tab2:
    st.header("Transaction Analytics")
    kpi_sql = f"""
        SELECT COUNT(*) as cnt, AVG(amount) as avg_amt, AVG(probability) as avg_risk
        FROM {TXN_TABLE}
        WHERE {date_filter} AND {risk_filter} AND {decision_filter}
    """
    df_kpi = safe_run_query(kpi_sql)
    if not df_kpi.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Filtered Txns", f"{int(df_kpi.iloc[0]['cnt']):,}")
        c2.metric("Avg Amount", f"${df_kpi.iloc[0]['avg_amt']:,.2f}" if df_kpi.iloc[0]['avg_amt'] is not None else "N/A")
        c3.metric("Avg Risk Score", f"{df_kpi.iloc[0]['avg_risk']:.2f}" if df_kpi.iloc[0]['avg_risk'] is not None else "N/A")

    vol_sql = f"""
        SELECT DATE(timestamp) as date, COUNT(*) as cnt
        FROM {TXN_TABLE}
        WHERE {date_filter} AND {risk_filter} AND {decision_filter}
        GROUP BY DATE(timestamp)
        ORDER BY date
    """
    df_vol = safe_run_query(vol_sql)
    if not df_vol.empty:
        fig_vol = px.line(df_vol, x='date', y='cnt', title="Daily Transaction Volume", markers=True)
        fig_vol.update_layout(template="plotly_white", height=300)
        st.plotly_chart(fig_vol, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        dec_sql = f"SELECT decision, COUNT(*) as cnt FROM {TXN_TABLE} WHERE {date_filter} AND {risk_filter} AND {decision_filter} GROUP BY decision"
        df_dec = safe_run_query(dec_sql)
        if not df_dec.empty:
            fig_dec = px.pie(df_dec, names='decision', values='cnt', color='decision',
                             color_discrete_map=COLOR_MAP_DECISION, hole=0.4)
            fig_dec.update_layout(title="Decision Split", height=300, template="plotly_white")
            st.plotly_chart(fig_dec, use_container_width=True)
    with col2:
        risk_sql = f"SELECT risk_level, COUNT(*) as cnt FROM {TXN_TABLE} WHERE {date_filter} AND {risk_filter} AND {decision_filter} GROUP BY risk_level"
        df_risk = safe_run_query(risk_sql)
        if not df_risk.empty:
            fig_risk = px.bar(df_risk, x='risk_level', y='cnt', color='risk_level',
                              color_discrete_map=COLOR_MAP_RISK)
            fig_risk.update_layout(title="Risk Breakdown", height=300, template="plotly_white", showlegend=False)
            st.plotly_chart(fig_risk, use_container_width=True)

    # Amount distribution by decision — shows where the money actually sits
    st.subheader("Transaction Amount by Decision")
    amt_sql = f"""
        SELECT amount, decision, risk_level
        FROM {TXN_TABLE}
        WHERE {date_filter} AND {risk_filter} AND {decision_filter}
        LIMIT 20000
    """
    df_amt = safe_run_query(amt_sql)
    if not df_amt.empty:
        fig_box = px.box(df_amt, x='decision', y='amount', color='decision',
                         color_discrete_map=COLOR_MAP_DECISION, points=False)
        fig_box.update_layout(height=320, template="plotly_white", showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    # Hour-of-day x day-of-week heatmap — surfaces attack/usage patterns
    st.subheader("Transaction Volume Heatmap (Hour × Day)")
    heat_sql = f"""
        SELECT day_of_week(timestamp) as dow, hour(timestamp) as hr, COUNT(*) as cnt
        FROM {TXN_TABLE}
        WHERE {date_filter} AND {risk_filter} AND {decision_filter}
        GROUP BY day_of_week(timestamp), hour(timestamp)
    """
    df_heat = safe_run_query(heat_sql)
    if not df_heat.empty:
        dow_labels = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
        df_heat['dow_label'] = df_heat['dow'].map(dow_labels)
        pivot = df_heat.pivot_table(index='dow_label', columns='hr', values='cnt', fill_value=0)
        pivot = pivot.reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        fig_heat = px.imshow(pivot, aspect='auto', color_continuous_scale='Blues',
                             labels=dict(x="Hour of Day", y="Day of Week", color="Txns"))
        fig_heat.update_layout(height=320, template="plotly_white")
        st.plotly_chart(fig_heat, use_container_width=True)

    st.subheader("Approval Queue")
    queue_sql = f"""
        SELECT transaction_id, amount, probability as risk_score, risk_level, decision, timestamp
        FROM {TXN_TABLE}
        WHERE decision = 'REVIEW' AND {date_filter} AND {risk_filter}
        ORDER BY timestamp DESC
        LIMIT 100
    """
    df_queue = safe_run_query(queue_sql)
    if not df_queue.empty:
        st.dataframe(df_queue, use_container_width=True, height=300)
    else:
        st.info("No pending reviews.")

# -----------------------------------------------------------------------------
# TAB 3: USERS
# -----------------------------------------------------------------------------
with tab3:
    st.header("User Analytics")
    if not has_login:
        st.warning(f"Login logs table (`{short_name(LOGIN_TABLE)}`) not found in `{DATABASE}`.")
    else:
        login_trend_sql = f"""
            SELECT DATE(timestamp) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as success,
                   SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failure
            FROM {LOGIN_TABLE}
            WHERE {date_filter}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        df_lt = safe_run_query(login_trend_sql)
        if not df_lt.empty:
            fig_lt = go.Figure()
            fig_lt.add_trace(go.Scatter(x=df_lt['date'], y=df_lt['success'], mode='lines+markers', name='Success', line=dict(color='#2E8B57')))
            fig_lt.add_trace(go.Scatter(x=df_lt['date'], y=df_lt['failure'], mode='lines+markers', name='Failure', line=dict(color='#C0392B')))
            fig_lt.update_layout(title="Login Activity (Success vs Failure)", height=300, template="plotly_white")
            st.plotly_chart(fig_lt, use_container_width=True)

            total_success = df_lt['success'].sum()
            total_failure = df_lt['failure'].sum()
            total_all = total_success + total_failure
            success_rate = (total_success / total_all * 100) if total_all > 0 else 0
            st.metric("Overall Login Success Rate", f"{success_rate:.1f}%")

        top_users_sql = f"""
            SELECT username, COUNT(*) as login_count
            FROM {LOGIN_TABLE}
            WHERE {date_filter}
            GROUP BY username
            ORDER BY login_count DESC
            LIMIT 10
        """
        df_top = safe_run_query(top_users_sql)
        if not df_top.empty:
            fig_top = px.bar(df_top, x='username', y='login_count', title="Top Users by Login Count", color='login_count',
                             color_continuous_scale='Blues')
            fig_top.update_layout(height=300, template="plotly_white")
            st.plotly_chart(fig_top, use_container_width=True)

        if has_activity:
            st.subheader("Recent User Activity")
            act_sql = f"""
                SELECT username, action, details, timestamp
                FROM {ACTIVITY_TABLE}
                WHERE {date_filter}
                ORDER BY timestamp DESC
                LIMIT 50
            """
            df_act = safe_run_query(act_sql)
            if not df_act.empty:
                st.dataframe(df_act, use_container_width=True, height=250)
        else:
            st.info(f"User activity table (`{short_name(ACTIVITY_TABLE)}`) not found — skipping activity feed.")

# -----------------------------------------------------------------------------
# TAB 4: API & SYSTEM
# -----------------------------------------------------------------------------
with tab4:
    st.header("API & System Health")
    if not has_api:
        st.warning(f"API requests table (`{short_name(API_TABLE)}`) not found in `{DATABASE}`.")
    else:
        latency_sql = f"""
            SELECT DATE(timestamp) as date, AVG(latency_ms) as avg_latency, MAX(latency_ms) as max_latency
            FROM {API_TABLE}
            WHERE {date_filter}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        df_lat = safe_run_query(latency_sql)
        if not df_lat.empty:
            fig_lat = go.Figure()
            fig_lat.add_trace(go.Scatter(x=df_lat['date'], y=df_lat['avg_latency'], mode='lines+markers', name='Avg Latency', line=dict(color=ACCENT)))
            fig_lat.add_trace(go.Scatter(x=df_lat['date'], y=df_lat['max_latency'], mode='lines', name='Max Latency', line=dict(color='#C0392B', dash='dot')))
            fig_lat.update_layout(title="API Latency (ms)", height=300, template="plotly_white")
            st.plotly_chart(fig_lat, use_container_width=True)

        status_sql = f"""
            SELECT status, COUNT(*) as cnt
            FROM {API_TABLE}
            WHERE {date_filter}
            GROUP BY status
            ORDER BY cnt DESC
        """
        df_status = safe_run_query(status_sql)
        if not df_status.empty:
            fig_status = px.bar(df_status, x='status', y='cnt', title="API Status Code Distribution", color='status')
            fig_status.update_layout(height=300, template="plotly_white")
            st.plotly_chart(fig_status, use_container_width=True)

        endpoints_sql = f"""
            SELECT endpoint, COUNT(*) as hits
            FROM {API_TABLE}
            WHERE {date_filter}
            GROUP BY endpoint
            ORDER BY hits DESC
            LIMIT 10
        """
        df_ep = safe_run_query(endpoints_sql)
        if not df_ep.empty:
            fig_ep = px.bar(df_ep, x='endpoint', y='hits', title="Top Endpoints", color='hits',
                            color_continuous_scale='Blues')
            fig_ep.update_layout(height=300, template="plotly_white")
            st.plotly_chart(fig_ep, use_container_width=True)

        error_rate_sql = f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status >= 400 THEN 1 ELSE 0 END) as errors
            FROM {API_TABLE}
            WHERE {date_filter}
        """
        df_err = safe_run_query(error_rate_sql)
        if not df_err.empty:
            total = int(df_err.iloc[0]['total'])
            errors = int(df_err.iloc[0]['errors'])
            error_pct = (errors / total * 100) if total > 0 else 0
            c1, c2 = st.columns(2)
            c1.metric("API Error Rate", f"{error_pct:.2f}%", delta=f"{errors} errors")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=error_pct,
                title={'text': "Error Rate %"},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': ACCENT},
                       'steps': [
                           {'range': [0, 2], 'color': '#2E8B57'},
                           {'range': [2, 10], 'color': '#F2A900'},
                           {'range': [10, 100], 'color': '#C0392B'},
                       ]},
            ))
            fig_gauge.update_layout(height=250, template="plotly_white")
            c2.plotly_chart(fig_gauge, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: AUDIT
# -----------------------------------------------------------------------------
with tab5:
    st.header("Audit Log – Decision Overrides")
    if not has_override:
        st.warning(f"Override table (`{short_name(OVR_TABLE)}`) not found in `{DATABASE}`.")
    else:
        audit_count_sql = f"SELECT COUNT(*) as cnt FROM {OVR_TABLE}"
        df_audit_count = safe_run_query(audit_count_sql)
        total_overrides = int(df_audit_count.iloc[0]['cnt']) if not df_audit_count.empty else 0
        st.metric("Total Overrides on Record", f"{total_overrides:,}")

        page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)
        total_pages = max(1, (total_overrides + page_size - 1) // page_size)
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
        offset = (page - 1) * page_size

        audit_sql = f"""
            SELECT transaction_id, original_decision, new_decision, overridden_by, reason, created_at
            FROM {OVR_TABLE}
            ORDER BY created_at DESC
            OFFSET {offset} LIMIT {page_size}
        """
        df_audit = safe_run_query(audit_sql)
        if not df_audit.empty:
            with st.container(height=420):
                st.dataframe(df_audit, use_container_width=True)
            st.caption(f"Showing rows {offset + 1}–{offset + len(df_audit)} of {total_overrides}")

            df_audit_full = safe_run_query(f"""
                SELECT transaction_id, original_decision, new_decision, overridden_by, reason, created_at
                FROM {OVR_TABLE}
                ORDER BY created_at DESC
            """)
            st.download_button(
                "⬇️ Download Full Audit Log",
                data=df_audit_full.to_csv(index=False).encode('utf-8'),
                file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            )

            # Who's overriding what — story: is one reviewer overruling the model a lot?
            st.subheader("Overrides by Reviewer")
            by_reviewer = df_audit_full.groupby('overridden_by').size().reset_index(name='count').sort_values('count', ascending=False)
            fig_rev = px.bar(by_reviewer, x='overridden_by', y='count', color='count', color_continuous_scale='Blues')
            fig_rev.update_layout(height=280, template="plotly_white", showlegend=False)
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("No overrides found.")

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.caption(f"FraudGuard Command Centre · Rendered {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
