from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, List
from fraud_detection.database.postgres_db import get_connection, Database
from fraud_detection.api.dependencies import get_current_admin, get_services
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

class UserApprove(BaseModel):
    user_id: int
    approve: bool

class RoleUpdate(BaseModel):
    role: str

class BlockRequest(BaseModel):
    reason: Optional[str] = None

# ---- Test route ----
@router.get("/test")
async def test_route():
    return {"message": "Admin router works!"}

# ---- User approval endpoints ----
@router.get("/users/pending")
async def get_pending_users(current_user=Depends(get_current_admin)):
    db = Database()
    pending = db.get_pending_users()
    return {"pending": pending}

@router.post("/users/approve")
async def approve_user(approval: UserApprove, current_user=Depends(get_current_admin)):
    db = Database()
    new_status = "active" if approval.approve else "rejected"
    db.update_user_status(approval.user_id, new_status)
    db.log_admin_action(
        username=current_user.get("sub", "admin"),
        action="user_approve",
        details={"user_id": approval.user_id, "approved": approval.approve}
    )
    return {"message": f"User {approval.user_id} set to {new_status}"}

# ---- Get all users (paginated) ----
@router.get("/users")
async def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    current_user=Depends(get_current_admin)
):
    db = Database()
    result = db.get_all_users_paginated(page, page_size, search, role, status)
    return result

# ---- Update user role ----
@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    req: RoleUpdate,
    current_user=Depends(get_current_admin)
):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    old_role = user["role"]
    db.update_user_role(user_id, req.role)
    db.log_admin_action(
        username=current_user.get("sub", "admin"),
        action="role_change",
        details={"user_id": user_id, "old_role": old_role, "new_role": req.role}
    )
    return {"message": f"User {user_id} role updated to {req.role}"}

# ---- Block user ----
@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int,
    req: BlockRequest,
    current_user=Depends(get_current_admin)
):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user["status"] == "blocked":
        raise HTTPException(400, "User is already blocked")
    db.update_user_status(user_id, "blocked", req.reason or "No reason provided")
    db.log_admin_action(
        username=current_user.get("sub", "admin"),
        action="user_block",
        details={"user_id": user_id, "reason": req.reason}
    )
    return {"message": f"User {user_id} blocked"}

# ---- Unblock user ----
@router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    current_user=Depends(get_current_admin)
):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user["status"] != "blocked":
        raise HTTPException(400, "User is not blocked")
    db.update_user_status(user_id, "active")
    db.log_admin_action(
        username=current_user.get("sub", "admin"),
        action="user_unblock",
        details={"user_id": user_id}
    )
    return {"message": f"User {user_id} unblocked"}

# ---- Delete user (soft-delete) ----
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_admin)
):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user["status"] == "deleted":
        raise HTTPException(400, "User is already deleted")
    db.delete_user(user_id)
    db.log_admin_action(
        username=current_user.get("sub", "admin"),
        action="user_delete",
        details={"user_id": user_id}
    )
    return {"message": f"User {user_id} deleted"}

# ---- Get user activity ----
@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: int,
    current_user=Depends(get_current_admin)
):
    db = Database()
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    activity = db.get_user_activity_logs(user_id)
    login_logs = db.get_user_login_logs(user["username"])
    return {"activity": activity, "login_logs": login_logs}

# ---- Security alerts ----
@router.get("/security/alerts")
async def get_security_alerts(
    current_user=Depends(get_current_admin)
):
    db = Database()
    alerts = db.get_security_alerts()
    return {"alerts": alerts}

# ---- Acknowledge alert ----
@router.post("/security/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    current_user=Depends(get_current_admin)
):
    # For simplicity, we just log the acknowledgement.
    db = Database()
    db.log_admin_action(
        username=current_user.get("sub", "admin"),
        action="alert_acknowledge",
        details={"alert_id": alert_id}
    )
    return {"message": "Alert acknowledged"}

# ---- Dashboard summary ----
@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user=Depends(get_current_admin)
):
    db = Database()
    summary = db.get_dashboard_summary()
    return summary

# ---- Login logs (paginated) ----
@router.get("/login-logs")
async def get_login_logs_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    username: Optional[str] = None,
    current_user=Depends(get_current_admin)
):
    db = Database()
    result = db.get_login_logs_paginated(page, page_size, username)
    return result

# ---- Legacy login logs (non-paginated) ----
@router.get("/login-logs-legacy")
async def get_login_logs_legacy(current_user=Depends(get_current_admin)):
    db = Database()
    logs = db.get_login_logs(200)
    return logs

# ---- Override history (existing) ----
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

# ---- Single transaction override (existing) ----
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

# ---- Bulk approve (existing) ----
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
