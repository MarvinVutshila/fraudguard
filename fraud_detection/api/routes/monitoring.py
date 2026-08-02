from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta
from fraud_detection.api.dependencies import get_current_user
from fraud_detection.database.postgres_db import get_connection
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/stats")
async def get_monitoring_stats(user=Depends(get_current_user)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(request_count), 0)
                FROM api_usage_hourly
                WHERE hour_bucket >= %s
            """, (today,))
            total_requests = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COALESCE(SUM(error_count), 0)
                FROM api_usage_hourly
                WHERE hour_bucket >= %s
            """, (today,))
            total_errors = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COALESCE(AVG(avg_latency), 0)
                FROM api_usage_hourly
                WHERE hour_bucket >= %s
            """, (today,))
            avg_latency = cur.fetchone()[0]
            
            cur.execute("""
                SELECT endpoint, SUM(request_count) as total
                FROM api_usage_hourly
                WHERE hour_bucket >= %s
                GROUP BY endpoint
                ORDER BY total DESC
                LIMIT 5
            """, (yesterday,))
            top_endpoints = [{"endpoint": r[0], "count": r[1]} for r in cur.fetchall()]
            
            cur.execute("""
                SELECT u.username, SUM(h.request_count)
                FROM api_usage_hourly h
                LEFT JOIN users u ON h.user_id = u.id
                WHERE h.hour_bucket >= %s
                GROUP BY u.username
                ORDER BY 2 DESC
                LIMIT 10
            """, (yesterday,))
            users = [{"username": r[0] or "Unknown", "count": r[1]} for r in cur.fetchall()]
            
            cur.execute("""
                SELECT cpu_percent, memory_used_mb, memory_total_mb, db_connections
                FROM system_health
                ORDER BY timestamp DESC LIMIT 1
            """)
            health = cur.fetchone()
            system_health = {
                "cpu_percent": health[0] if health else 0,
                "memory_used_mb": health[1] if health else 0,
                "memory_total_mb": health[2] if health else 0,
                "db_connections": health[3] if health else 0
            }
            
    return {
        "total_requests_today": total_requests,
        "error_rate": round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
        "avg_latency": round(avg_latency, 2),
        "top_endpoints": top_endpoints,
        "users": users,
        "system_health": system_health
    }


# NEW: renamed endpoint to avoid any routing cache issues
@router.get("/request-logs")
async def get_request_logs(
    user_id: Optional[int] = Query(None),
    endpoint: Optional[str] = Query(None),
    status_code: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user)
):
    """
    Return paginated API logs with optional filters.
    Empty strings are ignored.
    This endpoint replaces /logs to avoid caching issues.
    """
    logger.info(f"📥 /request-logs called with: user_id={user_id}, endpoint={endpoint}, status_code={status_code}, "
                f"date_from={date_from}, date_to={date_to}, limit={limit}, offset={offset}")

    # Convert empty strings to None
    if endpoint == "":
        endpoint = None
    if status_code == "":
        status_code = None
    if date_from == "":
        date_from = None
    if date_to == "":
        date_to = None

    sql = """
        SELECT 
            r.id, r.user_id, u.username, r.endpoint, r.method,
            r.status_code, r.response_time, r.client_ip, r.timestamp
        FROM api_requests r
        LEFT JOIN users u ON r.user_id = u.id
        WHERE 1=1
    """
    count_sql = "SELECT COUNT(*) FROM api_requests r WHERE 1=1"
    params = []
    count_params = []

    if user_id is not None:
        sql += " AND r.user_id = %s"
        count_sql += " AND r.user_id = %s"
        params.append(user_id)
        count_params.append(user_id)

    if endpoint is not None:
        sql += " AND r.endpoint = %s"
        count_sql += " AND r.endpoint = %s"
        params.append(endpoint)
        count_params.append(endpoint)

    if status_code is not None:
        try:
            status_int = int(status_code)
            sql += " AND r.status_code = %s"
            count_sql += " AND r.status_code = %s"
            params.append(status_int)
            count_params.append(status_int)
        except ValueError:
            pass

    if date_from is not None:
        try:
            dt_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            sql += " AND r.timestamp >= %s"
            count_sql += " AND r.timestamp >= %s"
            params.append(dt_from)
            count_params.append(dt_from)
        except ValueError:
            pass

    if date_to is not None:
        try:
            dt_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            sql += " AND r.timestamp <= %s"
            count_sql += " AND r.timestamp <= %s"
            params.append(dt_to)
            count_params.append(dt_to)
        except ValueError:
            pass

    sql += " ORDER BY r.timestamp DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(count_sql, count_params)
            total = cur.fetchone()[0]

            cur.execute(sql, params)
            rows = cur.fetchall()
            logs = [{
                "id": r[0],
                "user_id": r[1],
                "username": r[2],
                "endpoint": r[3],
                "method": r[4],
                "status_code": r[5],
                "response_time": r[6],
                "client_ip": r[7],
                "timestamp": r[8].isoformat()
            } for r in rows]

    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/cleanup")
async def cleanup_old_records(user=Depends(get_current_user)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cut_off_requests = datetime.utcnow() - timedelta(days=7)
            cur.execute("DELETE FROM api_requests WHERE timestamp < %s", (cut_off_requests,))
            deleted_req = cur.rowcount
            
            cut_off_hourly = datetime.utcnow() - timedelta(days=180)
            cur.execute("DELETE FROM api_usage_hourly WHERE hour_bucket < %s", (cut_off_hourly,))
            deleted_hourly = cur.rowcount
            
            cut_off_health = datetime.utcnow() - timedelta(days=30)
            cur.execute("DELETE FROM system_health WHERE timestamp < %s", (cut_off_health,))
            deleted_health = cur.rowcount
        conn.commit()
    return {
        "deleted_api_requests": deleted_req,
        "deleted_hourly_aggregates": deleted_hourly,
        "deleted_system_health": deleted_health
    }