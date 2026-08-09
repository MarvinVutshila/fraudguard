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
            # Total requests today
            cur.execute("SELECT COALESCE(SUM(request_count), 0) FROM api_usage_hourly WHERE hour_bucket >= %s", (today,))
            total_requests = cur.fetchone()[0]

            # Error breakdown: 4xx vs 5xx (we need a separate table or derive from api_requests)
            # If we have api_requests table, we can query it directly
            cur.execute("""
                SELECT status_code, COUNT(*) 
                FROM api_requests 
                WHERE timestamp >= %s AND (status_code >= 400 AND status_code < 600)
                GROUP BY status_code
            """, (today,))
            error_rows = cur.fetchall()
            auth_errors = sum(cnt for code, cnt in error_rows if 400 <= code < 500)
            server_errors = sum(cnt for code, cnt in error_rows if 500 <= code < 600)

            # Average latency
            cur.execute("SELECT COALESCE(AVG(response_time), 0) FROM api_requests WHERE timestamp >= %s", (today,))
            avg_latency = cur.fetchone()[0]

            # Top endpoints
            cur.execute("""
                SELECT endpoint, COUNT(*) as total
                FROM api_requests
                WHERE timestamp >= %s
                GROUP BY endpoint
                ORDER BY total DESC
                LIMIT 5
            """, (yesterday,))
            top_endpoints = [{"endpoint": r[0], "count": r[1]} for r in cur.fetchall()]

            # User activity
            cur.execute("""
                SELECT u.username, COUNT(r.id)
                FROM api_requests r
                LEFT JOIN users u ON r.user_id = u.id
                WHERE r.timestamp >= %s
                GROUP BY u.username
                ORDER BY 2 DESC
                LIMIT 10
            """, (yesterday,))
            users = [{"username": r[0] or "Unknown", "count": r[1]} for r in cur.fetchall()]

            # System health
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

    error_rate = round((auth_errors + server_errors) / total_requests * 100, 2) if total_requests > 0 else 0
    overall_status = "healthy" if server_errors == 0 and auth_errors < 5 else "degraded"

    return {
        "total_requests_today": total_requests,
        "error_rate": error_rate,
        "auth_errors": auth_errors,
        "server_errors": server_errors,
        "avg_latency": round(avg_latency, 2),
        "top_endpoints": top_endpoints,
        "users": users,
        "system_health": system_health,
        "status": overall_status
    }


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
    sql = """
        SELECT r.id, r.user_id, u.username, r.endpoint, r.method,
               r.status_code, r.response_time, r.client_ip, r.timestamp
        FROM api_requests r
        LEFT JOIN users u ON r.user_id = u.id
        WHERE 1=1
    """
    count_sql = "SELECT COUNT(*) FROM api_requests r WHERE 1=1"
    params, count_params = [], []

    if user_id is not None:
        sql += " AND r.user_id = %s"
        count_sql += " AND r.user_id = %s"
        params.append(user_id); count_params.append(user_id)

    if endpoint:
        sql += " AND r.endpoint = %s"
        count_sql += " AND r.endpoint = %s"
        params.append(endpoint); count_params.append(endpoint)

    if status_code:
        try:
            st = int(status_code)
            sql += " AND r.status_code = %s"
            count_sql += " AND r.status_code = %s"
            params.append(st); count_params.append(st)
        except ValueError:
            pass

    if date_from:
        try:
            dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            sql += " AND r.timestamp >= %s"
            count_sql += " AND r.timestamp >= %s"
            params.append(dt); count_params.append(dt)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            sql += " AND r.timestamp <= %s"
            count_sql += " AND r.timestamp <= %s"
            params.append(dt); count_params.append(dt)
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

    return {"logs": logs, "total": total, "limit": limit, "offset": offset}


@router.post("/cleanup")
async def cleanup_old_records(user=Depends(get_current_user)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cut_off = datetime.utcnow() - timedelta(days=7)
            cur.execute("DELETE FROM api_requests WHERE timestamp < %s", (cut_off,))
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