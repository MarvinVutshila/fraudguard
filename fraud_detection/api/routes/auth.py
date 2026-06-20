from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fraud_detection.api.auth import create_access_token
from fraud_detection.database.postgres_db import get_connection
from passlib.context import CryptContext
import logging

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------- Request Models ----------
class RegisterRequest(BaseModel):
    username: str
    password: str
    avatar_url: str | None = None

class LoginRequest(BaseModel):
    username: str
    password: str

# ---------- Routes ----------
@router.post("/auth/register")
async def register(request: RegisterRequest):
    """
    Register a new user.
    Account is created with status = 'pending'.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if username already exists
            cur.execute("SELECT id FROM users WHERE username = %s", (request.username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Username already exists")

            # Hash password and insert new user
            hashed = pwd_context.hash(request.password)
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role, status, avatar_url)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (request.username, hashed, "analyst", "pending", request.avatar_url)
            )
            conn.commit()

    return {"message": "Account created successfully. Awaiting admin approval."}


@router.post("/auth/login")
async def login(request: LoginRequest):
    """
    Log in an existing user.
    Only users with status = 'active' are allowed to log in.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Retrieve user by username
            cur.execute(
                "SELECT id, password_hash, role, status FROM users WHERE username = %s",
                (request.username,)
            )
            row = cur.fetchone()

            # User not found
            if not row:
                raise HTTPException(status_code=401, detail="Invalid credentials")

            user_id, hashed, role, status = row

            # Verify password
            if not pwd_context.verify(request.password, hashed):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # Check approval status
            if status != "active":
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
                else:
                    raise HTTPException(
                        status_code=403,
                        detail="Account status is not active. Please contact support."
                    )

            # Generate JWT token
            token = create_access_token({"sub": request.username, "role": role})

            return {
                "access_token": token,
                "token_type": "bearer",
                "role": role
            }