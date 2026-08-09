import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from fraud_detection.api.dependencies import get_services, verify_token
from fraud_detection.schemas import TransactionRequest

logger = logging.getLogger(__name__)

router = APIRouter()

class OverrideRequest(BaseModel):
    new_decision: str
    reason: str
    new_probability: Optional[float] = None


@router.get("/transactions")
async def get_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    decision: Optional[str] = None,
    user=Depends(verify_token)
):
    """Fetch transactions with override info."""
    try:
        if decision in ("", "All", "all"):
            decision = None

        svc = get_services()
        records = svc.storage_service.get_transactions(limit, offset, decision)

        result = []
        for rec in records:
            tx_id = rec.get("transaction_id")
            if not tx_id:
                logger.warning(f"Transaction missing ID: {rec}")
                continue
            override = svc.storage_service.get_override(tx_id)
            rec["overridden"] = override is not None
            rec["effective_decision"] = override["new_decision"] if override else rec.get("decision")
            rec["overridden_by"] = override["overridden_by"] if override else None
            result.append(rec)

        total = svc.storage_service.count_transactions(decision)

        logger.info(f"[transactions] limit={limit}, offset={offset}, decision={decision}, records={len(result)}, total={total}")
        return {"transactions": result, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Error in /transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/transactions/review-count")
async def get_review_count(user=Depends(verify_token)):
    """Return the number of pending REVIEW transactions (not overridden)."""
    try:
        svc = get_services()
        count = svc.storage_service.count_pending_reviews()
        return {"pending": count}
    except Exception as e:
        logger.error(f"Error in /transactions/review-count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch review count")


@router.post("/transactions/{tx_id}/override")
async def override_transaction(
    tx_id: str,
    req: OverrideRequest,
    user=Depends(verify_token)
):
    """Override a transaction, update decision, risk, and optionally probability."""
    try:
        svc = get_services()
        original = svc.storage_service.get_transaction(tx_id)
        if not original:
            raise HTTPException(status_code=404, detail="Transaction not found")

        username = user.get("sub", "unknown")
        risk_map = {'APPROVE': 'LOW', 'BLOCK': 'HIGH', 'REVIEW': 'MEDIUM'}
        new_risk = risk_map.get(req.new_decision, 'MEDIUM')

        # Save override history
        svc.storage_service.set_override(
            tx_id,
            original.get("decision"),
            req.new_decision,
            username,
            req.reason
        )

        # Update transaction (probability optional)
        svc.storage_service.db.update_transaction_decision(
            tx_id,
            req.new_decision,
            new_risk,
            req.new_probability
        )

        return {
            "status": "ok",
            "new_decision": req.new_decision,
            "message": f"Transaction {tx_id} overridden to {req.new_decision}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error overriding {tx_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Override failed: {str(e)}")


@router.post("/transactions/ingest")
async def ingest_transaction(request: dict):
    """
    Ingest a transaction: predict, deduplicate, store.
    Returns inserted/skipped status.
    """
    try:
        svc = get_services()

        # Extract features
        amount = request.get('Amount') or request.get('amount')
        time_val = request.get('Time') or request.get('timestamp') or 0
        features = {"Amount": amount, "Time": time_val}
        for k, v in request.items():
            if k.startswith('V'):
                features[k] = v

        # Predict
        tx_request = TransactionRequest(**features)
        pred = svc.prediction_service.predict(tx_request, explain=False)

        # Generate transaction ID
        new_tx_id = f"txn-{uuid.uuid4().hex[:12]}"

        # Save with deduplication – the DB layer handles duplicate transaction_id
        inserted = svc.storage_service.create_transaction_if_not_exists(
            transaction_id=new_tx_id,
            amount=amount,
            probability=float(pred.fraud_probability),
            decision=pred.decision,
            risk_level=pred.risk_level,
            features=features
        )

        if inserted:
            logger.info(f"Ingested {new_tx_id} | prob={pred.fraud_probability:.4f} | decision={pred.decision}")
            return {
                "status": "success",
                "transaction_id": new_tx_id,
                "probability": pred.fraud_probability,
                "decision": pred.decision,
                "risk_level": pred.risk_level,
                "inserted": True
            }
        else:
            logger.info(f"Skipped duplicate transaction (ID already exists)")
            return {
                "status": "skipped",
                "transaction_id": new_tx_id,
                "message": "Duplicate transaction_id, not inserted",
                "inserted": False
            }
    except Exception as e:
        logger.error(f"Ingest error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Ingestion failed: {str(e)}")