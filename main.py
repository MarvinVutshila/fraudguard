# main.py (final, with correct SPA fallback)

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os
from pydantic import BaseModel

from fraud_detection.core.config import MODELS_DIR, DB_DSN, LOG_LEVEL, APPROVE_THRESHOLD, BLOCK_THRESHOLD
from fraud_detection.ml.inference.model_loader import load_artefacts
from fraud_detection.application.services.prediction_service import PredictionService
from fraud_detection.application.services.decision_service import DecisionService
from fraud_detection.infrastructure.repositories.postgres_transaction_repository import StorageService
from fraud_detection.database.postgres_db import Database, init_db_pool, create_tables
from fraud_detection.api.routes import router
from fraud_detection.api.dependencies import set_services
from fraud_detection.api.auth import create_access_token

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class Services:
    pass


services = Services()


class LoginRequest(BaseModel):
    username: str
    password: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database connection pool...")
    init_db_pool(DB_DSN, min_conn=1, max_conn=10)
    create_tables()
    db = Database()

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

    yield
    logger.info("Shutting down – database pool will be closed automatically")


app = FastAPI(title="Fraud Detection API", version="3.0.0", lifespan=lifespan)

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

# 4. Catch‑all route: serve index.html for ANY other path
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    # If the path starts with an API route, let the router handle it (already done)
    # For everything else, serve index.html
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
