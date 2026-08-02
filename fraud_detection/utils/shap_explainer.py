"""
utils/shap_explainer.py
=======================
Wraps SHAP TreeExplainer to produce human-readable feature attribution
for every prediction.  The explainer is initialised once and reused.

Design decisions
────────────────
* TreeExplainer is used (not KernelExplainer) because it is orders of
  magnitude faster and works natively with XGBoost / RandomForest.
* For EnsembleModel objects (average of several models), we fall back to
  the first sub-model that SHAP can handle.
* If SHAP is unavailable or fails for any reason the service continues
  without explanations rather than crashing — explainability is
  best-effort in production.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False
    logger.warning("shap package not installed — explainability disabled")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_model(model: Any) -> Any:
    """
    Return a SHAP-compatible model.
    Handles the EnsembleModel wrapper saved by train.py.
    """
    # EnsembleModel has a `.models` attribute (list of base estimators)
    if hasattr(model, "models") and isinstance(model.models, list):
        for sub in model.models:
            if _is_tree_model(sub):
                logger.debug("Using sub-model %s for SHAP", type(sub).__name__)
                return sub
        # No tree sub-model found — return the first one anyway
        return model.models[0]
    return model


def _is_tree_model(m: Any) -> bool:
    name = type(m).__name__
    return any(k in name for k in ("XGB", "RandomForest", "GradientBoosting", "LightGBM"))


# ── Public API ────────────────────────────────────────────────────────────────

class SHAPExplainer:
    """
    Lazy-initialised SHAP TreeExplainer wrapper.

    Usage
    -----
    explainer = SHAPExplainer(model, feature_names)
    top_features, contributions = explainer.explain(X_scaled, top_n=5)
    """

    def __init__(self, model: Any, feature_names: List[str]) -> None:
        self._raw_model    = model
        self.feature_names = feature_names
        self._explainer: Optional[Any] = None

    def _init_explainer(self) -> None:
        if not _SHAP_AVAILABLE:
            return
        try:
            resolved = _resolve_model(self._raw_model)
            self._explainer = shap.TreeExplainer(resolved)
            logger.info("SHAP TreeExplainer initialised for %s", type(resolved).__name__)
        except Exception as exc:
            logger.warning("SHAP explainer init failed: %s — proceeding without explanations", exc)

    def explain(
        self,
        X_scaled: np.ndarray,
        top_n: int = 5,
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Compute SHAP values for a single (1-row) scaled feature matrix.

        Returns
        -------
        top_feature_strings : e.g. ["V14: strongly reduces fraud risk (-0.42)", ...]
        contributions       : {feature_name: shap_value}
        """
        if not _SHAP_AVAILABLE:
            return [], {}

        # Lazy init
        if self._explainer is None:
            self._init_explainer()

        if self._explainer is None:
            return [], {}

        try:
            shap_values = self._explainer.shap_values(X_scaled)

            # For binary classifiers some SHAP versions return a list [neg, pos]
            if isinstance(shap_values, list):
                shap_values = shap_values[1]

            values_1d = shap_values[0]  # shape (n_features,)

            # Sort by absolute magnitude
            indices = np.argsort(np.abs(values_1d))[::-1][:top_n]

            contributions: Dict[str, float] = {
                self.feature_names[i]: round(float(values_1d[i]), 6)
                for i in indices
            }

            top_feature_strings = _format_contributions(contributions)
            return top_feature_strings, contributions

        except Exception as exc:
            logger.warning("SHAP explain failed: %s", exc)
            return [], {}


# ── Formatting ────────────────────────────────────────────────────────────────

def _format_contributions(contributions: Dict[str, float]) -> List[str]:
    """
    Convert {feature: shap_value} into readable English phrases.

    Examples
    --------
    "V14 strongly reduces fraud risk  (SHAP: -0.4200)"
    "Amount_Q moderately increases fraud risk  (SHAP: +0.1530)"
    """
    phrases = []
    for feat, val in contributions.items():
        direction = "increases" if val > 0 else "reduces"
        magnitude = abs(val)

        if magnitude >= 0.30:
            intensity = "strongly"
        elif magnitude >= 0.10:
            intensity = "moderately"
        else:
            intensity = "slightly"

        sign = "+" if val >= 0 else ""
        phrases.append(
            f"{feat} {intensity} {direction} fraud risk  (SHAP: {sign}{val:.4f})"
        )

    return phrases