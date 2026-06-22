from fastapi import HTTPException, Depends
from fraud_detection.api.auth import verify_token
from fraud_detection.database.postgres_db import Database

_services = None

def set_services(services):
    global _services
    _services = services

def get_services():
    if _services is None:
        raise HTTPException(status_code=503, detail="Services not initialised")
    return _services

class UserContext:
    def __init__(self, username: str, role: str, status: str = "active"):
        self.username = username
        self.role = role
        self.status = status

def get_current_user(payload: dict = Depends(verify_token)) -> UserContext:
    username = payload.get("sub")
    role = payload.get("role", "analyst")
    if not username:
        raise HTTPException(401, "Invalid token")
    
    # Fetch user from DB to check status
    db = Database()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(401, "User not found")
    
    # If user is blocked, rejected, or deleted, deny access
    if user['status'] not in ['active', 'pending']:  # pending can be allowed to access? typically pending shouldn't login, but they can't login anyway
        # For active session, if status is blocked/rejected/deleted, reject
        raise HTTPException(403, detail=f"Account is {user['status']}. Access denied.")
    
    # Optional: update last_active? Already done on login, maybe not needed.
    return UserContext(username, role, user['status'])

def get_current_admin(current_user: UserContext = Depends(get_current_user)) -> UserContext:
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return current_user
