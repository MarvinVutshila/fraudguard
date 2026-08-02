from fastapi import APIRouter
from fraud_detection.api.dependencies import get_services

router = APIRouter()

@router.get("/health")
async def health():
    svc = get_services()
    return {"status": "ok" if svc.prediction_service else "down"}
