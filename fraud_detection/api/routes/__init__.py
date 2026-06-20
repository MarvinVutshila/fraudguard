from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fraud_detection.api.auth import router as auth_router
from .health import router as health_router
from .model import router as model_router
from .predictions import router as predictions_router
from .transactions import router as transactions_router
from .history import router as history_router
from .admin import router as admin_router          # <-- admin_router imported
from fraud_detection.api.dependencies import get_current_user
from fraud_detection.database.postgres_db import get_connection
import base64

router = APIRouter()

# Include all routers
router.include_router(auth_router)          # /auth/...
router.include_router(health_router)        # /health
router.include_router(model_router)          # /model/...
router.include_router(predictions_router)    # /predict/...
router.include_router(transactions_router)   # /transactions/...
router.include_router(history_router)        # /history/...
router.include_router(admin_router)          # /admin/...   <-- THIS IS CRITICAL

@router.post("/users/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    contents = await file.read()
    if len(contents) > 1_000_000:
        raise HTTPException(400, "Avatar too large (max 1MB)")
    b64 = base64.b64encode(contents).decode()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET avatar_url = %s WHERE username = %s", (b64, current_user.username))
        conn.commit()
    return {"avatar": b64}