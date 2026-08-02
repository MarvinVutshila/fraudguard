from __future__ import annotations

import logging
import json
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# SQL statements
# -------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    transaction_id  TEXT,
    amount          REAL NOT NULL,
    probability     REAL NOT NULL,
    decision        TEXT NOT NULL,
    risk_level      TEXT NOT NULL,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    features        JSONB
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
    last_active     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    blocked_reason  TEXT,
    blocked_at      TIMESTAMPTZ,
    totp_secret     TEXT,
    totp_enabled    BOOLEAN DEFAULT FALSE
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
CREATE INDEX IF NOT EXISTS idx_user_activity_username ON user_activity (username);
"""

CREATE_REFRESH_TOKENS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          SERIAL PRIMARY KEY,
    username    TEXT NOT NULL,
    token       TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_username ON refresh_tokens (username);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens (token);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens (expires_at);
"""

# -------- Monitoring Tables (added for Observability) --------
CREATE_MONITORING_REQUESTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_requests (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    api_key_id      INTEGER,
    endpoint        TEXT NOT NULL,
    method          TEXT NOT NULL,
    status_code     INTEGER NOT NULL,
    response_time   INTEGER NOT NULL,
    client_ip       TEXT,
    user_agent      TEXT,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_requests_user ON api_requests (user_id);
CREATE INDEX IF NOT EXISTS idx_api_requests_timestamp ON api_requests (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_requests_endpoint ON api_requests (endpoint);
"""

CREATE_MONITORING_HOURLY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_usage_hourly (
    id              BIGSERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    api_key_id      INTEGER,
    endpoint        TEXT NOT NULL,
    hour_bucket     TIMESTAMPTZ NOT NULL,
    request_count   INTEGER DEFAULT 0,
    total_latency   BIGINT DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    avg_latency     FLOAT GENERATED ALWAYS AS (total_latency / NULLIF(request_count,0)) STORED,
    UNIQUE(user_id, api_key_id, endpoint, hour_bucket)
);
CREATE INDEX IF NOT EXISTS idx_hourly_bucket ON api_usage_hourly (hour_bucket);
"""

CREATE_SYSTEM_HEALTH_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS system_health (
    id              BIGSERIAL PRIMARY KEY,
    cpu_percent     FLOAT,
    memory_used_mb  FLOAT,
    memory_total_mb FLOAT,
    db_connections  INTEGER,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_system_health_ts ON system_health (timestamp DESC);
"""

# -------- Settings Tables (new) --------
CREATE_API_KEYS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    key         TEXT UNIQUE NOT NULL,
    prefix      TEXT,   -- first 6 chars for display
    last_used   TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys (key);
"""

CREATE_SYSTEM_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS system_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_by  TEXT
);
"""

# -------- Knowledge Base Table (NEW) --------
CREATE_KNOWLEDGE_BASE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_base (
    id          SERIAL PRIMARY KEY,
    category    TEXT DEFAULT 'General',
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    keywords    TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_kb_question ON knowledge_base (question);
"""

# -------------------------------------------------------------------
# Global connection pool
# -------------------------------------------------------------------
_pool: Optional[SimpleConnectionPool] = None
_dsn: Optional[str] = None

def init_db_pool(dsn: str, min_conn: int = 1, max_conn: int = 20) -> None:
    global _pool, _dsn
    _dsn = dsn
    _pool = SimpleConnectionPool(min_conn, max_conn, dsn=dsn)
    logger.info(f"Database pool created (min={min_conn}, max={max_conn})")

def create_tables() -> None:
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_db_pool() first.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            cur.execute(CREATE_OVERRIDES_TABLE_SQL)
            cur.execute(CREATE_USERS_TABLE_SQL)
            cur.execute(CREATE_LOGIN_LOGS_TABLE_SQL)
            cur.execute(CREATE_USER_ACTIVITY_TABLE_SQL)
            cur.execute(CREATE_REFRESH_TOKENS_TABLE_SQL)
            # Monitoring tables
            cur.execute(CREATE_MONITORING_REQUESTS_TABLE_SQL)
            cur.execute(CREATE_MONITORING_HOURLY_TABLE_SQL)
            cur.execute(CREATE_SYSTEM_HEALTH_TABLE_SQL)
            # Settings tables
            cur.execute(CREATE_API_KEYS_TABLE_SQL)
            cur.execute(CREATE_SYSTEM_SETTINGS_TABLE_SQL)
            # Knowledge Base table
            cur.execute(CREATE_KNOWLEDGE_BASE_TABLE_SQL)
        conn.commit()

    # Add missing columns if they don't exist
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check and add last_active
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='users' AND column_name='last_active';
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN last_active TIMESTAMPTZ;")
                logger.info("Added last_active column.")

            # Add blocked_reason
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='users' AND column_name='blocked_reason';
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN blocked_reason TEXT;")
                logger.info("Added blocked_reason column.")

            # Add blocked_at
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='users' AND column_name='blocked_at';
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN blocked_at TIMESTAMPTZ;")
                logger.info("Added blocked_at column.")

            # Add totp_secret
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='users' AND column_name='totp_secret';
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT;")
                logger.info("Added totp_secret column.")

            # Add totp_enabled
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='users' AND column_name='totp_enabled';
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;")
                logger.info("Added totp_enabled column.")

            # Add preferences
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='users' AND column_name='preferences';
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE users ADD COLUMN preferences JSONB DEFAULT '{}';")
                logger.info("Added preferences column.")

            # ✅ Add features column to transactions if missing
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='transactions' AND column_name='features';
            """)
            if not cur.fetchone():
                cur.execute("ALTER TABLE transactions ADD COLUMN features JSONB;")
                logger.info("Added features column to transactions.")

        conn.commit()

    logger.info("Database tables and indexes verified")

@contextmanager
def get_connection():
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_db_pool() first.")
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)

# -------------------------------------------------------------------
# Database class
# -------------------------------------------------------------------
class Database:
    def __init__(self) -> None:
        if _pool is None:
            raise RuntimeError("Database pool not initialised. Call init_db_pool() first.")

    # ---- Transactions ----
    def insert_transaction(self, transaction_id: str, amount: float,
                           probability: float, decision: str,
                           risk_level: str, timestamp: Optional[datetime] = None,
                           features: Optional[Dict[str, Any]] = None) -> int:
        sql = """
            INSERT INTO transactions (transaction_id, amount, probability,
                                      decision, risk_level, timestamp, features)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, NOW()), %s)
            RETURNING id;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (transaction_id, amount, probability,
                                  decision, risk_level, timestamp,
                                  json.dumps(features) if features else None))
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
                new_decision = EXCLUDED.new_decision,
                overridden_by = EXCLUDED.overridden_by,
                reason = EXCLUDED.reason,
                timestamp = NOW()
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (transaction_id, original_decision, new_decision,
                                  overridden_by, reason))
            conn.commit()

    def get_all_overrides(self, limit: int = 100) -> List[Dict[str, Any]]:
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

    # ---- Users ----
    def create_user(self, username: str, password: str,
                    role: str = 'analyst', status: str = 'pending',
                    avatar_url: Optional[str] = None) -> int:
        sql = """
            INSERT INTO users (username, password, role, status, avatar_url, last_active)
            VALUES (%s, %s, %s, %s, %s, NOW())
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

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM users WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone()
        return dict(row) if row else None

    def update_user_status(self, user_id: int, new_status: str) -> None:
        sql = "UPDATE users SET status = %s WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (new_status, user_id))
            conn.commit()

    def update_user_password(self, user_id: int, new_password_hash: str) -> None:
        sql = "UPDATE users SET password = %s WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (new_password_hash, user_id))
            conn.commit()

    def block_user(self, user_id: int, reason: Optional[str] = None) -> None:
        sql = """
            UPDATE users 
            SET status = 'blocked', blocked_reason = %s, blocked_at = NOW() 
            WHERE id = %s;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (reason, user_id))
            conn.commit()

    def unblock_user(self, user_id: int) -> None:
        sql = """
            UPDATE users 
            SET status = 'active', blocked_reason = NULL, blocked_at = NULL 
            WHERE id = %s;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
            conn.commit()

    def delete_user(self, user_id: int) -> None:
        """Permanently delete a user from the database"""
        sql = "DELETE FROM users WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
            conn.commit()

    def get_pending_users(self) -> List[Dict[str, Any]]:
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
        new_status = "active" if approve else "rejected"
        self.update_user_status(user_id, new_status)

    def get_all_users(self) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, username, role, status, avatar_url, last_active, created_at,
                   blocked_reason, blocked_at, totp_enabled, preferences
            FROM users
            ORDER BY username;
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def update_last_active(self, username: str) -> None:
        sql = "UPDATE users SET last_active = NOW() WHERE username = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username,))
            conn.commit()

    # ---- User Preferences (new) ----
    def get_user_preferences(self, username: str) -> Dict[str, Any]:
        sql = "SELECT preferences FROM users WHERE username = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username,))
                row = cur.fetchone()
        return row[0] if row and row[0] else {}

    def update_user_preferences(self, username: str, preferences: Dict[str, Any]) -> None:
        sql = "UPDATE users SET preferences = %s WHERE username = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (json.dumps(preferences), username))
            conn.commit()

    # ---- API Keys (new) ----
    def get_api_keys_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, name, prefix, last_used, expires_at, revoked, created_at
            FROM api_keys
            WHERE user_id = %s
            ORDER BY created_at DESC;
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def create_api_key(self, user_id: int, name: str, key: str, prefix: str, expires_at: datetime) -> int:
        sql = """
            INSERT INTO api_keys (user_id, name, key, prefix, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, name, key, prefix, expires_at))
                key_id = cur.fetchone()[0]
            conn.commit()
        return key_id

    def revoke_api_key(self, key_id: int, user_id: int) -> bool:
        sql = "UPDATE api_keys SET revoked = TRUE WHERE id = %s AND user_id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (key_id, user_id))
                updated = cur.rowcount > 0
            conn.commit()
        return updated

    def get_api_key_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM api_keys WHERE key = %s;"
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (key,))
                row = cur.fetchone()
        return dict(row) if row else None

    def update_api_key_last_used(self, key_id: int) -> None:
        sql = "UPDATE api_keys SET last_used = NOW() WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (key_id,))
            conn.commit()

    # ---- System Settings (new) ----
    def get_system_settings(self) -> Dict[str, Any]:
        sql = "SELECT key, value FROM system_settings;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        return {row[0]: row[1] for row in rows}

    def get_system_setting(self, key: str) -> Optional[Any]:
        sql = "SELECT value FROM system_settings WHERE key = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (key,))
                row = cur.fetchone()
        return row[0] if row else None

    def update_system_setting(self, key: str, value: Any, updated_by: str) -> None:
        sql = """
            INSERT INTO system_settings (key, value, updated_at, updated_by)
            VALUES (%s, %s, NOW(), %s)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (key, json.dumps(value), updated_by))
            conn.commit()

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

    def get_login_logs(self, limit: int = 100, offset: int = 0,
                       username: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, username, success, ip, user_agent, timestamp
            FROM login_logs
        """
        params = []
        if username:
            sql += " WHERE username = %s"
            params.append(username)
        sql += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def count_login_logs(self, username: Optional[str] = None) -> int:
        sql = "SELECT COUNT(*) FROM login_logs"
        params = []
        if username:
            sql += " WHERE username = %s"
            params.append(username)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()[0]

    def get_login_logs_for_user(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_login_logs(limit, 0, username)

    # ---- User Activity ----
    def log_user_activity(self, username: str, action: str,
                          details: Optional[Dict[str, Any]] = None) -> None:
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

    # ---- Refresh Tokens ----
    def create_refresh_tokens_table(self) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_REFRESH_TOKENS_TABLE_SQL)
            conn.commit()
        logger.info("Refresh tokens table verified")

    def store_refresh_token(self, username: str, token: str, expires_at: datetime) -> None:
        sql = """
            INSERT INTO refresh_tokens (username, token, expires_at)
            VALUES (%s, %s, %s)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username, token, expires_at))
            conn.commit()

    def get_refresh_token(self, username: str, token: str) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT * FROM refresh_tokens
            WHERE username = %s AND token = %s AND revoked = FALSE AND expires_at > NOW()
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (username, token))
                row = cur.fetchone()
        return dict(row) if row else None

    def revoke_refresh_token(self, username: str, token: str) -> None:
        sql = "UPDATE refresh_tokens SET revoked = TRUE WHERE username = %s AND token = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username, token))
            conn.commit()

    def revoke_all_refresh_tokens(self, username: str) -> None:
        sql = "UPDATE refresh_tokens SET revoked = TRUE WHERE username = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username,))
            conn.commit()

    def cleanup_expired_refresh_tokens(self) -> int:
        sql = "DELETE FROM refresh_tokens WHERE expires_at < NOW() OR revoked = TRUE"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                deleted = cur.rowcount
            conn.commit()
        return deleted

    # ---- 2FA ----
    def add_totp_columns(self) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='users' AND column_name='totp_secret';
                """)
                if not cur.fetchone():
                    cur.execute("ALTER TABLE users ADD COLUMN totp_secret TEXT;")
                    logger.info("Added totp_secret column.")
                
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='users' AND column_name='totp_enabled';
                """)
                if not cur.fetchone():
                    cur.execute("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;")
                    logger.info("Added totp_enabled column.")
            conn.commit()

    def store_totp_secret(self, username: str, secret: str) -> None:
        sql = "UPDATE users SET totp_secret = %s WHERE username = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (secret, username))
            conn.commit()

    def get_totp_secret(self, username: str) -> Optional[str]:
        sql = "SELECT totp_secret FROM users WHERE username = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username,))
                row = cur.fetchone()
        return row[0] if row else None

    def enable_2fa(self, username: str, secret: str) -> None:
        sql = "UPDATE users SET totp_secret = %s, totp_enabled = TRUE WHERE username = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (secret, username))
            conn.commit()

    def disable_2fa(self, username: str) -> None:
        sql = "UPDATE users SET totp_secret = NULL, totp_enabled = FALSE WHERE username = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username,))
            conn.commit()

    def is_2fa_enabled(self, username: str) -> bool:
        sql = "SELECT totp_enabled FROM users WHERE username = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username,))
                row = cur.fetchone()
        return row[0] if row else False

    # ---- User Management Stats ----
    def get_user_stats(self) -> Dict[str, Any]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
                active_users = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
                pending_users = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM users WHERE status = 'blocked'")
                blocked_users = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM users WHERE status = 'rejected'")
                rejected_users = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
                admin_users = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM users WHERE totp_enabled = TRUE")
                twofa_enabled = cur.fetchone()[0]
                
        return {
            "total_users": total_users,
            "active_users": active_users,
            "pending_users": pending_users,
            "blocked_users": blocked_users,
            "rejected_users": rejected_users,
            "admin_users": admin_users,
            "twofa_enabled": twofa_enabled
        }

    # ---- Security Alerts ----
    def get_brute_force_alerts(self, minutes: int = 15, threshold: int = 5) -> List[Dict[str, Any]]:
        sql = """
            SELECT username, COUNT(*) as attempts, 
                   MAX(timestamp) as last_attempt,
                   MIN(timestamp) as first_attempt,
                   array_agg(DISTINCT ip) as ips
            FROM login_logs
            WHERE success = false
            AND timestamp > NOW() - INTERVAL '%s minutes'
            GROUP BY username
            HAVING COUNT(*) > %s
            ORDER BY last_attempt DESC
        """
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (minutes, threshold))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_recent_failed_logins(self, username: str, hours: int = 24) -> int:
        sql = """
            SELECT COUNT(*) 
            FROM login_logs
            WHERE username = %s 
            AND success = false
            AND timestamp > NOW() - INTERVAL '%s hours'
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (username, hours))
                row = cur.fetchone()
        return row[0] if row else 0

    def get_total_failed_logins_last_24h(self) -> int:
        sql = """
            SELECT COUNT(*) 
            FROM login_logs
            WHERE success = false
            AND timestamp > NOW() - INTERVAL '24 hours'
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchone()[0]

    # ---- Cleanup ----
    def cleanup_old_logs(self, days: int = 30) -> Dict[str, int]:
        results = {}
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM login_logs WHERE timestamp < NOW() - INTERVAL '%s days'", (days,))
                results['login_logs'] = cur.rowcount
            conn.commit()
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_activity WHERE timestamp < NOW() - INTERVAL '%s days'", (days,))
                results['user_activity'] = cur.rowcount
            conn.commit()
        
        results['refresh_tokens'] = self.cleanup_expired_refresh_tokens()
        
        return results

    # ---- Knowledge Base (NEW) ----
    def get_knowledge_base_entries(self, search: str = "", limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List knowledge base entries with optional search."""
        if search:
            sql = """
                SELECT id, category, question, answer, usage_count, created_at, updated_at
                FROM knowledge_base
                WHERE question ILIKE %s OR answer ILIKE %s OR keywords ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
            """
            pattern = f"%{search}%"
            params = (pattern, pattern, pattern, limit, offset)
        else:
            sql = """
                SELECT id, category, question, answer, usage_count, created_at, updated_at
                FROM knowledge_base
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
            """
            params = (limit, offset)
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def count_knowledge_base_entries(self, search: str = "") -> int:
        """Count total KB entries (with search)."""
        if search:
            sql = """
                SELECT COUNT(*) FROM knowledge_base
                WHERE question ILIKE %s OR answer ILIKE %s OR keywords ILIKE %s;
            """
            pattern = f"%{search}%"
            params = (pattern, pattern, pattern)
        else:
            sql = "SELECT COUNT(*) FROM knowledge_base;"
            params = ()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()[0]

    def get_knowledge_base_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM knowledge_base WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (entry_id,))
                row = cur.fetchone()
        return dict(row) if row else None

    def create_knowledge_base_entry(self, question: str, answer: str, category: str = "General", keywords: str = "") -> int:
        sql = """
            INSERT INTO knowledge_base (category, question, answer, keywords)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (category, question, answer, keywords))
                entry_id = cur.fetchone()[0]
            conn.commit()
        return entry_id

    def update_knowledge_base_entry(self, entry_id: int, question: str, answer: str, category: str, keywords: str) -> bool:
        sql = """
            UPDATE knowledge_base
            SET category = %s, question = %s, answer = %s, keywords = %s, updated_at = NOW()
            WHERE id = %s;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (category, question, answer, keywords, entry_id))
                updated = cur.rowcount > 0
            conn.commit()
        return updated

    def delete_knowledge_base_entry(self, entry_id: int) -> bool:
        sql = "DELETE FROM knowledge_base WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (entry_id,))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def increment_knowledge_base_usage(self, entry_id: int) -> None:
        sql = "UPDATE knowledge_base SET usage_count = usage_count + 1 WHERE id = %s;"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (entry_id,))
            conn.commit()