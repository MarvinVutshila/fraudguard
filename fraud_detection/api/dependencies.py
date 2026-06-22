from fastapi import HTTPException, Depends
from fraud_detection.api.auth import verify_token
from fraud_detection.database.postgres_db import Database
from typing import Optional

_services = None

def set_services(services):
    global _services
    _services = services

def get_services():
    if _services is None:
        raise HTTPException(status_code=503, detail="Services not initialised")
    return _services

class UserContext:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role

def get_current_user(payload: dict = Depends(verify_token)) -> UserContext:
    username = payload.get("sub")
    role = payload.get("role", "analyst")
    if not username:
        raise HTTPException(401, "Invalid token")
    
    # Optional: update last_active for this user (safe way)
    try:
        db = Database()
        db.update_last_active(username)   # username is a string ✅
    except Exception:
        # Log error but don't break the request
        pass
    
    return UserContext(username, role)

def get_current_admin(current_user: UserContext = Depends(get_current_user)) -> UserContext:
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return current_user
