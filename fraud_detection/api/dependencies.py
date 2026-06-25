from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import os
from typing import Optional, Dict, Any
from datetime import datetime

# Import from the correct location
from fraud_detection.api.routes.auth import verify_token
from fraud_detection.database.postgres_db import Database

security = HTTPBearer()

# Global services object (set by main.py)
_services = None

# Support contact information
SUPPORT_EMAIL = "marvin@support.co.za"

def set_services(services):
    """Set the global services instance (called from main.py startup)"""
    global _services
    _services = services

def get_services():
    """Get the global services instance"""
    if _services is None:
        raise HTTPException(status_code=503, detail="Services not initialized")
    return _services

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token and check if they are still active"""
    try:
        token = credentials.credentials
        payload = verify_token(credentials)
        
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: no username")
        
        # Get token issued at time
        token_iat = payload.get("iat")
        if token_iat:
            token_issued_at = datetime.fromtimestamp(token_iat)
        else:
            token_issued_at = None
        
        db = Database()
        user = db.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 🔒 Check if user is blocked - IMMEDIATELY REJECT
        if user.get('status') == 'blocked':
            blocked_at = user.get('blocked_at')
            
            # If token was issued BEFORE the user was blocked, reject immediately
            if blocked_at and token_issued_at:
                if isinstance(blocked_at, str):
                    blocked_at = datetime.fromisoformat(blocked_at.replace('Z', '+00:00'))
                
                if token_issued_at < blocked_at:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Your account has been blocked.\n\nIf you believe this is an error, please contact your system administrator at {SUPPORT_EMAIL}."
                    )
            
            raise HTTPException(
                status_code=403, 
                detail=f"Your account has been blocked.\n\nIf you believe this is an error, please contact your system administrator at {SUPPORT_EMAIL}."
            )
        
        # Check if user is deleted
        if user.get('status') == 'deleted':
            raise HTTPException(
                status_code=403, 
                detail="Your account has been deleted.\n\nIf you believe this is an error, please contact your system administrator."
            )
        
        # Check if user is pending or rejected
        if user.get('status') in ['pending', 'rejected']:
            raise HTTPException(
                status_code=403, 
                detail=f"Your account is {user.get('status')}.\n\nIf you believe this is an error, please contact your system administrator."
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def get_current_admin(user: dict = Depends(get_current_user)):
    """Check if current user is admin"""
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def get_current_analyst(user: dict = Depends(get_current_user)):
    """Check if current user is analyst or admin"""
    if user.get('role') not in ['admin', 'analyst']:
        raise HTTPException(status_code=403, detail="Analyst or admin access required")
    return user

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        payload = verify_token(credentials)
        username = payload.get("sub")
        if not username:
            return None
        
        db = Database()
        user = db.get_user_by_username(username)
        if not user or user.get('status') in ['blocked', 'deleted']:
            return None
        
        return user
    except:
        return None

# For backward compatibility
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Alias for get_optional_user"""
    return get_optional_user(credentials)

# For backward compatibility with admin.py
def get_current_admin_user(user: dict = Depends(get_current_admin)):
    """Alias for get_current_admin"""
    return user

# Export everything
__all__ = [
    'set_services',
    'get_services',
    'get_current_user',
    'get_current_admin',
    'get_current_analyst',
    'get_optional_user',
    'get_current_user_optional',
    'get_current_admin_user',
    'security',
    'SUPPORT_EMAIL'
]
