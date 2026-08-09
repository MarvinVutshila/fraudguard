import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fraud_detection.api.dependencies import get_services, verify_token
from fraud_detection.schemas import TransactionRequest

logger = logging.getLogger(__name__)

router = APIRouter()

class OverrideRequest(BaseModel):
    new_decision: str
    reason: str
    new_probability: Optional[float] = None  # <-- Accept AI's new probability

@router.get("/transactions")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    decision: Optional[str] = None,
    user=Depends(verify_token)
):
    """
    Fetch transactions with override information.
    ✅ Accessible to all authenticated users (analysts + admins)
    """
    try:
        # Normalize decision
        if decision in ("", "All", "all"):
            decision = None

        svc = get_services()
        records = svc.storage_service.get_transactions(limit, offset, decision)

        # Enrich records with override data
        result = []
        for rec in records:
            tx_id = rec.get("transaction_id")
            if not tx_id:
                logger.warning(f"Transaction record missing transaction_id: {rec}")
                continue

            override = svc.storage_service.get_override(tx_id)
            rec["overridden"] = override is not None
            rec["effective_decision"] = override["new_decision"] if override else rec.get("decision")
            rec["overridden_by"] = override["overridden_by"] if override else None
            result.append(rec)

        total = svc.storage_service.count_transactions(decision)

        logger.info(f"[transactions] limit={limit}, offset={offset}, decision={decision}, records={len(result)}, total={total}")

        return {
            "transactions": result,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error in /transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/transactions/{tx_id}/override")
async def override_transaction(
    tx_id: str,
    req: OverrideRequest,
    user=Depends(verify_token)
):
    """
    Override a transaction decision, update the transaction itself,
    and optionally save the new AI probability (but **not** in the override history).
    """
    try:
        svc = get_services()
        original = svc.storage_service.get_transaction(tx_id)
        if not original:
            raise HTTPException(status_code=404, detail="Transaction not found")

        original_decision = original.get("decision")
        new_decision = req.new_decision
        reason = req.reason
        new_probability = req.new_probability
        username = user.get("sub", "unknown")

        # Save override history (without new_probability)
        svc.storage_service.set_override(
            tx_id,
            original_decision,
            new_decision,
            username,
            reason
        )

        # Update the transaction's decision and risk level
        risk_map = {
            'APPROVE': 'LOW',
            'BLOCK': 'HIGH',
            'REVIEW': 'MEDIUM'
        }
        new_risk = risk_map.get(new_decision, 'MEDIUM')

        # Also update the probability if a new one was provided
        svc.storage_service.db.update_transaction_decision(tx_id, new_decision, new_risk, new_probability)

        return {
            "status": "ok",
            "new_decision": new_decision,
            "message": f"Transaction {tx_id} overridden to {new_decision}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error overriding transaction {tx_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Override failed: {str(e)}")

# ---------------------------------------------------------
# Real‑time Ingestion Endpoint
# ---------------------------------------------------------
@router.post("/transactions/ingest")
async def ingest_transaction(request: dict):
    """
    Receives raw transaction data, runs the ML model
    to calculate the REAL fraud probability, and saves it to the database.
    """
    try:
        svc = get_services()

        # 1. Extract features
        amount = request.get('Amount') or request.get('amount')
        time_val = request.get('Time') or request.get('timestamp') or 0

        features = {
            "Amount": amount,
            "Time": time_val,
        }
        for key, value in request.items():
            if key.startswith('V'):
                features[key] = value

        # 2. Get prediction from ML model
        tx_request = TransactionRequest(**features)
        pred_response = svc.prediction_service.predict(tx_request, explain=False)

        real_probability = float(pred_response.fraud_probability)
        real_decision = pred_response.decision

        # 3. Set Risk Level
        if real_probability > 0.8:
            risk_level = 'CRITICAL'
        elif real_probability > 0.5:
            risk_level = 'HIGH'
        elif real_probability > 0.2:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        # 4. Save the transaction
        new_tx_id = f"txn-{uuid.uuid4().hex[:12]}"

        svc.storage_service.create_transaction(
            transaction_id=new_tx_id,
            amount=amount,
            probability=real_probability,
            decision=real_decision,
            risk_level=risk_level,
            features=features
        )

        logger.info(f"Ingested transaction {new_tx_id} with decision {real_decision} (prob: {real_probability:.4f})")

        return {
            "status": "success",
            "transaction_id": new_tx_id,
            "probability": real_probability,
            "decision": real_decision,
            "risk_level": risk_level
        }
    except Exception as e:
        logger.error(f"Error ingesting transaction: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Ingestion failed: {str(e)}")
