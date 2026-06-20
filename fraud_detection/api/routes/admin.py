from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from fraud_detection.database.postgres_db import get_connection
from fraud_detection.api.dependencies import get_current_admin, get_services
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

class UserApprove(BaseModel):
    user_id: int
    approve: bool

# ---- Test route to confirm the router is mounted ----
@router.get("/test")
async def test_route():
    return {"message": "Admin router works! You can now access /admin/users/pending, etc."}

# ---- User approval endpoints ----
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

# ---- Login logs ----
@router.get("/login-logs")
async def get_login_logs(current_user=Depends(get_current_admin)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, success, ip, user_agent, timestamp FROM login_logs ORDER BY timestamp DESC LIMIT 200")
            rows = cur.fetchall()
    logs = [{"username": r[0], "success": r[1], "ip": r[2], "user_agent": r[3], "timestamp": r[4]} for r in rows]
    return logs

# ---- NEW: Override history (Audit Log) ----
@router.get("/overrides")
async def get_overrides(
    limit: int = 100,
    current_user=Depends(get_current_admin)
):
    """Fetch transaction override history for the Approval Audit Log."""
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

# ---- NEW: Override a transaction (and update its decision) ----
@router.post("/transactions/override")
async def override_transaction(
    request: Request,
    current_user=Depends(get_current_admin)
):
    """Override a transaction decision and update the transaction itself."""
    try:
        data = await request.json()
        transaction_id = data.get('transaction_id')
        new_decision = data.get('new_decision')
        reason = data.get('reason', '')
        username = current_user.get('sub') if isinstance(current_user, dict) else 'admin'  # fallback

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

        # Save override history
        storage.set_override(transaction_id, original_decision, new_decision, username, reason)

        # Update the transaction's decision and risk level
        risk_map = {
            'APPROVE': 'LOW',
            'BLOCK': 'HIGH',
            'REVIEW': 'MEDIUM'
        }
        new_risk = risk_map.get(new_decision, 'MEDIUM')
        storage.db.update_transaction_decision(transaction_id, new_decision, new_risk)

        return {"message": f"Transaction {transaction_id} overridden to {new_decision}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error overriding transaction: {e}", exc_info=True)
        raise HTTPException(500, "Failed to override transaction")
