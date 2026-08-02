"""
utils/feature_engineering.py
=============================
Pure-function feature engineering that exactly mirrors the transformations
applied in train.py.  The API calls this so every caller gets consistent
features regardless of how the request was constructed.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd


def engineer_features(
    tx_dict: dict,
    feature_names: List[str],
    amount_bins: np.ndarray,
) -> np.ndarray:
    """
    Build a 1-row feature vector from raw transaction fields.

    Parameters
    ----------
    tx_dict       : dict with at minimum 'Time', 'Amount', and V1-V28 keys.
    feature_names : ordered list of column names expected by the scaler/model.
    amount_bins   : quantile bin edges saved by train.py (amount_bins.pkl).

    Returns
    -------
    np.ndarray of shape (1, n_features), dtype float32.
    """
    time   = float(tx_dict.get("Time",   0.0))
    amount = float(tx_dict.get("Amount", 0.0))

    # ── Cyclical hour encoding ─────────────────────────────────────────────
    hour     = (time // 3600) % 24
    hour_sin = float(np.sin(2 * np.pi * hour / 24))
    hour_cos = float(np.cos(2 * np.pi * hour / 24))

    # ── Log-transform of amount ────────────────────────────────────────────
    log_amount = float(np.log1p(amount))

    # ── Quantile bucket for amount (same bins as training) ─────────────────
    bin_idx = pd.cut([amount], bins=amount_bins, labels=False)[0]
    if pd.isna(bin_idx):
        # Amount falls outside training range — assign to the nearest bin
        bin_centers = (amount_bins[:-1] + amount_bins[1:]) / 2
        bin_idx = int(np.argmin(np.abs(bin_centers - amount)))
    amount_q = float(bin_idx)

    # ── Assemble all features in the order the model was trained ───────────
    derived = {
        **{f"V{i}": float(tx_dict.get(f"V{i}", 0.0)) for i in range(1, 29)},
        "Hour":       float(hour),
        "Hour_sin":   hour_sin,
        "Hour_cos":   hour_cos,
        "Log_Amount": log_amount,
        "Amount_Q":   amount_q,
    }

    vector = np.array(
        [derived[name] for name in feature_names],
        dtype=np.float32,
    ).reshape(1, -1)

    return vector
