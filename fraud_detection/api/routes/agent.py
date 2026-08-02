from fastapi import APIRouter, Depends, HTTPException
from fraud_detection.api.dependencies import get_services
from fraud_detection.application.services.agent_service import AgentService
from fraud_detection.database.postgres_db import Database
from fraud_detection.schemas import TransactionRequest
import logging

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)

@router.post("/suggest")
async def suggest_decision(request: dict, services=Depends(get_services)):
    """
    AI Agent suggests a decision for a transaction.
    Accepts either:
      - { "transaction_id": "..." }  → fetches stored features
      - { "Amount": ..., "Time": ..., "V1": ..., ... }  → uses direct features
    """
    try:
        tx_id = request.get("transaction_id")
        
        # --- PATH 1: Fetch from Database ---
        if tx_id:
            db = Database()
            tx = db.get_transaction(tx_id)
            if not tx:
                raise HTTPException(404, "Transaction not found")
            
            features = tx.get('features')
            if not features:
                # This will trigger if your DB has 'features': None, which your logs show
                raise HTTPException(
                    400,
                    "No features stored for this transaction. Please re-run prediction to store features."
                )
            
            # Ensure 'Amount' and 'Time' are present
            if 'Amount' not in features and 'amount' in features:
                features['Amount'] = features.pop('amount')
            if 'Time' not in features and 'time' in features:
                features['Time'] = features.pop('time')
            
            tx_request = TransactionRequest(**features)

        # --- PATH 2: Direct Features ---
        else:
            # Direct features mode: normalise field names
            amount = request.get('Amount') or request.get('amount')
            time_val = request.get('Time') or request.get('timestamp') or 0
            
            # 🚨 CRITICAL FIX: Prevent passing None to Pydantic
            if amount is None:
                raise HTTPException(400, "Amount is required to generate a suggestion")
                
            tx_data = {
                'Amount': amount,
                'Time': time_val,
            }
            for key, value in request.items():
                if key.startswith('V'):
                    tx_data[key] = value
            if 'transaction_id' in request:
                tx_data['transaction_id'] = request['transaction_id']
            
            tx_request = TransactionRequest(**tx_data)

        # --- Call the Agent Service ---
        agent = AgentService(services.prediction_service)
        suggestion = agent.suggest_decision(tx_request)
        return suggestion

    except HTTPException:
        # If we manually raised a 400/404, we let it return as is
        raise
    except Exception as e:
        # Catch ALL other unexpected errors (Pydantic, AgentService failing, etc.)
        logger.error(f"Agent suggestion failed: {str(e)}")
        raise HTTPException(400, f"Agent processing failed: {str(e)}")