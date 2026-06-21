import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fraud_detection.api.dependencies import get_services, verify_token

logger = logging.getLogger(__name__)

router = APIRouter()

class OverrideRequest(BaseModel):
    new_decision: str
    reason: str

@router.get("/transactions")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    decision: Optional[str] = None,
    user=Depends(verify_token)
):
    """
    Fetch transactions with override information.
    """
    try:
        # Normalize decision: treat empty string or 'All' as None
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

        # Get the TRUE total count (without pagination)
        total = svc.storage_service.count_transactions(decision)

        # Log the values for debugging
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
    Override a transaction decision and update the transaction itself.
    """
    try:
        svc = get_services()
        original = svc.storage_service.get_transaction(tx_id)
        if not original:
            raise HTTPException(status_code=404, detail="Transaction not found")

        original_decision = original.get("decision")
        new_decision = req.new_decision
        reason = req.reason
        username = user.get("sub", "unknown")

        # Save override history
        svc.storage_service.set_override(tx_id, original_decision, new_decision, username, reason)

        # Update the transaction's decision and risk level
        risk_map = {
            'APPROVE': 'LOW',
            'BLOCK': 'HIGH',
            'REVIEW': 'MEDIUM'
        }
        new_risk = risk_map.get(new_decision, 'MEDIUM')
        svc.storage_service.update_transaction_decision(tx_id, new_decision, new_risk)

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
