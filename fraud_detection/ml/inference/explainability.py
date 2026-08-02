"""
Explainability module – uses SHAPExplainer from utils to generate feature attributions.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from fraud_detection.utils.shap_explainer import SHAPExplainer

logger = logging.getLogger(__name__)

# Global explainer instance (initialised once during startup)
_explainer: Optional[SHAPExplainer] = None
_feature_names: Optional[List[str]] = None


def init_explainer(model, feature_names: List[str]) -> None:
    """Initialise the global SHAP explainer."""
    global _explainer, _feature_names
    try:
        _explainer = SHAPExplainer(model, feature_names)
        _feature_names = feature_names
        logger.info("✅ SHAP explainer initialised with %d features.", len(feature_names))
    except Exception as e:
        logger.warning("⚠️ Failed to initialise SHAP explainer: %s", e)
        _explainer = None
        _feature_names = None


def explain_prediction(transaction_data: Dict[str, Any], probability: float) -> Dict[str, float]:
    """Return SHAP feature contributions for a single transaction."""
    if _explainer is None or _feature_names is None:
        logger.debug("SHAP explainer not available – returning empty explanation.")
        return {}

    try:
        # Build feature vector in the correct order (matching training)
        features = []
        for feat in _feature_names:
            value = transaction_data.get(feat, 0.0)
            try:
                features.append(float(value))
            except (ValueError, TypeError):
                features.append(0.0)

        X = np.array(features).reshape(1, -1)

        # Get contributions (SHAP values for each feature)
        _, contributions = _explainer.explain(X, top_n=len(_feature_names))
        return contributions

    except Exception as e:
        logger.warning("SHAP explanation failed: %s", e)
        return {}


def get_feature_names() -> Optional[List[str]]:
    return _feature_names


def is_available() -> bool:
    return _explainer is not None