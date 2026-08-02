"""
models/model_loader.py
======================
Responsible for loading all trained artefacts from disk exactly once
at startup.  Any downstream service receives a reference to this
singleton — no repeated disk I/O per request.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

import joblib
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ModelArtefacts:
    """
    Container for every artefact produced by train.py.
    Passed around as a single object to avoid repetitive path lookups.
    """
    model:         Any                   # sklearn-compatible (predict_proba)
    scaler:        Any                   # StandardScaler
    feature_names: List[str]
    optimal_threshold: float
    amount_bins:   np.ndarray


def load_artefacts(models_dir: Path) -> ModelArtefacts:
    """
    Load all artefacts from *models_dir*.  Raises FileNotFoundError with a
    clear message if mandatory files are missing so startup fails fast.
    """
    def _load(name: str) -> Any:
        path = models_dir / name
        if not path.exists():
            raise FileNotFoundError(
                f"Required artefact '{name}' not found in {models_dir}. "
                "Re-run train.py to regenerate it."
            )
        return joblib.load(path)

    logger.info("Loading model artefacts from %s", models_dir)

    model     = _load("best_model.pkl")
    scaler    = _load("scaler.pkl")
    bins      = _load("amount_bins.pkl")

    # Feature names — fall back gracefully for older training runs
    feat_path = models_dir / "feature_names.pkl"
    if feat_path.exists():
        feature_names = joblib.load(feat_path)
    else:
        logger.warning("feature_names.pkl missing — using hardcoded column order")
        feature_names = (
            [f"V{i}" for i in range(1, 29)]
            + ["Hour", "Hour_sin", "Hour_cos", "Log_Amount", "Amount_Q"]
        )

    # Optimal threshold — fall back to 0.5
    thr_path = models_dir / "optimal_threshold.pkl"
    threshold = float(joblib.load(thr_path)) if thr_path.exists() else 0.5
    if not thr_path.exists():
        logger.warning("optimal_threshold.pkl missing — falling back to 0.5")

    artefacts = ModelArtefacts(
        model=model,
        scaler=scaler,
        feature_names=feature_names,
        optimal_threshold=threshold,
        amount_bins=bins,
    )

    logger.info(
        "Artefacts loaded | model=%s | features=%d | threshold=%.4f",
        type(model).__name__, len(feature_names), threshold,
    )
    return artefacts
