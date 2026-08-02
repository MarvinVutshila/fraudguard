from __future__ import annotations

import logging
import secrets
from datetime import datetime
import numpy as np
import pandas as pd
import torch
import joblib
from fastapi import HTTPException

from fraud_detection.core.config import MAX_KNOWN_AMOUNT, SHAP_TOP_N, MODELS_DIR
from fraud_detection.ml.inference.model_loader import ModelArtefacts
from fraud_detection.schemas import (
    ExplanationOutput,
    PredictionResponse,
    TransactionRequest,
)
from fraud_detection.application.services.decision_service import DecisionService
from fraud_detection.infrastructure.repositories.postgres_transaction_repository import StorageService
from fraud_detection.ml.feature_engineering import engineer_features
from fraud_detection.ml.inference.explainability import SHAPExplainer
from fraud_detection.ml.autoencoder import Autoencoder

logger = logging.getLogger(__name__)

class PredictionService:
    def __init__(
        self,
        artefacts: ModelArtefacts,
        decision_service: DecisionService,
        storage_service: StorageService,
    ) -> None:
        self._artefacts = artefacts
        self._decision_service = decision_service
        self._storage_service = storage_service
        self._shap = SHAPExplainer(
            model=artefacts.model,
            feature_names=artefacts.feature_names,
        )

        # ---------- Load Autoencoder ----------
        self.ae_model = None
        self.ae_scaler = None
        self.ae_features = None
        try:
            ae_model_path = MODELS_DIR / "autoencoder.pth"
            ae_scaler_path = MODELS_DIR / "autoencoder_scaler.pkl"
            ae_features_path = MODELS_DIR / "autoencoder_features.pkl"
            if all(p.exists() for p in [ae_model_path, ae_scaler_path, ae_features_path]):
                self.ae_scaler = joblib.load(ae_scaler_path)
                self.ae_features = joblib.load(ae_features_path)
                input_dim = len(self.ae_features)
                self.ae_model = Autoencoder(input_dim=input_dim)
                self.ae_model.load_state_dict(torch.load(ae_model_path, map_location='cpu'))
                self.ae_model.eval()
                logger.info("Autoencoder loaded for inference.")
            else:
                logger.warning("Autoencoder artefacts not found. Running without AE error.")
        except Exception as e:
            logger.error(f"Failed to load Autoencoder: {e}")
            self.ae_model = None

        logger.info("PredictionService ready")

    def predict(
        self,
        tx: TransactionRequest,
        explain: bool = True,
    ) -> PredictionResponse:
        self._validate_amount(tx)

        # ---- Generate transaction ID if not provided ----
        if not tx.transaction_id:
            tx.transaction_id = f"txn-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
            logger.info(f"Generated transaction ID: {tx.transaction_id}")

        # ---------- Feature engineering ----------
        base_feature_names = [f for f in self._artefacts.feature_names if f != 'Autoencoder_Error']
        X_raw = engineer_features(
            tx_dict=tx.model_dump(),
            feature_names=base_feature_names,
            amount_bins=self._artefacts.amount_bins,
        )

        X_scaled = self._artefacts.scaler.transform(X_raw)

        # ---------- Autoencoder error ----------
        if self.ae_model is not None:
            try:
                X_raw_df = pd.DataFrame(X_raw, columns=base_feature_names)
                ae_input = X_raw_df[self.ae_features].values
                ae_input_scaled = self.ae_scaler.transform(ae_input)
                with torch.no_grad():
                    ae_tensor = torch.tensor(ae_input_scaled, dtype=torch.float32)
                    recon = self.ae_model(ae_tensor)
                    ae_error = torch.mean((recon - ae_tensor) ** 2).item()
                X_scaled = np.hstack([X_scaled, np.array([[ae_error]])])
                logger.debug(f"Autoencoder error: {ae_error:.4f}")
            except Exception as e:
                logger.error(f"Autoencoder inference failed: {e}. Proceeding without AE error.")
                if 'Autoencoder_Error' in self._artefacts.feature_names:
                    X_scaled = np.hstack([X_scaled, np.array([[0.0]])])
        else:
            if 'Autoencoder_Error' in self._artefacts.feature_names:
                logger.warning("Autoencoder not available; padding with 0 for Autoencoder_Error.")
                X_scaled = np.hstack([X_scaled, np.array([[0.0]])])

        # ---------- Prediction ----------
        prob = float(self._artefacts.model.predict_proba(X_scaled)[0, 1])
        decision, risk_level = self._decision_service.evaluate(prob)

        # ---------- SHAP explanation ----------
        explanation: ExplanationOutput | None = None
        if explain:
            top_features, contributions = self._shap.explain(
                X_scaled, top_n=SHAP_TOP_N
            )
            if top_features:
                explanation = ExplanationOutput(
                    top_features=top_features,
                    feature_contributions=contributions,
                )

        # ---------- Build features dict for storage ----------
        features_dict = {}
        for i, name in enumerate(base_feature_names):
            features_dict[name] = float(X_raw[0][i])
        if 'Autoencoder_Error' in self._artefacts.feature_names:
            features_dict['Autoencoder_Error'] = float(X_scaled[0][-1])
        # Add Amount and Time explicitly (they are part of the raw features anyway)
        features_dict['Amount'] = float(tx.Amount)
        features_dict['Time'] = float(tx.Time)

        logger.debug(f"Features dict built with {len(features_dict)} features")

        # ---------- Store transaction ----------
        self._storage_service.store(
            transaction_id=tx.transaction_id,
            amount=tx.Amount,
            probability=prob,
            decision=decision,
            risk_level=risk_level,
            features=features_dict,
        )

        logger.info(
            "Prediction | tx=%s  prob=%.4f  decision=%s  risk=%s",
            tx.transaction_id, prob, decision, risk_level,
        )

        return PredictionResponse(
            transaction_id=tx.transaction_id,
            fraud_probability=round(prob, 6),
            decision=decision,
            risk_level=risk_level,
            threshold=self._artefacts.optimal_threshold,
            explanation=explanation,
            is_fraud=(decision == "BLOCK")
        )

    @staticmethod
    def _validate_amount(tx: TransactionRequest) -> None:
        if tx.Amount > MAX_KNOWN_AMOUNT:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Transaction amount ${tx.Amount:,.2f} exceeds the maximum "
                    f"allowed amount ${MAX_KNOWN_AMOUNT:,.2f}. "
                    "Contact support if this is a legitimate transaction."
                ),
            )

    def model_info(self) -> dict:
        a = self._artefacts
        version = "v3.0"
        try:
            meta_path = MODELS_DIR / "metadata.pkl"
            if meta_path.exists():
                meta = joblib.load(meta_path)
                if "training_date" in meta:
                    version = meta["training_date"].split()[0]
        except Exception:
            pass

        return {
            "model_type": type(a.model).__name__,
            "n_features": len(a.feature_names),
            "feature_names": a.feature_names,
            "optimal_threshold": a.optimal_threshold,
            "max_allowed_amount": MAX_KNOWN_AMOUNT,
            "approve_threshold": self._decision_service.approve_threshold,
            "block_threshold": self._decision_service.block_threshold,
            "version": version,
        }