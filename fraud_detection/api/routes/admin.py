from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from fraud_detection.database.postgres_db import get_connection, Database
from fraud_detection.api.dependencies import get_current_admin, get_services
from psycopg2.extras import RealDictCursor
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ---------- Pydantic models ----------
class UserApprove(BaseModel):
    user_id: int
    approve: bool

class RoleUpdate(BaseModel):
    role: str

class BlockRequest(BaseModel):
    reason: Optional[str] = None

# ---------- Router with /admin prefix ----------
router = APIRouter(prefix="/admin", tags=["admin"])

# ---------- Test route ----------
@router.get("/test")
async def test_route():
    logger.info("✅ Admin test route called")
    return {"message": "Admin router works!"}

# ---------- User approval endpoints (ADMIN ONLY) ----------
@router.get("/users/pending")
async def get_pending_users(current_user=Depends(get_current_admin)):
    logger.info("📊 get_pending_users called")
    db = Database()
    pending = db.get_pending_users()
    logger.info(f"   Found {len(pending)} pending users")
    return {"pending": pending}

@router.post("/users/approve")
async def approve_user(approval: UserApprove, current_user=Depends(get_current_admin)):
    try:
        logger.info(f"📊 approve_user called for user_id: {approval.user_id}")
        db = Database()
        user = db.get_user_by_id(approval.user_id)
        if not user:
            raise HTTPException(404, "User not found")
        
        # Check if user is already processed
        if user['status'] in ['active', 'rejected']:
            raise HTTPException(400, f"User already {user['status']}")
        
        new_status = "active" if approval.approve else "rejected"
        db.update_user_status(approval.user_id, new_status)
        
        # Log activity
        db.log_user_activity(
            current_user.get('sub', 'admin'), 
            "approve_user", 
            {"target": user['username'], "status": new_status}
        )
        
        logger.info(f"✅ User {user['username']} set to {new_status}")
        return {"message": f"User {user['username']} set to {new_status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving user: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to approve user: {str(e)}")

# ---------- User role update (ADMIN ONLY) ----------
@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: int, update: RoleUpdate, current_user=Depends(get_current_admin)):
    valid_roles = ["admin", "analyst", "viewer"]
    if update.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    logger.info(f"📊 update_user_role called for user_id: {user_id}, new role: {update.role}")
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE id = %s RETURNING id", (update.role, user_id))
            if not cur.fetchone():
                raise HTTPException(404, "User not found")
        conn.commit()
    
    # Log activity
    db.log_user_activity(
        current_user.get('sub', 'admin'),
        "change_role",
        {"target": user['username'], "new_role": update.role}
    )
    
    logger.info(f"✅ User {user['username']} role updated to {update.role}")
    return {"message": f"User {user_id} role updated to {update.role}"}

# ---------- Block user (ADMIN ONLY) ----------
@router.post("/users/{user_id}/block")
async def block_user(user_id: int, block_data: BlockRequest, current_user=Depends(get_current_admin)):
    logger.info(f"📊 block_user called for user_id: {user_id}")
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user['status'] == 'deleted':
        raise HTTPException(400, "Cannot block a deleted user")
    
    db.block_user(user_id, block_data.reason)
    db.log_user_activity(
        current_user.get('sub', 'admin'), 
        "block_user", 
        {"target": user['username'], "reason": block_data.reason}
    )
    logger.info(f"✅ User {user['username']} blocked")
    return {"message": f"User {user_id} has been blocked"}

# ---------- Unblock user (ADMIN ONLY) ----------
@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: int, current_user=Depends(get_current_admin)):
    logger.info(f"📊 unblock_user called for user_id: {user_id}")
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user['status'] != 'blocked':
        raise HTTPException(400, "User is not currently blocked")
    
    db.unblock_user(user_id)
    db.log_user_activity(
        current_user.get('sub', 'admin'), 
        "unblock_user", 
        {"target": user['username']}
    )
    logger.info(f"✅ User {user['username']} unblocked")
    return {"message": f"User {user_id} has been unblocked"}

# ---------- Delete user (ADMIN ONLY) - COMPLETE CASCADE DELETE ----------
@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user=Depends(get_current_admin)):
    """
    Permanently delete a user and all their associated data.
    - Deletes from users table
    - Deletes from login_logs table
    - Deletes from user_activity table
    - Deletes from refresh_tokens table
    - Cannot delete the last admin user
    """
    logger.info(f"📊 delete_user called for user_id: {user_id}")
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Check if user is already deleted
    if user['status'] == 'deleted':
        raise HTTPException(400, "User is already deleted")
    
    # Prevent deleting the last admin
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND status != 'deleted'")
            admin_count = cur.fetchone()[0]
            if admin_count <= 1 and user['role'] == 'admin':
                raise HTTPException(400, "Cannot delete the last admin user. Please create another admin first.")
    
    # Get username for logging and deletion
    username = user['username']
    admin_username = current_user.get('sub', 'admin')
    
    # Perform hard delete (remove all user data from all tables)
    deleted_counts = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Delete user activity logs
            cur.execute("DELETE FROM user_activity WHERE username = %s", (username,))
            deleted_counts['user_activity'] = cur.rowcount
            logger.info(f"Deleted {cur.rowcount} user_activity records for {username}")
            
            # Delete login logs
            cur.execute("DELETE FROM login_logs WHERE username = %s", (username,))
            deleted_counts['login_logs'] = cur.rowcount
            logger.info(f"Deleted {cur.rowcount} login_logs records for {username}")
            
            # Delete refresh tokens
            cur.execute("DELETE FROM refresh_tokens WHERE username = %s", (username,))
            deleted_counts['refresh_tokens'] = cur.rowcount
            logger.info(f"Deleted {cur.rowcount} refresh_tokens records for {username}")
            
            # Delete the user
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            deleted_counts['users'] = cur.rowcount
            logger.info(f"Deleted user {username} (ID: {user_id})")
        conn.commit()
    
    # Log the activity (by admin who deleted)
    db.log_user_activity(
        admin_username, 
        "delete_user", 
        {
            "deleted_user": username, 
            "user_id": user_id,
            "deleted_records": deleted_counts
        }
    )
    
    return {
        "message": f"User '{username}' has been permanently deleted",
        "deleted_user": username,
        "user_id": user_id,
        "deleted_records": deleted_counts
    }

# ---------- User activity (ADMIN ONLY) ----------
@router.get("/users/{user_id}/activity")
async def get_user_activity(user_id: int, current_user=Depends(get_current_admin)):
    logger.info(f"📊 get_user_activity called for user_id: {user_id}")
    db = Database()
    
    # Get user info
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Get recent failed logins count
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) FROM login_logs
                WHERE username = %s AND success = false
                AND timestamp > NOW() - INTERVAL '24 hours'
            """, (user['username'],))
            user['recent_failed_logins'] = cur.fetchone()['count']
    
    # Get activity logs using Database class
    activity = db.get_user_activity(user['username'], 50)
    
    # Get login logs using Database class
    login_logs = db.get_login_logs(50)
    # Filter for this specific user
    login_logs = [log for log in login_logs if log['username'] == user['username']]
    
    logger.info(f"   Found {len(activity)} activity logs and {len(login_logs)} login logs")
    
    return {
        "user": user,
        "activity": activity,
        "login_logs": login_logs,
    }

# ---------- Dashboard summary (ADMIN ONLY) ----------
@router.get("/dashboard/summary")
async def get_dashboard_summary(current_user=Depends(get_current_admin)):
    logger.info("📊 get_dashboard_summary called")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                logger.info(f"   total_users: {total_users}")
                
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
    except Exception as e:
        logger.error(f"Dashboard summary error: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get dashboard summary: {str(e)}")

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
async def get_login_logs(
    page: int = 1,
    page_size: int = 50,
    username: Optional[str] = None,
    current_user=Depends(get_current_admin)
):
    logger.info(f"📊 get_login_logs called, page: {page}, page_size: {page_size}")
    db = Database()
    logs = db.get_login_logs(page_size * page)
    
    # Filter by username if provided
    if username:
        logs = [log for log in logs if username.lower() in log['username'].lower()]
    
    total = len(logs)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    paginated_logs = logs[start:end]
    
    return {
        "logs": paginated_logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

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

# ---------- Single transaction override (ADMIN ONLY) ----------
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

# ---------- Bulk approve (ADMIN ONLY) ----------
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
async def get_all_users(
    page: int = 1,
    page_size: int = 15,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    current_user=Depends(get_current_admin)
):
    try:
        logger.info(f"📊 get_all_users called - page: {page}, search: {search}, role: {role}, status: {status}")
        db = Database()
        users = db.get_all_users()
        
        logger.info(f"   Found {len(users)} total users in database")
        
        # Apply filters
        if search:
            users = [u for u in users if search.lower() in u['username'].lower()]
            logger.info(f"   After search filter: {len(users)} users")
        if role:
            users = [u for u in users if u['role'] == role]
            logger.info(f"   After role filter: {len(users)} users")
        if status:
            users = [u for u in users if u['status'] == status]
            logger.info(f"   After status filter: {len(users)} users")
        
        total = len(users)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        paginated_users = users[start:end]
        
        logger.info(f"   Returning {len(paginated_users)} users (page {page} of {total_pages})")
        
        return {
            "users": paginated_users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error fetching users: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to fetch users: {str(e)}")

# ---------- Export router ----------
__all__ = ['router']
