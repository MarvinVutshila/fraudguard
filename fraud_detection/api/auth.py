import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from fraud_detection.database.postgres_db import get_connection
from .auth_models import LoginRequest, UserRegister
import json
import logging

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def log_activity(username: str, action: str, details: dict = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_activity (username, action, details) VALUES (%s, %s, %s)",
                (username, action, json.dumps(details) if details else None)
            )
        conn.commit()

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(creds: LoginRequest, request: Request):
    user_agent = request.headers.get("user-agent", "")
    ip = request.client.host
    success = False
    user = None
    role = "analyst"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, password, role, status FROM users WHERE username = %s", (creds.username,))
            row = cur.fetchone()
            if row:
                user = row[0]
                hashed = row[1]
                role = row[2]
                status = row[3]
                if status == "active" and verify_password(creds.password, hashed):
                    success = True

    if success:
        token = create_access_token({"sub": user, "role": role})
        await log_activity(user, "login", {"ip": ip, "user_agent": user_agent})
    else:
        pass

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO login_logs (username, success, ip, user_agent) VALUES (%s, %s, %s, %s)",
                (creds.username, success, ip, user_agent)
            )
        conn.commit()

    if not success:
        raise HTTPException(status_code=401, detail="Invalid credentials or inactive account")
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register")
async def register(user: UserRegister, request: Request):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE username = %s", (user.username,))
            if cur.fetchone():
                raise HTTPException(409, "Username already exists")
            hashed = hash_password(user.password)
            cur.execute(
                "INSERT INTO users (username, password, avatar_url, status) VALUES (%s, %s, %s, 'active') RETURNING id",
                (user.username, hashed, user.avatar_url)
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    return {"message": "Account created successfully. You can now log in."}

@router.get("/me")
async def get_current_user_info(payload: dict = Depends(verify_token)):
    username = payload.get("sub")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, role, avatar_url, status FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return {"username": row[0], "role": row[1], "avatar_url": row[2], "status": row[3]}
