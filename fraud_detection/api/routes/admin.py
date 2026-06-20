from fastapi import APIRouter, Depends, HTTPException
from fraud_detection.database.postgres_db import get_connection
from fraud_detection.api.dependencies import get_current_admin
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])

class UserApprove(BaseModel):
    user_id: int
    approve: bool

# ---- Test route to confirm the router is mounted ----
@router.get("/test")
async def test_route():
    return {"message": "Admin router works! You can now access /admin/users/pending, etc."}

# ---- Main endpoints ----
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

@router.get("/login-logs")
async def get_login_logs(current_user=Depends(get_current_admin)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, success, ip, user_agent, timestamp FROM login_logs ORDER BY timestamp DESC LIMIT 200")
            rows = cur.fetchall()
    logs = [{"username": r[0], "success": r[1], "ip": r[2], "user_agent": r[3], "timestamp": r[4]} for r in rows]
    return logs