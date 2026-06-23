from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from fraud_detection.database.postgres_db import get_connection, Database
from fraud_detection.api.dependencies import get_current_admin, get_services
from psycopg2.extras import RealDictCursor
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------- Pydantic models ----------
class UserApprove(BaseModel):
    user_id: int
    approve: bool

class RoleUpdate(BaseModel):
    role: str

class BlockRequest(BaseModel):
    reason: Optional[str] = None

# ---------- Test route ----------
@router.get("/test")
async def test_route():
    return {"message": "Admin router works!"}

# ---------- User approval endpoints (ADMIN ONLY) ----------
@router.get("/users/pending")
async def get_pending_users(current_user=Depends(get_current_admin)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, avatar_url, created_at FROM users WHERE status = 'pending'")
            rows = cur.fetchall()
    return {"pending": [{"id": r[0], "username": r[1], "avatar_url": r[2], "created_at": r[3]} for r in rows]}

@router.post("/users/approve")
async def approve_user(approval: UserApprove, current_user=Depends(get_current_admin)):
    new_status = "active" if approval.approve else "rejected"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, approval.user_id))
        conn.commit()
    return {"message": f"User {approval.user_id} set to {new_status}"}

# ---------- User role update (ADMIN ONLY) ----------
@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: int, update: RoleUpdate, current_user=Depends(get_current_admin)):
    valid_roles = ["admin", "analyst", "viewer"]
    if update.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE id = %s RETURNING id", (update.role, user_id))
            if not cur.fetchone():
                raise HTTPException(404, "User not found")
        conn.commit()
    
    return {"message": f"User {user_id} role updated to {update.role}"}

# ---------- Block user (ADMIN ONLY) ----------
@router.post("/users/{user_id}/block")
async def block_user(user_id: int, block_data: BlockRequest, current_user=Depends(get_current_admin)):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user['status'] == 'deleted':
        raise HTTPException(400, "Cannot block a deleted user")
    db.block_user(user_id, block_data.reason)
    db.log_user_activity(current_user.username, "block_user", {"target": user['username'], "reason": block_data.reason})
    return {"message": f"User {user_id} has been blocked"}

# ---------- Unblock user (ADMIN ONLY) ----------
@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: int, current_user=Depends(get_current_admin)):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user['status'] != 'blocked':
        raise HTTPException(400, "User is not currently blocked")
    db.unblock_user(user_id)
    db.log_user_activity(current_user.username, "unblock_user", {"target": user['username']})
    return {"message": f"User {user_id} has been unblocked"}

# ---------- Delete user (ADMIN ONLY) ----------
@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user=Depends(get_current_admin)):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user['status'] == 'deleted':
        raise HTTPException(400, "User already deleted")
    db.delete_user(user_id)
    db.log_user_activity(current_user.username, "delete_user", {"target": user['username']})
    return {"message": f"User {user_id} has been deleted"}

# ---------- User activity (ADMIN ONLY) ----------
@router.get("/users/{user_id}/activity")
async def get_user_activity(user_id: int, current_user=Depends(get_current_admin)):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, username, role, status, avatar_url, last_active, created_at,
                       blocked_reason, blocked_at
                FROM users WHERE id = %s
            """, (user_id,))
            user = cur.fetchone()
            if not user:
                raise HTTPException(404, "User not found")
            
            cur.execute("""
                SELECT COUNT(*) FROM login_logs
                WHERE username = %s AND success = false
                AND timestamp > NOW() - INTERVAL '24 hours'
            """, (user['username'],))
            user['recent_failed_logins'] = cur.fetchone()[0]
            
            cur.execute("""
                SELECT action, details, timestamp
                FROM user_activity
                WHERE username = %s
                ORDER BY timestamp DESC
                LIMIT 50
            """, (user['username'],))
            activity = cur.fetchall()
            
            cur.execute("""
                SELECT success, ip, user_agent, timestamp
                FROM login_logs
                WHERE username = %s
                ORDER BY timestamp DESC
                LIMIT 50
            """, (user['username'],))
            login_logs = cur.fetchall()
    
    return {
        "user": dict(user),
        "activity": [dict(row) for row in activity],
        "login_logs": [dict(row) for row in login_logs],
    }

# ---------- Dashboard summary (ADMIN ONLY) ----------
@router.get("/dashboard/summary")
async def get_dashboard_summary(current_user=Depends(get_current_admin)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
            active_users = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            pending_approvals = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE status = 'blocked'")
            blocked_users = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(DISTINCT username) FROM login_logs 
                WHERE success = false 
                AND timestamp > NOW() - INTERVAL '1 hour'
                GROUP BY username
                HAVING COUNT(*) > 5
            """)
            high_risk_rows = cur.fetchall()
            high_risk_users = len(high_risk_rows) if high_risk_rows else 0
            
            cur.execute("""
                SELECT COUNT(*) FROM login_logs 
                WHERE success = false 
                AND timestamp > NOW() - INTERVAL '24 hours'
            """)
            failed_logins_24h = cur.fetchone()[0]
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "pending_approvals": pending_approvals,
        "blocked_users": blocked_users,
        "high_risk_users": high_risk_users,
        "failed_logins_24h": failed_logins_24h,
    }

# ---------- Security alerts (ADMIN ONLY) ----------
@router.get("/security/alerts")
async def get_security_alerts(current_user=Depends(get_current_admin)):
    alerts = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, COUNT(*) as attempts, MAX(timestamp) as last_attempt
                FROM login_logs
                WHERE success = false
                AND timestamp > NOW() - INTERVAL '15 minutes'
                GROUP BY username
                HAVING COUNT(*) > 5
                ORDER BY last_attempt DESC
            """)
            brute_force = cur.fetchall()
            for row in brute_force:
                alerts.append({
                    "id": f"bf-{row[0]}",
                    "type": "brute_force",
                    "severity": "high",
                    "username": row[0],
                    "message": f"{row[1]} failed login attempts in 15 minutes",
                    "timestamp": row[2].isoformat() if row[2] else None,
                })
    return {"alerts": alerts}

# ---------- Login logs (ADMIN ONLY) ----------
@router.get("/login-logs")
async def get_login_logs(current_user=Depends(get_current_admin)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, success, ip, user_agent, timestamp FROM login_logs ORDER BY timestamp DESC LIMIT 200")
            rows = cur.fetchall()
    logs = [{"username": r[0], "success": r[1], "ip": r[2], "user_agent": r[3], "timestamp": r[4]} for r in rows]
    return logs

# ---------- Override history (ADMIN ONLY - for audit purposes) ----------
@router.get("/overrides")
async def get_overrides(limit: int = 100, current_user=Depends(get_current_admin)):
    try:
        services = get_services()
        db = services.storage_service.db if services.storage_service else None
        if not db:
            raise HTTPException(503, "Database service unavailable")
        overrides = db.get_all_overrides(limit)
        return {"overrides": overrides}
    except Exception as e:
        logger.error(f"Error fetching overrides: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch override history")

# ---------- Single transaction override (ADMIN ONLY - keep this restricted!) ----------
@router.post("/transactions/override")
async def override_transaction(request: Request, current_user=Depends(get_current_admin)):
    try:
        data = await request.json()
        transaction_id = data.get('transaction_id')
        new_decision = data.get('new_decision')
        reason = data.get('reason', '')
        username = current_user.get('sub') if isinstance(current_user, dict) else 'admin'

        if not transaction_id or not new_decision:
            raise HTTPException(400, "transaction_id and new_decision are required")

        services = get_services()
        storage = services.storage_service
        if not storage:
            raise HTTPException(503, "Storage service unavailable")

        tx = storage.get_transaction(transaction_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")

        original_decision = tx.get('decision')
        storage.set_override(transaction_id, original_decision, new_decision, username, reason)

        risk_map = {'APPROVE': 'LOW', 'BLOCK': 'HIGH', 'REVIEW': 'MEDIUM'}
        new_risk = risk_map.get(new_decision, 'MEDIUM')
        storage.update_transaction_decision(transaction_id, new_decision, new_risk)

        return {"message": f"Transaction {transaction_id} overridden to {new_decision}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error overriding transaction: {e}", exc_info=True)
        raise HTTPException(500, "Failed to override transaction")

# ---------- Bulk approve (ADMIN ONLY - keep this restricted!) ----------
@router.post("/transactions/bulk-approve")
async def bulk_approve(current_user=Depends(get_current_admin)):
    try:
        services = get_services()
        storage = services.storage_service
        db = services.storage_service.db
        reviews = storage.get_transactions(limit=1000, decision='REVIEW')
        count = 0
        username = current_user.get('sub') if isinstance(current_user, dict) else 'admin'
        for tx in reviews:
            tx_id = tx['transaction_id']
            storage.set_override(tx_id, tx['decision'], 'APPROVE', username, 'Bulk approval')
            db.update_transaction_decision(tx_id, 'APPROVE', 'LOW')
            count += 1
        return {"message": f"Approved {count} transactions"}
    except Exception as e:
        logger.error(f"Bulk approve failed: {e}", exc_info=True)
        raise HTTPException(500, "Bulk approve failed")

# ---------- Get all users (ADMIN ONLY) ----------
@router.get("/users")
async def get_all_users(current_user=Depends(get_current_admin)):
    try:
        db = Database()
        users = db.get_all_users()
        return {"users": users}
    except Exception as e:
        logger.error(f"Error fetching users: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch users")
