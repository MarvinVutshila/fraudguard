# main.py - FraudGuard API entry point (AWS EC2 production)
# Includes Monitoring, SPA fallback, activity tracking, AI Agent, and Knowledge Base POST fix

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import asyncio
from datetime import datetime, timedelta
from pydantic import BaseModel
from fraud_detection.core.config import MODELS_DIR, DB_DSN, LOG_LEVEL, APPROVE_THRESHOLD, BLOCK_THRESHOLD
from fraud_detection.ml.inference.model_loader import load_artefacts
from fraud_detection.ml.inference.explainability import init_explainer
from fraud_detection.application.services.prediction_service import PredictionService
from fraud_detection.application.services.decision_service import DecisionService
from fraud_detection.infrastructure.repositories.postgres_transaction_repository import StorageService
from fraud_detection.database.postgres_db import Database, init_db_pool, create_tables
from fraud_detection.api import router
from fraud_detection.api.dependencies import set_services, verify_token
from fraud_detection.api.routes import assistant, knowledge_base
from fraud_detection.api.routes.knowledge_base import KBEntryCreate
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt

# ---------- Monitoring ----------
from fraud_detection.monitoring.middleware import (
    attach_monitoring_middleware,
    start_monitoring,
    stop_monitoring
)

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# ---------- Support Configuration ----------
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "marvinmakhubela04@gmail.com")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+27670957647")

# ---------- Service Classes ----------
class Services:
    pass

services = Services()

class LoginRequest(BaseModel):
    username: str
    password: str

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Initialising database connection pool...")
        init_db_pool(DB_DSN, min_conn=1, max_conn=10)
        create_tables()
        db = Database()
        
        if hasattr(db, 'create_refresh_tokens_table'):
            db.create_refresh_tokens_table()
        if hasattr(db, 'add_totp_columns'):
            db.add_totp_columns()

        logger.info("Loading model artefacts…")
        artefacts = load_artefacts(MODELS_DIR)

        init_explainer(artefacts.model, artefacts.feature_names)
        logger.info("SHAP explainer initialised.")

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

        start_monitoring(app)
        logger.info("Monitoring workers started.")

        asyncio.create_task(cleanup_scheduler())

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield
    logger.info("Shutting down – database pool will be closed automatically")
    stop_monitoring()
    logger.info("Monitoring stopped.")

# ---------- Daily Cleanup Scheduler ----------
async def cleanup_scheduler():
    BASE_URL = os.getenv("INTERNAL_API_URL", "http://localhost:8000")
    while True:
        now = datetime.utcnow()
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        sleep_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(sleep_seconds)

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BASE_URL}/monitoring/cleanup")
                if resp.status_code == 200:
                    logger.info("✅ Daily monitoring cleanup completed.")
                else:
                    logger.warning(f"Cleanup endpoint returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Cleanup scheduler error: {e}")

# ---------- FastAPI App ----------
app = FastAPI(
    title="Fraud Detection API",
    version="3.0.0",
    lifespan=lifespan
)

attach_monitoring_middleware(app)

# ---- CORS Middleware (cleaned for EC2 only) ----
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "http://13.40.181.181"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Health check ----
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "FraudGuard API is running"}

# ---- Include all routers ----
app.include_router(router)
app.include_router(assistant.router)
app.include_router(knowledge_base.router)

# ---- FIX: Fallback POST route for /knowledge_base (no trailing slash) ----
@app.post("/knowledge_base")
async def fallback_create_knowledge(entry: KBEntryCreate, user=Depends(verify_token)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin required")
    db = Database()
    entry_id = db.create_knowledge_base_entry(
        question=entry.question,
        answer=entry.answer,
        category=entry.category,
        keywords=entry.keywords
    )
    return {"id": entry_id, "message": "Entry created"}

# ---- Frontend static files ----
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if not os.path.exists(frontend_path):
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
logger.info(f"Frontend path set to: {frontend_path}")

assets_path = os.path.join(frontend_path, "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    logger.info(f"Assets mounted from: {assets_path}")

# ---- Middleware for user tracking and block checks ----
@app.middleware("http")
async def track_last_active_and_check_blocked(request: Request, call_next):
    public_paths = {"/auth/login", "/auth/register", "/health", "/", "/docs", "/openapi.json", "/favicon.ico"}
    if request.url.path in public_paths:
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            SECRET_KEY = os.getenv("JWT_SECRET_KEY")
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            if payload.get("type") != "access":
                return await call_next(request)
            username = payload.get("sub")
            token_iat = payload.get("iat")
            token_issued_at = datetime.fromtimestamp(token_iat) if token_iat else None

            if username:
                db = Database()
                user = db.get_user_by_username(username)
                if user:
                    status = user.get('status')
                    if status == 'blocked':
                        blocked_at = user.get('blocked_at')
                        if blocked_at and token_issued_at:
                            if isinstance(blocked_at, str):
                                blocked_at = datetime.fromisoformat(blocked_at.replace('Z', '+00:00'))
                            if token_issued_at < blocked_at:
                                logger.warning(f"🚫 Blocked user (token issued before block) attempted: {username} - {request.url.path}")
                                return JSONResponse(
                                    status_code=403,
                                    content={"detail": f"Your account has been blocked.\n\nIf you believe this is an error, please contact your system administrator at {SUPPORT_EMAIL}."}
                                )
                        logger.warning(f"🚫 Blocked user attempted: {username} - {request.url.path}")
                        return JSONResponse(
                            status_code=403,
                            content={"detail": f"Your account has been blocked.\n\nIf you believe this is an error, please contact your system administrator at {SUPPORT_EMAIL}."}
                        )
                    if status in ['pending', 'rejected', 'deleted']:
                        logger.warning(f"🚫 {status} user attempted: {username} - {request.url.path}")
                        return JSONResponse(
                            status_code=403,
                            content={"detail": f"Your account is {status}.\n\nIf you believe this is an error, please contact your system administrator."}
                        )
                    if hasattr(db, 'update_last_active'):
                        db.update_last_active(username)
        except Exception as e:
            logger.warning(f"Could not verify token or check user status: {e}")
    
    response = await call_next(request)
    return response

# ---- Catch‑all SPA route ----
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
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
