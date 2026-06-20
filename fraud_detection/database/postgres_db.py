from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# SQL statements (run only once)
# -------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    transaction_id  TEXT,
    amount          REAL NOT NULL,
    probability     REAL NOT NULL,
    decision        TEXT NOT NULL,
    risk_level      TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_txn_timestamp ON transactions (timestamp DESC);
"""

CREATE_OVERRIDES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transaction_overrides (
    transaction_id      TEXT PRIMARY KEY,
    original_decision   TEXT NOT NULL,
    new_decision        TEXT NOT NULL,
    overridden_by       TEXT NOT NULL,
    reason              TEXT,
    timestamp           TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    password        TEXT NOT NULL,
    role            TEXT DEFAULT 'analyst',
    status          TEXT DEFAULT 'pending',
    avatar_url      TEXT,
    failed_attempts INTEGER DEFAULT 0,
    lock_until      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

CREATE_LOGIN_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS login_logs (
    id          SERIAL PRIMARY KEY,
    username    TEXT,
    success     BOOLEAN,
    ip          TEXT,
    user_agent  TEXT,
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_login_logs_timestamp ON login_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_login_logs_username ON login_logs (username);
"""

CREATE_USER_ACTIVITY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_activity (
    id          SERIAL PRIMARY KEY,
    username    TEXT,
    action      TEXT,
    details     JSONB,
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity (timestamp DESC);
"""

# -------------------------------------------------------------------
# Global connection pool (initialised once at startup)
# -------------------------------------------------------------------
_pool: Optional[SimpleConnectionPool] = None
_dsn: Optional[str] = None


def init_db_pool(dsn: str, min_conn: int = 1, max_conn: int = 20) -> None:
    """Call this ONCE when your application starts."""
    global _pool, _dsn
    _dsn = dsn
    _pool = SimpleConnectionPool(min_conn, max_conn, dsn=dsn)
    logger.info(f"Database pool created (min={min_conn}, max={max_conn})")


def create_tables() -> None:
    """Run table creation – call once at startup after init_db_pool()."""
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_db_pool() first.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            cur.execute(CREATE_OVERRIDES_TABLE_SQL)
            cur.execute(CREATE_USERS_TABLE_SQL)
            cur.execute(CREATE_LOGIN_LOGS_TABLE_SQL)
            cur.execute(CREATE_USER_ACTIVITY_TABLE_SQL)
        conn.commit()
    logger.info("Database tables and indexes verified")


@contextmanager
def get_connection():
    """
    Context manager that returns a connection from the pool.
    The connection is automatically returned to the pool when the block exits.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_db_pool() first.")

    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)


# -------------------------------------------------------------------
# Database class – uses the pool internally, no per-query overhead
# -------------------------------------------------------------------
class Database:
    """
    Main database accessor. Reuses the global connection pool.
    Do NOT create a new instance per request – create ONE global instance.
    """

    def __init__(self) -> None:
        """No DDL here – tables must already exist."""
        if _pool is None:
            raise RuntimeError("Database pool not initialised. Call init_db_pool() first.")

    # ---- Transactions ----
    def insert_transaction(self, transaction_id: str, amount: float,
                           probability: float, decision: str,
                           risk_level: str, timestamp) -> int:
        sql = """
            INSERT INTO transactions (transaction_id, amount, probability,
                                      decision, risk_level, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (transaction_id, amount, probability,
                                  decision, risk_level, timestamp))
                row_id = cur.fetchone()[0]
            conn.commit()
        return row_id

    def fetch_history(self, limit: int, offset: int,
                      decision_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if decision_filter:
            sql = """
                SELECT * FROM transactions
                WHERE decision = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s;
            """
            params = (decision_filter.upper(), limit, offset)
        else:
            sql = """
                SELECT * FROM transactions
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s;
            """
            params = (limit, offset)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def count_transactions(self, decision_filter: Optional[str] = None) -> int:
        if decision_filter:
            sql = "SELECT COUNT(*) FROM transactions WHERE decision = %s;"
            params = (decision_filter.upper(),)
        else:
            sql = "SELECT COUNT(*) FROM transactions;"
            params = ()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()[0]

    def get_transactions(self, limit: int = 100, offset: int = 0,
                         decision: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.fetch_history(limit, offset, decision)

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM transactions WHERE transaction_id = %s;"
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (transaction_id,))
                row = cur.fetchone()
        return dict(row) if row else None

    # ---- Overrides ----
    def get_override(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM transaction_overrides WHERE transaction_id = %s;"
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (transaction_id,))
                row = cur.fetchone()
        return dict(row) if row else None

    def set_override(self, transaction_id: str, original_decision: str,
                     new_decision: str, overridden_by: str, reason: str) -> None:
        sql = """
            INSERT INTO transaction_overrides
                (transaction_id, original_decision, new_decision, overridden_by, reason)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (transaction_id) DO UPDATE SET
                original_decision = EXCLUDED.original_decision,
                new_decision = EXCLUDED.new_decision,
                overridden_by = EXCLUDED.overridden_by,
                reason = EXCLUDED.reason,
                timestamp = NOW();
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (transaction_id, original_decision, new_decision,
                                  overridden_by, reason))
            conn.commit()

    # ---- FIXED: Get all overrides with transaction details for audit log ----
    def get_all_overrides(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch override history with transaction details for the Approval Audit Log."""
        sql = """
            SELECT 
                o.transaction_id,
                COALESCE(t.amount, 0.0) AS amount,
                COALESCE(t.probability, 0.0) AS probability,
                o.original_decision AS model,
                o.new_decision AS human_decision,
                o.overridden_by AS analyst,
                o.reason,
                o.timestamp
            FROM transaction_overrides o
            LEFT JOIN transactions t ON o.transaction_id = t.transaction_id
            ORDER BY o.timestamp DESC
            LIMIT %s;
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    # ---- FIXED: Update transaction decision and risk level ----
    def update_transaction_decision(self, transaction_id: str, decision: str, risk_level: str) -> None:
        sql = """
            UPDATE transactions
            SET decision = %s, risk_level = %s
            WHERE transaction_id = %s;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (decision, risk_level, transaction_id))
            conn.commit()

    # ---- Users (aligned with auth.py) ----
    def create_user(self, username: str, password: str,
                    role: str = 'analyst', status: str = 'pending',
                    avatar_url: Optional[str] = None) -> int:
        sql = """
            INSERT INTO users (username, password, role, status, avatar_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username, password, role, status, avatar_url))
                user_id = cur.fetchone()[0]
            conn.commit()
        return user_id

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM users WHERE username = %s;"
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (username,))
                row = cur.fetchone()
        return dict(row) if row else None

    def update_user_status(self, user_id: int, new_status: str) -> None:
        sql = "UPDATE users SET status = %s WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (new_status, user_id))
            conn.commit()

    def get_pending_users(self) -> List[Dict[str, Any]]:
        """Fetch all users with status = 'pending' for admin approval."""
        sql = """
            SELECT id, username, role, avatar_url, created_at
            FROM users
            WHERE status = 'pending'
            ORDER BY created_at ASC;
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def approve_user(self, user_id: int, approve: bool) -> None:
        """Approve or reject a pending user."""
        new_status = "active" if approve else "rejected"
        self.update_user_status(user_id, new_status)

    # ---- Login logs ----
    def log_login_attempt(self, username: str, success: bool,
                          ip: Optional[str] = None,
                          user_agent: Optional[str] = None) -> None:
        sql = """
            INSERT INTO login_logs (username, success, ip, user_agent, timestamp)
            VALUES (%s, %s, %s, %s, NOW());
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username, success, ip, user_agent))
            conn.commit()

    def get_login_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        sql = """
            SELECT username, success, ip, user_agent, timestamp
            FROM login_logs
            ORDER BY timestamp DESC
            LIMIT %s;
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    # ---- User Activity ----
    def log_user_activity(self, username: str, action: str,
                          details: Optional[Dict[str, Any]] = None) -> None:
        import json
        sql = """
            INSERT INTO user_activity (username, action, details, timestamp)
            VALUES (%s, %s, %s, NOW());
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username, action, json.dumps(details) if details else None))
            conn.commit()

    def get_user_activity(self, username: Optional[str] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        if username:
            sql = """
                SELECT username, action, details, timestamp
                FROM user_activity
                WHERE username = %s
                ORDER BY timestamp DESC
                LIMIT %s;
            """
            params = (username, limit)
        else:
            sql = """
                SELECT username, action, details, timestamp
                FROM user_activity
                ORDER BY timestamp DESC
                LIMIT %s;
            """
            params = (limit,)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [dict(row) for row in rows]