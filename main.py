# main.py (final, with SPA fallback and activity tracking middleware)

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime
from pydantic import BaseModel
from fraud_detection.core.config import MODELS_DIR, DB_DSN, LOG_LEVEL, APPROVE_THRESHOLD, BLOCK_THRESHOLD
from fraud_detection.ml.inference.model_loader import load_artefacts
from fraud_detection.application.services.prediction_service import PredictionService
from fraud_detection.application.services.decision_service import DecisionService
from fraud_detection.infrastructure.repositories.postgres_transaction_repository import StorageService
from fraud_detection.database.postgres_db import Database, init_db_pool, create_tables
from fraud_detection.api import router
from fraud_detection.api.dependencies import set_services
from fraud_detection.api.routes.auth import create_access_token
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt  # ✅ ADD THIS IMPORT

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# ---------- Support Configuration ----------
SUPPORT_EMAIL = "marvin@support.co.za"
SUPPORT_PHONE = "+27 82 123 4567"

# ---------- Service Classes ----------
class Services:
    pass

services = Services()

class LoginRequest(BaseModel):
    username: str
    password: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Initialising database connection pool...")
        init_db_pool(DB_DSN, min_conn=1, max_conn=10)
        create_tables()
        db = Database()
        
        # Ensure refresh tokens table exists
        if hasattr(db, 'create_refresh_tokens_table'):
            db.create_refresh_tokens_table()
        
        # Ensure TOTP columns exist
        if hasattr(db, 'add_totp_columns'):
            db.add_totp_columns()

        logger.info("Loading model artefacts…")
        artefacts = load_artefacts(MODELS_DIR)

        decision_service = DecisionService(
            approve_threshold=APPROVE_THRESHOLD,
            block_threshold=BLOCK_THRESHOLD
        )

        storage_service = StorageService(db)
        prediction_service = PredictionService(artefacts, decision_service, storage_service)

        services.prediction_service = prediction_service
        services.decision_service = decision_service
        services.storage_service = storage_service

        set_services(services)
        logger.info("Application startup complete.")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield
    logger.info("Shutting down – database pool will be closed automatically")

app = FastAPI(
    title="Fraud Detection API", 
    version="3.0.0", 
    lifespan=lifespan
)

# ---- CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Health check endpoint ----
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "FraudGuard API is running"}

# 1. Include API routers FIRST
app.include_router(router)

# 2. Determine frontend folder
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if not os.path.exists(frontend_path):
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
logger.info(f"Frontend path set to: {frontend_path}")

# 3. Mount static assets (JS, CSS, images) under /assets
assets_path = os.path.join(frontend_path, "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    logger.info(f"Assets mounted from: {assets_path}")

# 4. Middleware to track last_active AND check if user is blocked (IMMEDIATE BLOCK)
@app.middleware("http")
async def track_last_active_and_check_blocked(request: Request, call_next):
    """
    Middleware that:
    1. Tracks user's last_active time
    2. 🔒 IMMEDIATELY checks if user is blocked/deleted on EVERY request
    """
    # Skip public endpoints
    public_paths = {"/auth/login", "/auth/register", "/health", "/", "/docs", "/openapi.json", "/favicon.ico"}
    if request.url.path in public_paths:
        return await call_next(request)
    
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            # ✅ Decode token directly without using verify_token
            SECRET_KEY = os.getenv("JWT_SECRET_KEY")
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            
            # Check token type
            if payload.get("type") != "access":
                return await call_next(request)
            
            username = payload.get("sub")
            
            # Get token issued at time
            token_iat = payload.get("iat")
            if token_iat:
                token_issued_at = datetime.fromtimestamp(token_iat)
            else:
                token_issued_at = None
            
            if username:
                db = Database()
                user = db.get_user_by_username(username)
                
                if user:
                    # 🔒 IMMEDIATE BLOCK CHECK - This runs on EVERY request
                    if user.get('status') == 'blocked':
                        blocked_at = user.get('blocked_at')
                        
                        # If token was issued BEFORE the user was blocked, reject immediately
                        if blocked_at and token_issued_at:
                            if isinstance(blocked_at, str):
                                blocked_at = datetime.fromisoformat(blocked_at.replace('Z', '+00:00'))
                            
                            if token_issued_at < blocked_at:
                                logger.warning(f"🚫 Blocked user (token issued before block) attempted: {username} - {request.url.path}")
                                return JSONResponse(
                                    status_code=403,
                                    content={
                                        "detail": f"Your account has been blocked.\n\nIf you believe this is an error, please contact your system administrator at {SUPPORT_EMAIL}."
                                    }
                                )
                        
                        logger.warning(f"🚫 Blocked user attempted: {username} - {request.url.path}")
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": f"Your account has been blocked.\n\nIf you believe this is an error, please contact your system administrator at {SUPPORT_EMAIL}."
                            }
                        )
                    
                    if user.get('status') == 'deleted':
                        logger.warning(f"🚫 Deleted user attempted: {username} - {request.url.path}")
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": "Your account has been deleted.\n\nIf you believe this is an error, please contact your system administrator."
                            }
                        )
                    
                    if user.get('status') in ['pending', 'rejected']:
                        logger.warning(f"🚫 {user.get('status')} user attempted: {username} - {request.url.path}")
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": f"Your account is {user.get('status')}.\n\nIf you believe this is an error, please contact your system administrator."
                            }
                        )
                    
                    # Update last_active if user is active
                    if hasattr(db, 'update_last_active'):
                        db.update_last_active(username)
        except Exception as e:
            logger.warning(f"Could not verify token or check user status: {e}")
    
    response = await call_next(request)
    return response

# 5. Catch‑all route: serve static files or index.html
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    # Skip API paths that might have been missed
    if full_path.startswith("admin/") or full_path.startswith("auth/") or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    file_path = os.path.join(frontend_path, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
