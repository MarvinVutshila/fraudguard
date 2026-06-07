from fastapi import APIRouter
from .auth import router as auth_router
from .health import router as health_router
from .model import router as model_router
from .predictions import router as predictions_router
from .transactions import router as transactions_router
from .history import router as history_router

router = APIRouter()
router.include_router(auth_router, prefix="", tags=["auth"])
router.include_router(health_router, prefix="", tags=["health"])
router.include_router(model_router, prefix="", tags=["model"])
router.include_router(predictions_router, prefix="", tags=["predictions"])
router.include_router(transactions_router, prefix="", tags=["transactions"])
router.include_router(history_router, prefix="", tags=["history"])
