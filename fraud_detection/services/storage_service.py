from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fraud_detection.database.postgres_db import Database

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, db: Database):
        self.db = db

    # ---- Legacy / Compatibility ----
    def store(self, transaction_id, amount, probability, decision, risk_level):
        """Store a single transaction (called by prediction_service)."""
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

    # ---- Core transaction methods (required by routes) ----
    def get_transactions(self, limit: int = 50, offset: int = 0,
                         decision: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return list of transactions (dicts) with pagination and optional decision filter."""
        return self.db.get_transactions(limit, offset, decision)

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single transaction by its transaction_id."""
        return self.db.get_transaction(transaction_id)

    def count_transactions(self, decision: Optional[str] = None) -> int:
        """Count total transactions, optionally filtered by decision."""
        return self.db.count_transactions(decision)

    # ---- Overrides ----
    def get_override(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Fetch override record for a transaction."""
        return self.db.get_override(transaction_id)

    def set_override(self, transaction_id: str, original_decision: str,
                     new_decision: str, overridden_by: str, reason: str) -> None:
        """Store or update an override."""
        self.db.set_override(transaction_id, original_decision, new_decision,
                             overridden_by, reason)

    def get_all_overrides(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent overrides with join on transactions."""
        return self.db.get_all_overrides(limit)

    # ---- Deduplication ----
    def create_transaction_if_not_exists(self, transaction_id: str, amount: float,
                                         probability: float, decision: str,
                                         risk_level: str,
                                         features: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Insert a transaction, skipping it if the transaction_id already exists.
        Returns the new row id, or None if skipped.
        """
        return self.db.insert_transaction_if_not_exists(
            transaction_id, amount, probability, decision, risk_level,
            timestamp=datetime.utcnow(), features=features
        )

    # ---- Review Queue ----
    def count_pending_reviews(self) -> int:
        """
        Return the number of REVIEW transactions that have NOT been overridden.
        Used for the approval queue badge.
        """
        return self.db.get_pending_review_count()