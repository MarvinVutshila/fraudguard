from __future__ import annotations
import logging
from typing import List, Optional

from fraud_detection.database.postgres_db import Database

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, db: Database):
        self.db = db

    def store(self, transaction_id, amount, probability, decision, risk_level):
        from datetime import datetime
        timestamp = datetime.utcnow()
        return self.db.insert_transaction(
            transaction_id=transaction_id,
            amount=amount,
            probability=probability,
            decision=decision,
            risk_level=risk_level,
            timestamp=timestamp
        )

    def get_recent(self, limit: int = 100, offset: int = 0, decision: Optional[str] = None):
        return self.db.fetch_history(limit, offset, decision)

    def get_transactions(self, limit: int = 50, offset: int = 0, decision: Optional[str] = None) -> List[dict]:
        return self.db.get_transactions(limit, offset, decision)

    def get_transaction(self, transaction_id: str) -> Optional[dict]:
        return self.db.get_transaction(transaction_id)

    def get_override(self, transaction_id: str) -> Optional[dict]:
        return self.db.get_override(transaction_id)

    # ✅ Corrected: 5 parameters (no new_probability)
    def set_override(self, transaction_id: str, original_decision: str, new_decision: str,
                     overridden_by: str, reason: str) -> None:
        self.db.set_override(transaction_id, original_decision, new_decision, overridden_by, reason)

    # ✅ Corrected: accepts new_probability as optional 4th parameter
    def update_transaction_decision(self, transaction_id: str, new_decision: str, new_risk: str, new_probability: Optional[float] = None) -> None:
        self.db.update_transaction_decision(transaction_id, new_decision, new_risk, new_probability)
