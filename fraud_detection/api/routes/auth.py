import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from fraud_detection.database.postgres_db import get_connection, Database
from .auth_models import (
    LoginRequest, UserRegister,
    TwoFactorSetupRequest, TwoFactorVerifyRequest, TwoFactorDisableRequest
)
import pyotp
import qrcode
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

# ---------- Configuration ----------
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", SECRET_KEY)
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

security = HTTPBearer()
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# In-memory rate limiting
login_attempts: Dict[str, list] = {}

# ---------- Helper Functions ----------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")

def check_rate_limit(username: str, ip: str) -> tuple[bool, Optional[int]]:
    key = f"{username}:{ip}"
    now = datetime.utcnow().timestamp()
    window_start = now - (LOCKOUT_MINUTES * 60)
    
    if key in login_attempts:
        login_attempts[key] = [t for t in login_attempts[key] if t > window_start]
        
        if len(login_attempts[key]) >= MAX_LOGIN_ATTEMPTS:
            oldest_attempt = min(login_attempts[key])
            remaining = int(LOCKOUT_MINUTES * 60 - (now - oldest_attempt))
            return False, max(0, remaining)
    
    return True, None

def record_login_attempt(username: str, ip: str, success: bool) -> None:
    if not success:
        key = f"{username}:{ip}"
        if key not in login_attempts:
            login_attempts[key] = []
        login_attempts[key].append(datetime.utcnow().timestamp())

# ---------- Router ----------
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(creds: LoginRequest, request: Request):
    """Authenticate a user with rate limiting and 2FA support."""
    user_agent = request.headers.get("user-agent", "unknown")
    client_ip = request.client.host if request.client else "0.0.0.0"
    
    allowed, remaining = check_rate_limit(creds.username, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please wait {remaining} seconds."
        )
    
    success = False
    user = None
    role = "analyst"
    status = None
    totp_enabled = False

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, password, role, status, totp_enabled FROM users WHERE username = %s",
                (creds.username,)
            )
            row = cur.fetchone()
            if row:
                user = row[0]
                hashed = row[1]
                role = row[2]
                status = row[3]
                totp_enabled = row[4] if len(row) > 4 else False
                if status == "active" and verify_password(creds.password, hashed):
                    success = True

    record_login_attempt(creds.username, client_ip, success)

    if not success:
        db = Database()
        db.log_login_attempt(creds.username, False, client_ip, user_agent)
        
        if status == "pending":
            raise HTTPException(403, detail="Account pending admin approval.")
        elif status == "rejected":
            raise HTTPException(403, detail="Account rejected by admin.")
        elif status == "blocked":
            raise HTTPException(403, detail="Account blocked.")
        else:
            raise HTTPException(401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user, "role": role})
    refresh_token = create_refresh_token({"sub": user, "role": role})
    
    db = Database()
    db.log_login_attempt(creds.username, True, client_ip, user_agent)
    db.log_user_activity(user, "login", {"ip": client_ip, "user_agent": user_agent})
    db.update_last_active(creds.username)
    db.store_refresh_token(user, refresh_token, 
                          datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    response_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": role
    }
    
    if totp_enabled:
        response_data["requires_2fa"] = True
    
    return response_data

@router.post("/refresh")
async def refresh_token(request: Request):
    """Get a new access token using a refresh token."""
    try:
        data = await request.json()
        refresh_token = data.get('refresh_token')
    except:
        raise HTTPException(400, "Invalid request body")
    
    if not refresh_token:
        raise HTTPException(400, "Refresh token required")
    
    try:
        payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
    except JWTError as e:
        raise HTTPException(401, f"Invalid refresh token: {str(e)}")
    
    username = payload.get("sub")
    role = payload.get("role", "analyst")
    
    db = Database()
    stored_token = db.get_refresh_token(username, refresh_token)
    if not stored_token:
        raise HTTPException(401, "Invalid or revoked refresh token")
    
    new_access_token = create_access_token({"sub": username, "role": role})
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/register")
async def register(user: UserRegister, request: Request):
    """Register a new user."""
    client_ip = request.client.host if request.client else "0.0.0.0"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE username = %s", (user.username,))
            if cur.fetchone():
                raise HTTPException(409, "Username already exists")

            hashed = hash_password(user.password)
            cur.execute(
                """
                INSERT INTO users (username, password, role, status, avatar_url)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (user.username, hashed, "analyst", "pending", user.avatar_url)
            )
            new_id = cur.fetchone()[0]
        conn.commit()

    logger.info(f"New user registered: {user.username} from IP {client_ip}")
    return {
        "message": "Account created successfully. Awaiting admin approval.",
        "user_id": new_id
    }

@router.post("/logout")
async def logout(request: Request, payload: dict = Depends(verify_token)):
    """Log out and revoke refresh token."""
    username = payload.get("sub")
    
    refresh_token = None
    try:
        data = await request.json()
        refresh_token = data.get('refresh_token')
    except:
        pass
    
    db = Database()
    if refresh_token:
        db.revoke_refresh_token(username, refresh_token)
    
    db.log_user_activity(username, "logout", {"message": "User logged out"})
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(payload: dict = Depends(verify_token)):
    """Get current user information."""
    username = payload.get("sub")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, role, avatar_url, status, totp_enabled FROM users WHERE username = %s",
                (username,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return {
        "username": row[0],
        "role": row[1],
        "avatar_url": row[2],
        "status": row[3],
        "totp_enabled": row[4] if len(row) > 4 else False
    }

# ---------- 2FA Endpoints ----------
@router.post("/2fa/setup")
async def setup_2fa(payload: dict = Depends(verify_token)):
    """Setup 2FA for the current user."""
    username = payload.get("sub")
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(username, issuer_name="FraudGuard")
    
    qr = qrcode.make(provisioning_uri)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    db = Database()
    db.store_totp_secret(username, secret)
    
    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "provisioning_uri": provisioning_uri
    }

@router.post("/2fa/verify-setup")
async def verify_2fa_setup(request: TwoFactorSetupRequest, payload: dict = Depends(verify_token)):
    """Verify and enable 2FA."""
    username = payload.get("sub")
    
    db = Database()
    secret = db.get_totp_secret(username)
    if not secret:
        raise HTTPException(400, "2FA setup not initiated")
    
    totp = pyotp.TOTP(secret)
    if not totp.verify(request.code):
        raise HTTPException(400, "Invalid verification code")
    
    db.enable_2fa(username, secret)
    db.log_user_activity(username, "2fa_enabled", {"message": "2FA enabled"})
    
    return {"message": "2FA enabled successfully"}

@router.post("/2fa/verify")
async def verify_2fa(request: TwoFactorVerifyRequest):
    """Verify 2FA code during login."""
    username = request.username
    code = request.code
    
    db = Database()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(404, "User not found")
    
    if not user.get('totp_enabled'):
        raise HTTPException(400, "2FA not enabled for this user")
    
    totp = pyotp.TOTP(user['totp_secret'])
    if not totp.verify(code):
        db.log_user_activity(username, "2fa_failed", {"message": "Invalid 2FA code"})
        raise HTTPException(400, "Invalid 2FA code")
    
    db.log_user_activity(username, "2fa_verified", {"message": "2FA verified"})
    return {"verified": True}

@router.post("/2fa/disable")
async def disable_2fa(request: TwoFactorDisableRequest, payload: dict = Depends(verify_token)):
    """Disable 2FA."""
    username = payload.get("sub")
    
    db = Database()
    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(404, "User not found")
    
    if not user.get('totp_enabled'):
        raise HTTPException(400, "2FA is not enabled")
    
    totp = pyotp.TOTP(user['totp_secret'])
    if not totp.verify(request.code):
        raise HTTPException(400, "Invalid 2FA code")
    
    db.disable_2fa(username)
    db.log_user_activity(username, "2fa_disabled", {"message": "2FA disabled"})
    return {"message": "2FA disabled successfully"}
