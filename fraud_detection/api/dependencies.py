from fraud_detection.api.routes.auth import verify_token
from fraud_detection.database.postgres_db import Database
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

def get_current_user(token: str = Depends(security)):
    """Get current user from token"""
    try:
        payload = verify_token(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(401, "Invalid token")
        
        db = Database()
        user = db.get_user_by_username(username)
        if not user:
            raise HTTPException(404, "User not found")
        
        return user
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")

def get_current_admin(user=Depends(get_current_user)):
    """Check if current user is admin"""
    if user.get('role') != 'admin':
        raise HTTPException(403, "Admin access required")
    return user

def get_services():
    """Get services - implement based on your app"""
    # This should return your services instance
    # For now, return a placeholder
    class Services:
        pass
    return Services()
