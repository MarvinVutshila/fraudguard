from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import List, Optional, Dict, Any

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# SQL Statements (run only once at application startup)
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

# -------------------------------------------------------------------
# Global connection pool (initialized once at startup)
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
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            cur.execute(CREATE_OVERRIDES_TABLE_SQL)
        conn.commit()
    logger.info("Database tables and indexes verified")


@contextmanager
def get_connection():
    """
    Context manager that returns a connection from the pool.
    The connection is automatically returned to the pool when the block exits.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)


# -------------------------------------------------------------------
# Database class – uses the pool internally, no per-query connection overhead
# -------------------------------------------------------------------
class Database:
    """
    Main database accessor. Reuses the global connection pool.
    Do NOT create a new instance per request – create ONE global instance.
    """
    
    def __init__(self) -> None:
        """No DDL here – tables must already exist."""
        if _pool is None:
            raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    
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
        # Same as fetch_history – you can keep both or remove one
        return self.fetch_history(limit, offset, decision)
    
    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM transactions WHERE transaction_id = %s;"
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (transaction_id,))
                row = cur.fetchone()
        return dict(row) if row else None
    
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
