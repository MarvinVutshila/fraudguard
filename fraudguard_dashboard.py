"""
FraudGuard Operations Dashboard
--------------------------------
A production-ready Streamlit dashboard for monitoring a fraud-detection
pipeline backed by AWS Athena.

Data source:
    Athena database: fraudguard_dwh
    Primary tables:  silver_transactions, silver_transaction_overrides
    Fallback tables: transactions, transaction_overrides
    (fallback is used automatically if the "silver" table does not exist)

Run with:
    streamlit run fraudguard_dashboard.py

Requires:
    pip install streamlit pandas plotly pyathena
"""

import time
import traceback
from datetime import datetime, timedelta, date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pyathena import connect
from pyathena.error import OperationalError, DatabaseError

# =============================================================================
# CONFIG
# =============================================================================

DATABASE = "fraudguard_dwh"
S3_STAGING_DIR = "s3://fraudguard-warehouse-2026/athena-results/"
AWS_REGION = "eu-west-2"

RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
DECISIONS = ["REVIEW", "APPROVE", "BLOCK"]

# Colour palette (professional / muted, colour-blind friendly)
COLOR_MAP_DECISION = {"REVIEW": "#F2A900", "APPROVE": "#2E8B57", "BLOCK": "#C0392B"}
COLOR_MAP_RISK = {"LOW": "#2E8B57", "MEDIUM": "#F2A900", "HIGH": "#C0392B"}
ACCENT = "#1F4E79"

st.set_page_config(
    page_title="FraudGuard Ops",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Light custom styling ---------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {padding-top: 1.5rem;}
        div[data-testid="stMetric"] {
            background: #F7F9FB;
            border: 1px solid #E3E8EF;
            border-radius: 10px;
            padding: 14px 16px;
        }
        div[data-testid="stMetricLabel"] {font-weight: 600; color: #4A5568;}
        h1, h2, h3 {color: #1F2933;}
        .stAlert {border-radius: 8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛡️ FraudGuard Operations Dashboard")
st.caption("Real-time monitoring of fraud decisions, review queue, and analyst overrides")

# =============================================================================
# CONNECTION
# =============================================================================


@st.cache_resource(show_spinner=False)
def get_connection():
    return connect(
        s3_staging_dir=S3_STAGING_DIR,
        region_name=AWS_REGION,
        database=DATABASE,
    )


def init_connection():
    try:
        conn = get_connection()
        return conn, None
    except Exception as e:  # noqa: BLE001
        return None, e


conn, conn_error = init_connection()

if conn_error is not None:
    st.error("❌ Could not connect to Athena. The dashboard cannot load any data.")
    with st.expander("Error details"):
        st.code("".join(traceback.format_exception(type(conn_error), conn_error, conn_error.__traceback__)))
    st.stop()

# =============================================================================
# TABLE RESOLUTION (silver -> raw fallback), cached for the session
# =============================================================================


@st.cache_data(ttl=300, show_spinner=False)
def table_exists(_conn_marker: str, table_name: str) -> bool:
    """Check information_schema to see if a table exists in fraudguard_dwh.
    _conn_marker is unused except to key the cache per-connection lifetime."""
    query = f"""
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = '{DATABASE}' AND table_name = '{table_name}'
    """
    try:
        df = pd.read_sql(query, conn)
        return bool(df.iloc[0]["cnt"] > 0)
    except Exception:
        # If information_schema itself is unreachable, fall back to a direct probe
        try:
            pd.read_sql(f"SELECT 1 FROM {DATABASE}.{table_name} LIMIT 1", conn)
            return True
        except Exception:
            return False


@st.cache_data(ttl=300, show_spinner=False)
def resolve_table(_conn_marker: str, silver_name: str, raw_name: str):
    """Return (fully_qualified_table_name, used_fallback: bool, resolved: bool)."""
    if table_exists(_conn_marker, silver_name):
        return f"{DATABASE}.{silver_name}", False, True
    if table_exists(_conn_marker, raw_name):
        return f"{DATABASE}.{raw_name}", True, True
    return None, False, False


TXN_TABLE, txn_fallback_used, txn_resolved = resolve_table("v1", "silver_transactions", "transactions")
OVR_TABLE, ovr_fallback_used, ovr_resolved = resolve_table("v1", "silver_transaction_overrides", "transaction_overrides")

if not txn_resolved:
    st.error(
        "❌ Neither `fraudguard_dwh.silver_transactions` nor `fraudguard_dwh.transactions` "
        "could be found. The dashboard cannot display transaction data."
    )
    st.stop()

if txn_fallback_used:
    st.warning(f"⚠️ `silver_transactions` not found — falling back to `{TXN_TABLE}`.")

if not ovr_resolved:
    st.info(
        "ℹ️ No override/audit table found (`silver_transaction_overrides` or "
        "`transaction_overrides`). Audit log will be shown as empty."
    )
elif ovr_fallback_used:
    st.warning(f"⚠️ `silver_transaction_overrides` not found — falling back to `{OVR_TABLE}`.")

# =============================================================================
# QUERY HELPERS
# =============================================================================


def sql_quote_list(values):
    """Safely build a SQL IN (...) list from a small, known set of string values."""
    escaped = [str(v).replace("'", "''") for v in values]
    return ", ".join(f"'{v}'" for v in escaped)


@st.cache_data(ttl=60, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, conn)


def safe_run_query(sql: str, empty_cols=None) -> pd.DataFrame:
    """Run a query, returning an empty DataFrame (with optional columns) on failure."""
    try:
        return run_query(sql)
    except (OperationalError, DatabaseError) as e:
        st.error(f"Query failed: {e}")
    except Exception as e:  # noqa: BLE001
        st.error(f"Unexpected query error: {e}")
    return pd.DataFrame(columns=empty_cols or [])


# =============================================================================
# SIDEBAR FILTERS
# =============================================================================

st.sidebar.header("🔎 Filters")

default_end = date.today()
default_start = default_end - timedelta(days=30)

date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start, default_end),
    max_value=default_end,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, default_end

selected_risk_levels = st.sidebar.multiselect(
    "Risk level", options=RISK_LEVELS, default=RISK_LEVELS
)

selected_decisions = st.sidebar.multiselect(
    "Decision", options=DECISIONS, default=DECISIONS
)

st.sidebar.divider()
st.sidebar.header("🔄 Refresh")
auto_refresh = st.sidebar.checkbox("Auto-refresh every 60s", value=False)
manual_refresh = st.sidebar.button("Refresh now", use_container_width=True)

if manual_refresh:
    st.cache_data.clear()
    st.rerun()

if auto_refresh:
    # Lightweight auto-refresh without extra dependencies.
    st_autorefresh_available = False
    try:
        from streamlit_autorefresh import st_autorefresh  # type: ignore

        st_autorefresh(interval=60_000, key="fraudguard_autorefresh")
        st_autorefresh_available = True
    except ImportError:
        pass

    if not st_autorefresh_available:
        st.sidebar.caption(
            "Tip: `pip install streamlit-autorefresh` for smoother auto-refresh. "
            "Using a basic 60s sleep-and-rerun loop instead."
        )
        placeholder = st.sidebar.empty()
        for remaining in range(60, 0, -1):
            placeholder.caption(f"Next refresh in {remaining}s")
            time.sleep(1)
        st.cache_data.clear()
        st.rerun()

# Guard against an empty multiselect breaking the SQL IN clause
_risk_filter = selected_risk_levels if selected_risk_levels else RISK_LEVELS
_decision_filter = selected_decisions if selected_decisions else DECISIONS

WHERE_CLAUSE = f"""
    WHERE DATE(timestamp) BETWEEN DATE('{start_date.isoformat()}') AND DATE('{end_date.isoformat()}')
      AND risk_level IN ({sql_quote_list(_risk_filter)})
      AND decision IN ({sql_quote_list(_decision_filter)})
"""

st.sidebar.divider()
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# =============================================================================
# 1. KPI ROW
# =============================================================================

st.header("📈 Key Metrics")

kpi_sql = f"""
    SELECT
        COUNT(*) AS total_txns,
        SUM(CASE WHEN decision = 'REVIEW' THEN 1 ELSE 0 END) AS pending_reviews,
        AVG(probability) AS avg_risk_score,
        AVG(amount) AS avg_amount
    FROM {TXN_TABLE}
    {WHERE_CLAUSE}
"""
df_kpi = safe_run_query(kpi_sql, empty_cols=["total_txns", "pending_reviews", "avg_risk_score", "avg_amount"])

if not df_kpi.empty:
    total_txns = int(df_kpi.iloc[0]["total_txns"] or 0)
    pending_reviews = int(df_kpi.iloc[0]["pending_reviews"] or 0)
    avg_risk_score = float(df_kpi.iloc[0]["avg_risk_score"] or 0)
    avg_amount = float(df_kpi.iloc[0]["avg_amount"] or 0)
else:
    total_txns = pending_reviews = avg_risk_score = avg_amount = 0

if ovr_resolved:
    overrides_sql = f"""
        SELECT COUNT(*) AS cnt
        FROM {OVR_TABLE}
        WHERE DATE(created_at) BETWEEN DATE('{start_date.isoformat()}') AND DATE('{end_date.isoformat()}')
    """
    df_ovr_count = safe_run_query(overrides_sql, empty_cols=["cnt"])
    total_overrides = int(df_ovr_count.iloc[0]["cnt"]) if not df_ovr_count.empty else 0
else:
    total_overrides = 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💳 Total Transactions", f"{total_txns:,}")
c2.metric("⏳ Pending Reviews", f"{pending_reviews:,}")
c3.metric("📝 Total Overrides", f"{total_overrides:,}")
c4.metric("📊 Avg Risk Score", f"{avg_risk_score:.2f}")
c5.metric("💰 Avg Amount", f"${avg_amount:,.2f}")

st.divider()

# =============================================================================
# 2. TIME SERIES — DAILY TRANSACTION VOLUME WITH TREND
# =============================================================================

st.header("📅 Daily Transaction Volume")

volume_sql = f"""
    SELECT DATE(timestamp) AS txn_date, COUNT(*) AS txn_count
    FROM {TXN_TABLE}
    {WHERE_CLAUSE}
    GROUP BY DATE(timestamp)
    ORDER BY txn_date
"""
df_volume = safe_run_query(volume_sql, empty_cols=["txn_date", "txn_count"])

if not df_volume.empty:
    df_volume["txn_date"] = pd.to_datetime(df_volume["txn_date"])
    df_volume = df_volume.sort_values("txn_date")
    df_volume["trend"] = df_volume["txn_count"].rolling(window=7, min_periods=1).mean()

    fig_volume = go.Figure()
    fig_volume.add_trace(
        go.Scatter(
            x=df_volume["txn_date"],
            y=df_volume["txn_count"],
            mode="lines+markers",
            name="Daily volume",
            line=dict(color=ACCENT, width=2),
        )
    )
    fig_volume.add_trace(
        go.Scatter(
            x=df_volume["txn_date"],
            y=df_volume["trend"],
            mode="lines",
            name="7-day trend",
            line=dict(color="#C0392B", width=2, dash="dash"),
        )
    )
    fig_volume.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title=None,
        yaxis_title="Transactions",
        template="plotly_white",
    )
    st.plotly_chart(fig_volume, use_container_width=True)
else:
    st.info("No transaction volume data available for the selected filters.")

st.divider()

# =============================================================================
# 3. PIE (DECISIONS) + BAR (RISK LEVELS)
# =============================================================================

st.header("📊 Distribution Analytics")
col_pie, col_bar = st.columns(2)

with col_pie:
    st.subheader("Decision Split")
    decision_sql = f"""
        SELECT decision, COUNT(*) AS cnt
        FROM {TXN_TABLE}
        {WHERE_CLAUSE}
        GROUP BY decision
    """
    df_decision = safe_run_query(decision_sql, empty_cols=["decision", "cnt"])
    if not df_decision.empty:
        fig_pie = px.pie(
            df_decision,
            names="decision",
            values="cnt",
            color="decision",
            color_discrete_map=COLOR_MAP_DECISION,
            hole=0.45,
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No decision data available for the selected filters.")

with col_bar:
    st.subheader("Risk Level Breakdown")
    risk_sql = f"""
        SELECT risk_level, COUNT(*) AS cnt
        FROM {TXN_TABLE}
        {WHERE_CLAUSE}
        GROUP BY risk_level
    """
    df_risk = safe_run_query(risk_sql, empty_cols=["risk_level", "cnt"])
    if not df_risk.empty:
        df_risk["risk_level"] = pd.Categorical(df_risk["risk_level"], categories=RISK_LEVELS, ordered=True)
        df_risk = df_risk.sort_values("risk_level")
        fig_bar = px.bar(
            df_risk,
            x="risk_level",
            y="cnt",
            color="risk_level",
            color_discrete_map=COLOR_MAP_RISK,
            text="cnt",
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            xaxis_title=None,
            yaxis_title="Transactions",
            template="plotly_white",
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No risk-level data available for the selected filters.")

st.divider()

# =============================================================================
# 4. SCATTER — AMOUNT vs PROBABILITY (coloured by risk level)
# =============================================================================

st.header("🔬 Amount vs. Risk Probability")

scatter_sql = f"""
    SELECT transaction_id, amount, probability, risk_level, decision
    FROM {TXN_TABLE}
    {WHERE_CLAUSE}
"""
df_scatter = safe_run_query(
    scatter_sql, empty_cols=["transaction_id", "amount", "probability", "risk_level", "decision"]
)

if not df_scatter.empty:
    fig_scatter = px.scatter(
        df_scatter,
        x="amount",
        y="probability",
        color="risk_level",
        color_discrete_map=COLOR_MAP_RISK,
        hover_data=["transaction_id", "decision"],
        opacity=0.7,
    )
    fig_scatter.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Amount",
        yaxis_title="Probability (risk score)",
        template="plotly_white",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.info("No transaction-level data available for the selected filters.")

st.divider()

# =============================================================================
# 5. HEATMAP — HOUR OF DAY vs DAY OF WEEK
# =============================================================================

st.header("🌡️ Transaction Heatmap (Hour vs. Day of Week)")

heatmap_sql = f"""
    SELECT
        day_of_week(timestamp) AS dow,
        hour(timestamp) AS hr,
        COUNT(*) AS cnt
    FROM {TXN_TABLE}
    {WHERE_CLAUSE}
    GROUP BY day_of_week(timestamp), hour(timestamp)
"""
df_heatmap = safe_run_query(heatmap_sql, empty_cols=["dow", "hr", "cnt"])

DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

if not df_heatmap.empty:
    pivot = (
        df_heatmap.pivot_table(index="dow", columns="hr", values="cnt", fill_value=0)
        .reindex(index=range(1, 8), columns=range(0, 24), fill_value=0)
    )
    pivot.index = DOW_LABELS

    fig_heat = px.imshow(
        pivot,
        labels=dict(x="Hour of day", y="Day of week", color="Transactions"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig_heat.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white")
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("No data available to build the hour/day heatmap for the selected filters.")

st.divider()

# =============================================================================
# 6. TABLES — APPROVAL QUEUE + AUDIT LOG (with CSV export)
# =============================================================================

st.header("📋 Live Data")
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("⏳ Approval Queue")
    queue_sql = f"""
        SELECT transaction_id, amount, probability AS risk_score, risk_level, decision, timestamp
        FROM {TXN_TABLE}
        WHERE decision = 'REVIEW'
          AND DATE(timestamp) BETWEEN DATE('{start_date.isoformat()}') AND DATE('{end_date.isoformat()}')
          AND risk_level IN ({sql_quote_list(_risk_filter)})
        ORDER BY timestamp DESC
        LIMIT 200
    """
    df_queue = safe_run_query(
        queue_sql,
        empty_cols=["transaction_id", "amount", "risk_score", "risk_level", "decision", "timestamp"],
    )
    if not df_queue.empty:
        st.dataframe(df_queue, use_container_width=True, height=320)
        st.download_button(
            "⬇️ Download queue as CSV",
            data=df_queue.to_csv(index=False).encode("utf-8"),
            file_name=f"fraudguard_approval_queue_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No pending reviews for the selected filters.")

with right_col:
    st.subheader("📝 Audit Log")
    if ovr_resolved:
        audit_sql = f"""
            SELECT transaction_id, original_decision, new_decision, overridden_by, reason, created_at
            FROM {OVR_TABLE}
            WHERE DATE(created_at) BETWEEN DATE('{start_date.isoformat()}') AND DATE('{end_date.isoformat()}')
            ORDER BY created_at DESC
            LIMIT 200
        """
        df_audit = safe_run_query(
            audit_sql,
            empty_cols=[
                "transaction_id",
                "original_decision",
                "new_decision",
                "overridden_by",
                "reason",
                "created_at",
            ],
        )
        if not df_audit.empty:
            st.dataframe(df_audit, use_container_width=True, height=320)
            st.download_button(
                "⬇️ Download audit log as CSV",
                data=df_audit.to_csv(index=False).encode("utf-8"),
                file_name=f"fraudguard_audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("No overrides found for the selected filters.")
    else:
        st.info("Audit log table not available in this environment.")

st.divider()
st.caption(
    f"FraudGuard Ops · Data source: `{TXN_TABLE}`"
    + (f" · `{OVR_TABLE}`" if ovr_resolved else "")
    + f" · Rendered {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
