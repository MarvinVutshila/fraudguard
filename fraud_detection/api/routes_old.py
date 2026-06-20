import logging
import json
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from datetime import datetime

# Import your dependencies
from fraud_detection.api.dependencies import get_services
from fraud_detection.api.auth import verify_token

logger = logging.getLogger(__name__)

# ---------- Router ----------
router = APIRouter()

# ---------- Helper Models ----------
class TransactionOverrideRequest(BaseModel):
    transaction_id: str
    new_decision: str
    reason: Optional[str] = None

class PredictBatchRequest(BaseModel):
    transactions: List[Dict[str, Any]]

# ---------- MAPPING FUNCTION ----------
def map_frontend_to_kaggle_features(tx: Dict[str, Any]) -> Dict[str, float]:
    """
    Converts frontend payload to the exact 30 features the Kaggle model expects.
    """
    raw_amount = tx.get('amount', 0)
    if isinstance(raw_amount, str):
        raw_amount = raw_amount.replace('$', '').replace(',', '').strip()
    try:
        amount = float(raw_amount)
    except (ValueError, TypeError):
        amount = 0.0

    features = {
        'Time': 0.0,
        'V1': 0.0, 'V2': 0.0, 'V3': 0.0, 'V4': 0.0, 'V5': 0.0,
        'V6': 0.0, 'V7': 0.0, 'V8': 0.0, 'V9': 0.0, 'V10': 0.0,
        'V11': 0.0, 'V12': 0.0, 'V13': 0.0, 'V14': 0.0, 'V15': 0.0,
        'V16': 0.0, 'V17': 0.0, 'V18': 0.0, 'V19': 0.0, 'V20': 0.0,
        'V21': 0.0, 'V22': 0.0, 'V23': 0.0, 'V24': 0.0, 'V25': 0.0,
        'V26': 0.0, 'V27': 0.0, 'V28': 0.0,
        'Amount': amount
    }
    return features

# ---------- ENDPOINTS ----------

@router.get("/")
async def root():
    return {"message": "Fraud Detection API is running"}

@router.get("/transactions")
async def get_transactions(
    limit: int = 100,
    offset: int = 0,
    decision: Optional[str] = None,
    payload: dict = Depends(verify_token)
):
    """Fetch transactions from the database."""
    try:
        services = get_services()
        storage = services.storage_service
        if not storage:
            raise HTTPException(503, "Storage service unavailable")

        if decision:
            transactions = storage.get_transactions(limit, offset, decision.upper())
            total = storage.count_transactions(decision.upper())
        else:
            transactions = storage.get_transactions(limit, offset)
            total = storage.count_transactions()

        return {
            "transactions": transactions,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch transactions")

@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    """Fetch a single transaction by ID."""
    try:
        services = get_services()
        storage = services.storage_service
        if not storage:
            raise HTTPException(503, "Storage service unavailable")

        tx = storage.get_transaction(transaction_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")
        return tx
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch transaction")

@router.post("/predict/batch")
async def predict_batch(request: Request):
    """
    Accepts a batch of transactions from the frontend, maps them to Kaggle
    features, and returns ML fraud probabilities.
    """
    try:
        raw_data = await request.json()

        if not raw_data or not isinstance(raw_data, list):
            raise HTTPException(
                status_code=400,
                detail="Invalid payload. Expected a non-empty list of transactions."
            )

        logger.info(f"Received {len(raw_data)} transactions for batch prediction")

        mapped_transactions = []
        for tx in raw_data:
            mapped_tx = map_frontend_to_kaggle_features(tx)
            mapped_transactions.append(mapped_tx)

        services = get_services()
        prediction_service = services.prediction_service
        if not prediction_service:
            logger.error("Prediction service not available.")
            raise HTTPException(status_code=503, detail="Prediction service unavailable.")

        model = prediction_service.artefacts.get('model')
        if model is None:
            logger.error("Model not found in artefacts.")
            raise HTTPException(status_code=500, detail="ML model not loaded.")

        df = pd.DataFrame(mapped_transactions)

        if hasattr(model, 'feature_names_in_'):
            expected_columns = list(model.feature_names_in_)
            logger.info(f"Model expects columns: {expected_columns}")
        else:
            expected_columns = list(mapped_transactions[0].keys()) if mapped_transactions else []

        for col in expected_columns:
            if col not in df.columns:
                df[col] = 0.0

        X = df[expected_columns]
        probabilities = model.predict_proba(X)[:, 1].tolist()

        logger.info(f"Successfully predicted {len(probabilities)} transactions")

        return {"predictions": probabilities}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal scoring engine error. Please check server logs."
        )

# ---------- Admin Endpoints ----------

@router.get("/admin/users/pending")
async def get_pending_users(payload: dict = Depends(verify_token)):
    """Get all pending user registrations (admin only)."""
    try:
        services = get_services()
        db = services.storage_service.db if services.storage_service else None
        if not db:
            raise HTTPException(503, "Database service unavailable")

        pending = db.get_pending_users()
        return {"pending": pending}
    except Exception as e:
        logger.error(f"Error fetching pending users: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch pending users")

@router.post("/admin/users/approve")
async def approve_user(request: Request, payload: dict = Depends(verify_token)):
    """Approve or reject a pending user."""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        approve = data.get('approve', False)

        if not user_id:
            raise HTTPException(400, "user_id is required")

        services = get_services()
        db = services.storage_service.db if services.storage_service else None
        if not db:
            raise HTTPException(503, "Database service unavailable")

        db.approve_user(user_id, approve)
        status = "approved" if approve else "rejected"
        return {"message": f"User {status} successfully"}
    except Exception as e:
        logger.error(f"Error approving user: {e}", exc_info=True)
        raise HTTPException(500, "Failed to update user status")

@router.get("/admin/login-logs")
async def get_login_logs(
    limit: int = 100,
    payload: dict = Depends(verify_token)
):
    """Fetch recent login logs for the admin panel."""
    try:
        services = get_services()
        db = services.storage_service.db if services.storage_service else None
        if not db:
            raise HTTPException(503, "Database service unavailable")

        logs = db.get_login_logs(limit)
        return logs
    except Exception as e:
        logger.error(f"Error fetching login logs: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch login logs")

# ---------- FIXED: Override endpoint now updates the transaction ----------
@router.post("/admin/transactions/override")
async def override_transaction(request: Request, payload: dict = Depends(verify_token)):
    """Override a transaction decision and update the transaction itself."""
    try:
        data = await request.json()
        transaction_id = data.get('transaction_id')
        new_decision = data.get('new_decision')
        reason = data.get('reason', '')
        username = payload.get('sub', 'unknown')

        if not transaction_id or not new_decision:
            raise HTTPException(400, "transaction_id and new_decision are required")

        services = get_services()
        storage = services.storage_service
        if not storage:
            raise HTTPException(503, "Storage service unavailable")

        tx = storage.get_transaction(transaction_id)
        if not tx:
            raise HTTPException(404, "Transaction not found")

        original_decision = tx.get('decision')

        # Save override history
        storage.set_override(transaction_id, original_decision, new_decision, username, reason)

        # Update the transaction's decision and risk level
        risk_map = {
            'APPROVE': 'LOW',
            'BLOCK': 'HIGH',
            'REVIEW': 'MEDIUM'
        }
        new_risk = risk_map.get(new_decision, 'MEDIUM')
        storage.db.update_transaction_decision(transaction_id, new_decision, new_risk)

        return {"message": f"Transaction {transaction_id} overridden to {new_decision}"}
    except Exception as e:
        logger.error(f"Error overriding transaction: {e}", exc_info=True)
        raise HTTPException(500, "Failed to override transaction")

# ---------- Override History ----------
@router.get("/admin/overrides")
async def get_overrides(
    limit: int = 100,
    payload: dict = Depends(verify_token)
):
    """Fetch transaction override history for the Approval Audit Log."""
    try:
        services = get_services()
        db = services.storage_service.db if services.storage_service else None
        if not db:
            raise HTTPException(503, "Database service unavailable")

        overrides = db.get_all_overrides(limit)
        return {"overrides": overrides}
    except Exception as e:
        logger.error(f"Error fetching overrides: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch override history")
