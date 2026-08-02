import logging
from typing import Dict, Any
from fraud_detection.ml.inference.explainability import explain_prediction
from fraud_detection.application.services.prediction_service import PredictionService
from fraud_detection.schemas import TransactionRequest

logger = logging.getLogger(__name__)

# Configuration constants to prevent "magic numbers" and biases
CONFIDENCE_HIGH_APPROVE_THRESHOLD = 0.10
CONFIDENCE_HIGH_BLOCK_THRESHOLD = 0.90

class AgentService:
    def __init__(self, prediction_service: PredictionService):
        self.prediction_service = prediction_service

    def suggest_decision(self, tx: TransactionRequest) -> Dict[str, Any]:
        """
        Suggest a decision for a transaction using the model and SHAP explanations.
        """
        # 1. Get prediction response from the ML model
        pred_response = self.prediction_service.predict(tx, explain=True)

        # Extract data safely (standardize casing)
        probability = float(getattr(pred_response, 'fraud_probability', 0.0))
        raw_decision = getattr(pred_response, 'decision', 'REVIEW')
        decision = raw_decision.upper()  # Normalize to uppercase

        # 2. Compute SHAP explanation (using your global explainer)
        # We convert the Pydantic model to a dict safely for any Pydantic v1/v2 version
        tx_dict = tx.model_dump() if hasattr(tx, 'model_dump') else tx.dict()
        explanation = self._explain(tx_dict, probability)

        # 3. Build the response
        return {
            "suggested_decision": decision,
            "probability": probability,
            "confidence": self._confidence(probability, decision),
            "explanation": explanation,
            "reason": self._generate_reason(decision, probability, explanation),
        }

    def _explain(self, data: Dict[str, Any], probability: float) -> Dict[str, float]:
        """
        Safely wraps SHAP explainability so the Agent never crashes on missing explainers.
        """
        try:
            return explain_prediction(data, probability)
        except Exception as e:
            logger.warning(f"SHAP explanation failed (returning empty dict): {e}")
            return {}

    def _confidence(self, prob: float, decision: str) -> str:
        """
        Calculates confidence based purely on model probability, avoiding bias.
        """
        if decision == "APPROVE":
            return "high" if prob < CONFIDENCE_HIGH_APPROVE_THRESHOLD else "medium"
        elif decision == "BLOCK":
            return "high" if prob > CONFIDENCE_HIGH_BLOCK_THRESHOLD else "medium"
        return "low"

    def _generate_reason(self, decision: str, prob: float, explanation: Dict[str, float]) -> str:
        """
        Generates a human-readable explanation. If SHAP data is missing, it gracefully falls back.
        """
        prob_str = f"{prob:.2%}"
        
        if decision == "APPROVE":
            return f"Model predicts low fraud risk (probability {prob_str}) – transaction appears normal."
        
        elif decision == "BLOCK":
            # If SHAP explanation is empty, don't crash or print an empty list
            if explanation:
                top_features = sorted(explanation.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
                features_str = ", ".join([f"{k} (impact {v:+.2f})" for k, v in top_features])
                return f"Model predicts high fraud risk (probability {prob_str}) due to: {features_str}."
            else:
                return f"Model predicts high fraud risk (probability {prob_str}) – critical anomaly detected."
        
        else: # Default to REVIEW/uncertain
            return f"Model is uncertain (probability {prob_str}) – manual review recommended."