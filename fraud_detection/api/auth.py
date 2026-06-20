import os
import json
import logging
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from fraud_detection.database.postgres_db import get_connection
from .auth_models import LoginRequest, UserRegister

logger = logging.getLogger(__name__)

# ---------- Configuration ----------
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# ---------- Helper Functions ----------
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

# ---------- Activity Logging (user_activity) ----------
async def log_activity(username: str, action: str, details: dict = None):
    """
    Log user actions into the user_activity table.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_activity (username, action, details) VALUES (%s, %s, %s)",
                    (username, action, json.dumps(details) if details else None)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log activity for {username}: {e}")

# ---------- Router ----------
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(creds: LoginRequest, request: Request):
    """
    Authenticate a user and log the attempt with IP and User-Agent.
    """
    # --- Extract request metadata ---
    user_agent = request.headers.get("user-agent", "unknown")
    client_ip = request.client.host if request.client else "0.0.0.0"

    success = False
    user = None
    role = "analyst"
    status = None

    # --- Authenticate ---
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, password, role, status FROM users WHERE username = %s",
                (creds.username,)
            )
            row = cur.fetchone()
            if row:
                user = row[0]
                hashed = row[1]
                role = row[2]
                status = row[3]
                if status == "active" and verify_password(creds.password, hashed):
                    success = True

    # --- Handle failure cases ---
    if not success:
        # Log the failed attempt before raising exception
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO login_logs (username, success, ip, user_agent, timestamp)
                        VALUES (%s, %s, %s, %s, NOW())
                        """,
                        (creds.username, False, client_ip, user_agent)
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log failed login for {creds.username}: {e}")

        # Raise appropriate HTTP error based on status
        if status == "pending":
            raise HTTPException(
                status_code=403,
                detail="Account pending admin approval. You will be notified once approved."
            )
        elif status == "rejected":
            raise HTTPException(
                status_code=403,
                detail="Account has been rejected by admin. Please contact support."
            )
        elif status == "active":
            raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials or inactive account")

    # --- Successful login ---
    token = create_access_token({"sub": user, "role": role})

    # Log success to user_activity
    await log_activity(user, "login", {"ip": client_ip, "user_agent": user_agent})

    # Log success to login_logs
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO login_logs (username, success, ip, user_agent, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (creds.username, True, client_ip, user_agent)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log successful login for {creds.username}: {e}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role
    }

@router.post("/register")
async def register(user: UserRegister, request: Request):
    """
    Register a new user with pending status.
    """
    # Extract IP for logging (optional)
    client_ip = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "unknown")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check for existing username
            cur.execute("SELECT 1 FROM users WHERE username = %s", (user.username,))
            if cur.fetchone():
                raise HTTPException(409, "Username already exists")

            # Hash password and insert
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

    # Log registration attempt (you can also log to user_activity if desired)
    logger.info(f"New user registered: {user.username} from IP {client_ip}")

    return {
        "message": "Account created successfully. Awaiting admin approval.",
        "user_id": new_id
    }

@router.get("/me")
async def get_current_user_info(payload: dict = Depends(verify_token)):
    """
    Get current user's info from JWT token.
    """
    username = payload.get("sub")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, role, avatar_url, status FROM users WHERE username = %s",
                (username,)
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return {
        "username": row[0],
        "role": row[1],
        "avatar_url": row[2],
        "status": row[3]
    }