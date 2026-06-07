# main.py (final, with connection pool)
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
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
    # 1. Initialise the database connection pool (run ONCE at startup)
    logger.info("Initialising database connection pool...")
    init_db_pool(DB_DSN, min_conn=1, max_conn=10)

    # 2. Create tables (if they don't exist)
    create_tables()

    # 3. Create a SINGLE Database instance (reused for all requests)
    db = Database()

    logger.info("Loading model artefacts…")
    artefacts = load_artefacts(MODELS_DIR)

    decision_service = DecisionService(
        approve_threshold=APPROVE_THRESHOLD,
        block_threshold=BLOCK_THRESHOLD
    )

    # 4. Pass the SAME db instance to StorageService
    storage_service = StorageService(db)
    prediction_service = PredictionService(artefacts, decision_service, storage_service)

    services.prediction_service = prediction_service
    services.decision_service = decision_service
    services.storage_service = storage_service

    set_services(services)

    yield
    logger.info("Shutting down – database pool will be closed automatically")
    # Optional: close the pool explicitly if you want
    # from fraud_detection.database.postgres_db import _pool
    # if _pool:
    #     _pool.closeall()


app = FastAPI(title="Fraud Detection API", version="3.0.0", lifespan=lifespan)

# Include API routers FIRST
app.include_router(router)

# Then serve static frontend (catch‑all for unmatched paths)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
