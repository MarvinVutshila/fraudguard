from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from fraud_detection.api.dependencies import get_current_user, get_current_admin
from fraud_detection.database.postgres_db import Database, get_connection
from fraud_detection.api.routes.auth import hash_password, verify_password, verify_token
from fraud_detection.api.routes.auth import setup_2fa as auth_setup_2fa
from fraud_detection.api.routes.auth import verify_2fa_setup as auth_verify_2fa_setup
from fraud_detection.api.routes.auth import disable_2fa as auth_disable_2fa
from .auth_models import TwoFactorSetupRequest, TwoFactorDisableRequest
from psycopg2.extras import RealDictCursor
import secrets
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

# ---------- Models ----------
class UserPreferences(BaseModel):
    theme: Optional[str] = "dark"
    notifications: Optional[Dict[str, bool]] = {}
    language: Optional[str] = "en"

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: int = 365

class SystemSettingsUpdate(BaseModel):
    approve_threshold: Optional[float] = None
    block_threshold: Optional[float] = None
    auto_retrain_enabled: Optional[bool] = None
    auto_retrain_schedule: Optional[str] = None
    alert_email: Optional[str] = None
    monitoring_interval: Optional[int] = None
    agent_config: Optional[Dict[str, Any]] = None   # <-- added for agent config

# ---------- Helpers ----------
def generate_api_key():
    return "fg_" + secrets.token_urlsafe(32)

# ---------- Endpoints ----------

@router.get("/")
async def get_settings(user=Depends(get_current_user)):
    db = Database()
    db_user = db.get_user_by_username(user["username"])
    if not db_user:
        raise HTTPException(404, "User not found")
    
    prefs = db_user.get("preferences") or {}
    
    system = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM system_settings")
            rows = cur.fetchall()
            for key, val in rows:
                system[key] = val
    
    return {
        "user": {
            "username": db_user["username"],
            "role": db_user["role"],
            "email": db_user["username"],
            "preferences": prefs,
            "2fa_enabled": db_user.get("totp_enabled", False),
        },
        "system": system
    }

@router.put("/preferences")
async def update_preferences(prefs: UserPreferences, user=Depends(get_current_user)):
    db = Database()
    db_user = db.get_user_by_username(user["username"])
    if not db_user:
        raise HTTPException(404, "User not found")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET preferences = %s WHERE id = %s",
                (json.dumps(prefs.dict()), db_user["id"])
            )
        conn.commit()
    
    return {"message": "Preferences updated"}

@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    db = Database()
    db_user = db.get_user_by_username(user["username"])
    if not db_user:
        raise HTTPException(404, "User not found")
    
    if not verify_password(req.current_password, db_user["password"]):
        raise HTTPException(400, "Current password is incorrect")
    
    new_hashed = hash_password(req.new_password)
    db.update_user_password(db_user["id"], new_hashed)
    
    return {"message": "Password changed successfully"}

# ---------- API Keys ----------
@router.get("/api-keys")
async def get_api_keys(user=Depends(get_current_user)):
    db = Database()
    db_user = db.get_user_by_username(user["username"])
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, prefix, last_used, expires_at, revoked, created_at "
                "FROM api_keys WHERE user_id = %s ORDER BY created_at DESC",
                (db_user["id"],)
            )
            rows = cur.fetchall()
    return [dict(row) for row in rows]

@router.post("/api-keys")
async def create_api_key(req: ApiKeyCreate, user=Depends(get_current_user)):
    db = Database()
    db_user = db.get_user_by_username(user["username"])
    
    key = generate_api_key()
    prefix = key[:6]
    expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO api_keys (user_id, name, key, prefix, expires_at) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (db_user["id"], req.name, key, prefix, expires_at)
            )
            key_id = cur.fetchone()[0]
        conn.commit()
    
    return {"id": key_id, "key": key, "prefix": prefix, "expires_at": expires_at}

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: int, user=Depends(get_current_user)):
    db = Database()
    db_user = db.get_user_by_username(user["username"])
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE api_keys SET revoked = TRUE WHERE id = %s AND user_id = %s",
                (key_id, db_user["id"])
            )
            if cur.rowcount == 0:
                raise HTTPException(404, "API key not found")
        conn.commit()
    return {"message": "API key revoked"}

# ---------- System Settings (admin only) ----------
@router.put("/system")
async def update_system_settings(settings: SystemSettingsUpdate, admin=Depends(get_current_admin)):
    admin_user = admin.get("username", "admin")
    updates = settings.dict(exclude_unset=True)
    with get_connection() as conn:
        with conn.cursor() as cur:
            for key, value in updates.items():
                # If value is a dict, we store as JSONB already
                cur.execute(
                    "INSERT INTO system_settings (key, value, updated_at, updated_by) "
                    "VALUES (%s, %s, NOW(), %s) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW(), updated_by = EXCLUDED.updated_by",
                    (key, json.dumps(value), admin_user)
                )
        conn.commit()
    
    return {"message": "System settings updated"}

# ============================================================
# 2FA endpoints – correctly use verify_token and auth functions
# ============================================================

@router.post("/2fa/setup")
async def setup_2fa(payload: dict = Depends(verify_token)):
    """Proxy to auth.setup_2fa with the token payload."""
    return await auth_setup_2fa(payload)

@router.post("/2fa/verify-setup")
async def verify_2fa_setup(request: Request, payload: dict = Depends(verify_token)):
    """Proxy to auth.verify_2fa_setup with the token payload and request body."""
    try:
        body = await request.json()
        code = body.get("code")
        if not code:
            raise HTTPException(400, "Code is required")
        req = TwoFactorSetupRequest(code=code)
        return await auth_verify_2fa_setup(req, payload)
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/2fa/disable")
async def disable_2fa(request: Request, payload: dict = Depends(verify_token)):
    """Proxy to auth.disable_2fa with the token payload and request body."""
    try:
        body = await request.json()
        code = body.get("code")
        if not code:
            raise HTTPException(400, "Code is required")
        req = TwoFactorDisableRequest(code=code)
        return await auth_disable_2fa(req, payload)
    except Exception as e:
        raise HTTPException(400, str(e))

# ---------- Export ----------
__all__ = ['router']