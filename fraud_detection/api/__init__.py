from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from fraud_detection.api.routes import (
    auth_router,
    health_router,
    model_router,
    predictions_router,
    transactions_router,
    admin_router,
    samples_router,
    monitoring_router,
    agent_router,          # <-- NEW import
)
from fraud_detection.api.dependencies import get_current_user
from fraud_detection.database.postgres_db import get_connection
from fraud_detection.api.routes.settings import router as settings_router
import base64

# ---- Create main router first ----
router = APIRouter()

# ---- Include all routers ----
router.include_router(settings_router)          # Settings endpoints
router.include_router(auth_router)
router.include_router(health_router)
router.include_router(model_router, prefix="/model")
router.include_router(predictions_router)
router.include_router(transactions_router)
router.include_router(admin_router)
router.include_router(samples_router)
router.include_router(monitoring_router)
router.include_router(agent_router)            # <-- NEW include

# ---- Additional endpoints ----
@router.post("/users/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    contents = await file.read()
    if len(contents) > 1_000_000:
        raise HTTPException(400, "Avatar too large (max 1MB)")
    b64 = base64.b64encode(contents).decode()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET avatar_url = %s WHERE username = %s", (b64, current_user["sub"]))
        conn.commit()
    return {"avatar": b64}

__all__ = ['router']