from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TransactionRequest(BaseModel):
    V1: float = 0.0; V2: float = 0.0; V3: float = 0.0; V4: float = 0.0; V5: float = 0.0
    V6: float = 0.0; V7: float = 0.0; V8: float = 0.0; V9: float = 0.0; V10: float = 0.0
    V11: float = 0.0; V12: float = 0.0; V13: float = 0.0; V14: float = 0.0; V15: float = 0.0
    V16: float = 0.0; V17: float = 0.0; V18: float = 0.0; V19: float = 0.0; V20: float = 0.0
    V21: float = 0.0; V22: float = 0.0; V23: float = 0.0; V24: float = 0.0; V25: float = 0.0
    V26: float = 0.0; V27: float = 0.0; V28: float = 0.0
    Time: float = Field(..., ge=0.0)
    Amount: float = Field(..., ge=0.0)
    transaction_id: Optional[str] = None


class BatchRequest(BaseModel):
    transactions: List[TransactionRequest]


class ExplanationOutput(BaseModel):
    top_features: List[str]
    feature_contributions: Dict[str, float]


class PredictionResponse(BaseModel):
    transaction_id: Optional[str]
    fraud_probability: float
    decision: str
    risk_level: str
    threshold: float
    explanation: Optional[ExplanationOutput] = None
    is_fraud: bool = Field(..., description="True if decision is BLOCK")


class BatchResponse(BaseModel):
    results: List[PredictionResponse]
    total: int
    fraud_count: int


class HistoryRecord(BaseModel):
    id: int
    transaction_id: Optional[str]
    amount: float
    probability: float
    decision: str
    risk_level: str
    timestamp: str


class HistoryResponse(BaseModel):
    records: List[HistoryRecord]
    total: int
