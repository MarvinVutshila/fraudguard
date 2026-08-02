from fastapi import APIRouter, HTTPException, Request
from fraud_detection.schemas import TransactionRequest, PredictionResponse
from fraud_detection.core.config import MAX_KNOWN_AMOUNT
from fraud_detection.api.dependencies import get_services
import logging
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------- Helper: patch XGBoost ----------
def patch_xgboost_model(model):
    required_attrs = {
        'use_label_encoder': False,
        'gpu_id': 0,
        'predictor': 'cpu_predictor',
        'n_jobs': 1,
    }
    for attr, value in required_attrs.items():
        if not hasattr(model, attr):
            setattr(model, attr, value)
            logger.debug(f"Set missing attribute {attr}={value}")
        try:
            model.set_params(**{attr: value})
        except Exception:
            pass


# ---------- Helper: convert SHAP output to frontend-friendly format ----------
def convert_shap_to_frontend(explanation):
    if explanation is None:
        return None
    top_features = explanation.top_features
    contributions = explanation.feature_contributions

    if isinstance(contributions, np.ndarray):
        contributions = contributions.tolist()
    if isinstance(contributions, dict):
        contributions = [{"feature": k, "contribution": float(v)} for k, v in contributions.items()]
    elif isinstance(contributions, list):
        if len(contributions) == len(top_features) and all(isinstance(x, (int, float)) for x in contributions):
            contributions = [{"feature": top_features[i], "contribution": float(contributions[i])} for i in range(len(contributions))]
        elif all(isinstance(x, dict) for x in contributions):
            contributions = [{"feature": d.get("feature", ""), "contribution": float(d.get("contribution", 0.0))} for d in contributions]
        else:
            contributions = [{"feature": str(i), "contribution": float(c) if isinstance(c, (int, float)) else 0.0} for i, c in enumerate(contributions)]
    else:
        contributions = []

    explanation.feature_contributions = contributions
    return explanation


# ---------- Single Prediction (POST) ----------
@router.post("/predict", response_model=PredictionResponse)
async def predict(tx: TransactionRequest):
    svc = get_services()
    if tx.Amount > MAX_KNOWN_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Amount ${tx.Amount:,.2f} exceeds maximum ${MAX_KNOWN_AMOUNT:,.2f}."
        )
    try:
        patch_xgboost_model(svc.prediction_service._artefacts.model)
        result = svc.prediction_service.predict(tx, explain=True)
        if result.explanation:
            result.explanation = convert_shap_to_frontend(result.explanation)
        return result
    except Exception as e:
        logger.error(f"Single prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Batch Prediction ----------
@router.post("/predict/batch")
async def predict_batch(request: Request):
    try:
        raw = await request.json()
        logger.info(f"Batch payload type: {type(raw)}")

        if isinstance(raw, dict) and "transactions" in raw:
            transactions = raw["transactions"]
        elif isinstance(raw, list):
            transactions = raw
        else:
            raise HTTPException(400, "Invalid payload. Expected a JSON array or object with 'transactions' key.")

        if not transactions or not isinstance(transactions, list):
            raise HTTPException(400, "'transactions' must be a non-empty list.")

        svc = get_services()
        model = svc.prediction_service._artefacts.model
        patch_xgboost_model(model)

        results = []
        for idx, tx_data in enumerate(transactions):
            try:
                tx_obj = TransactionRequest(
                    transaction_id=tx_data.get('transaction_id'),
                    Amount=tx_data.get('Amount', 0.0),
                    Time=tx_data.get('Time', 0.0),
                    V1=tx_data.get('V1', 0.0), V2=tx_data.get('V2', 0.0),
                    V3=tx_data.get('V3', 0.0), V4=tx_data.get('V4', 0.0),
                    V5=tx_data.get('V5', 0.0), V6=tx_data.get('V6', 0.0),
                    V7=tx_data.get('V7', 0.0), V8=tx_data.get('V8', 0.0),
                    V9=tx_data.get('V9', 0.0), V10=tx_data.get('V10', 0.0),
                    V11=tx_data.get('V11', 0.0), V12=tx_data.get('V12', 0.0),
                    V13=tx_data.get('V13', 0.0), V14=tx_data.get('V14', 0.0),
                    V15=tx_data.get('V15', 0.0), V16=tx_data.get('V16', 0.0),
                    V17=tx_data.get('V17', 0.0), V18=tx_data.get('V18', 0.0),
                    V19=tx_data.get('V19', 0.0), V20=tx_data.get('V20', 0.0),
                    V21=tx_data.get('V21', 0.0), V22=tx_data.get('V22', 0.0),
                    V23=tx_data.get('V23', 0.0), V24=tx_data.get('V24', 0.0),
                    V25=tx_data.get('V25', 0.0), V26=tx_data.get('V26', 0.0),
                    V27=tx_data.get('V27', 0.0), V28=tx_data.get('V28', 0.0)
                )

                pred_result = svc.prediction_service.predict(tx_obj, explain=False)

                results.append({
                    "transaction_id": tx_obj.transaction_id,
                    "amount": tx_obj.Amount,
                    "fraud_probability": pred_result.fraud_probability,
                    "decision": pred_result.decision,
                    "risk_level": pred_result.risk_level
                })

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Transaction {idx} failed: {error_msg}", exc_info=True)
                results.append({
                    "transaction_id": tx_data.get('transaction_id'),
                    "amount": tx_data.get('Amount', 0.0),
                    "fraud_probability": 0.0,
                    "decision": "ERROR",
                    "risk_level": f"ERROR: {error_msg[:50]}"
                })

        logger.info(f"Batch processed: {len(results)} transactions")
        return {"results": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}", exc_info=True)
        raise HTTPException(500, detail=f"Internal error: {str(e)}")
