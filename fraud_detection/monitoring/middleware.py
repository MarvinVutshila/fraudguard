import asyncio
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request
import psycopg2
from psycopg2.extras import execute_values
from jose import JWTError, jwt
import os
from fraud_detection.core.config import DB_DSN

logger = logging.getLogger(__name__)

# --- Queue for incoming request logs ---
_request_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)
_worker_task = None
_health_collector_thread = None
_stop_event = threading.Event()

# --- Cache for user_id lookups (username -> user_id) ---
_user_cache: Dict[str, int] = {}
_cache_lock = threading.Lock()


def get_user_id_from_username(username: str) -> Optional[int]:
    """Fetch user_id from database, with caching."""
    if not username:
        return None

    with _cache_lock:
        if username in _user_cache:
            return _user_cache[username]

    # Query the database
    try:
        conn = psycopg2.connect(DB_DSN)
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            user_id = row[0] if row else None
        conn.close()

        with _cache_lock:
            if user_id is not None:
                _user_cache[username] = user_id
        return user_id
    except Exception as e:
        logger.error(f"Failed to look up user_id for {username}: {e}")
        return None


def extract_user_id_from_token(token: str) -> Optional[int]:
    """Decode JWT and extract user_id from 'sub' claim."""
    try:
        SECRET_KEY = os.getenv("JWT_SECRET_KEY")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username:
            return get_user_id_from_username(username)
    except JWTError:
        pass
    return None


def get_user_id_from_request(request: Request) -> Optional[int]:
    """Extract user_id from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        return extract_user_id_from_token(token)
    return None


# ---------- Middleware ----------
async def log_request_middleware(request: Request, call_next):
    """FastAPI middleware to capture request metrics with user tracking."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start_time) * 1000)
    user_id = get_user_id_from_request(request)

    log_entry = {
        "user_id": user_id,
        "api_key_id": None,
        "endpoint": request.url.path,
        "method": request.method,
        "status_code": response.status_code,
        "response_time": duration_ms,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": datetime.utcnow()
    }

    try:
        _request_queue.put_nowait(log_entry)
    except asyncio.QueueFull:
        logger.warning("Monitoring queue full. Dropping request log.")

    return response


def attach_monitoring_middleware(app):
    """Attach the request logging middleware to the FastAPI app.
    Must be called BEFORE the app starts (i.e., before lifespan)."""
    app.middleware("http")(log_request_middleware)
    logger.info("Monitoring middleware attached.")


# ---------- Background Worker (unchanged) ----------
async def monitoring_worker():
    while True:
        await asyncio.sleep(5)
        batch = []
        while not _request_queue.empty() and len(batch) < 50:
            try:
                item = _request_queue.get_nowait()
                batch.append(item)
            except asyncio.QueueEmpty:
                break
        if not batch:
            continue
        try:
            await asyncio.to_thread(insert_batch, batch)
            logger.debug(f"Flushed {len(batch)} monitoring records.")
        except Exception as e:
            logger.error(f"Failed to insert monitoring batch: {e}")


def insert_batch(batch: list):
    if not batch:
        return
    conn = psycopg2.connect(DB_DSN)
    try:
        with conn.cursor() as cur:
            insert_sql = """
                INSERT INTO api_requests
                (user_id, api_key_id, endpoint, method, status_code,
                 response_time, client_ip, user_agent, timestamp)
                VALUES %s
            """
            values = [(
                item["user_id"], item["api_key_id"], item["endpoint"],
                item["method"], item["status_code"], item["response_time"],
                item["client_ip"], item["user_agent"], item["timestamp"]
            ) for item in batch]
            execute_values(cur, insert_sql, values)

            agg_sql = """
                INSERT INTO api_usage_hourly
                (user_id, api_key_id, endpoint, hour_bucket, request_count, total_latency, error_count)
                VALUES %s
                ON CONFLICT (user_id, api_key_id, endpoint, hour_bucket)
                DO UPDATE SET
                    request_count = api_usage_hourly.request_count + EXCLUDED.request_count,
                    total_latency = api_usage_hourly.total_latency + EXCLUDED.total_latency,
                    error_count = api_usage_hourly.error_count + EXCLUDED.error_count
            """
            agg_values = []
            for item in batch:
                hour_bucket = item["timestamp"].replace(minute=0, second=0, microsecond=0)
                agg_values.append((
                    item["user_id"],
                    item["api_key_id"],
                    item["endpoint"],
                    hour_bucket,
                    1,
                    item["response_time"],
                    1 if item["status_code"] >= 400 else 0
                ))
            execute_values(cur, agg_sql, agg_values)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ---------- System Health Collector (unchanged) ----------
def system_health_collector():
    import psutil
    conn = psycopg2.connect(DB_DSN)
    while not _stop_event.is_set():
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();")
                db_conns = cur.fetchone()[0]
            insert_sql = """
                INSERT INTO system_health
                (cpu_percent, memory_used_mb, memory_total_mb, db_connections, timestamp)
                VALUES (%s, %s, %s, %s, NOW())
            """
            with conn.cursor() as cur2:
                cur2.execute(insert_sql, (cpu, mem.used / (1024 * 1024), mem.total / (1024 * 1024), db_conns))
            conn.commit()
            logger.debug(f"System health: CPU={cpu}%, DB_conns={db_conns}")
        except Exception as e:
            logger.error(f"Health collector error: {e}")
        _stop_event.wait(60)
    conn.close()


def start_monitoring(app):
    """Start background workers."""
    global _worker_task, _health_collector_thread

    if not _worker_task:
        _worker_task = asyncio.create_task(monitoring_worker())
        logger.info("Monitoring worker started.")

    if not _health_collector_thread or not _health_collector_thread.is_alive():
        _stop_event.clear()
        _health_collector_thread = threading.Thread(target=system_health_collector, daemon=True)
        _health_collector_thread.start()
        logger.info("System health collector started.")


def stop_monitoring():
    global _worker_task
    if _worker_task:
        _worker_task.cancel()
        _worker_task = None
        logger.info("Monitoring worker stopped.")
    _stop_event.set()