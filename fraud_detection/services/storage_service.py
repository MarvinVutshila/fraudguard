# fraud_detection/services/storage_service.py
from __future__ import annotations
import logging
from typing import List, Optional

from fraud_detection.database.postgres_db import Database

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, db: Database):
        self.db = db

    def store(self, transaction_id, amount, probability, decision, risk_level):
        """Store a single transaction (called by prediction_service)."""
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
        """Alias for compatibility with old history endpoint."""
        return self.db.fetch_history(limit, offset, decision)

    # ===== New methods required by routes.py =====
    def get_transactions(self, limit: int = 50, offset: int = 0, decision: Optional[str] = None) -> List[dict]:
        """Return list of transactions (dicts) with pagination and optional decision filter."""
        return self.db.get_transactions(limit, offset, decision)

    def get_transaction(self, transaction_id: str) -> Optional[dict]:
        """Fetch a single transaction by its transaction_id."""
        return self.db.get_transaction(transaction_id)

    def get_override(self, transaction_id: str) -> Optional[dict]:
        """Fetch override record for a transaction."""
        return self.db.get_override(transaction_id)

    def set_override(self, transaction_id: str, original_decision: str, new_decision: str,
                     overridden_by: str, reason: str) -> None:
        """Store or update an override."""
        self.db.set_override(transaction_id, original_decision, new_decision, overridden_by, reason)