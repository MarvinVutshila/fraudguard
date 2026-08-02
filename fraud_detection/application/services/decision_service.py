import logging
from fraud_detection.ml.inference.explainability import explain_prediction

logger = logging.getLogger(__name__)

class DecisionService:
    def __init__(self, approve_threshold: float, block_threshold: float):
        self.approve_threshold = approve_threshold
        self.block_threshold = block_threshold
        logger.info("DecisionService ready | approve<%.2f | review=[%.2f,%.2f) | block>=%.2f",
                    approve_threshold, approve_threshold, block_threshold, block_threshold)

    def make_decision(self, probability: float) -> str:
        if probability < self.approve_threshold:
            return "APPROVE"
        elif probability < self.block_threshold:
            return "REVIEW"
        else:
            return "BLOCK"

    # Alias for compatibility with prediction_service (returns tuple)
    def evaluate(self, probability: float):
        decision = self.make_decision(probability)
        # Risk level mapping
        if decision == "APPROVE":
            risk_level = "LOW"
        elif decision == "BLOCK":
            risk_level = "HIGH"
        else:
            risk_level = "MEDIUM"
        return decision, risk_level