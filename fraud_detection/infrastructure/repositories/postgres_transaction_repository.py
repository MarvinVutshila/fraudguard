from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fraud_detection.database.postgres_db import Database

class StorageService:
    def __init__(self, db: Database):
        self.db = db

    def store(self, transaction_id: str, amount: float, probability: float,
              decision: str, risk_level: str, timestamp: Optional[datetime] = None) -> int:
        """
        Store a transaction. If timestamp is None, uses current UTC time.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        return self.db.insert_transaction(transaction_id, amount, probability,
                                          decision, risk_level, timestamp)

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_transaction(transaction_id)

    def get_transactions(self, limit: int = 100, offset: int = 0,
                         decision: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.db.get_transactions(limit, offset, decision)

    def count_transactions(self, decision_filter: Optional[str] = None) -> int:
        return self.db.count_transactions(decision_filter)

    # ---- Override methods ----
    def get_override(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single override record for a transaction."""
        return self.db.get_override(transaction_id)

    def set_override(self, transaction_id: str, original_decision: str,
                     new_decision: str, overridden_by: str, reason: str) -> None:
        """Save or update an override record."""
        self.db.set_override(transaction_id, original_decision, new_decision,
                             overridden_by, reason)

    def update_transaction_decision(self, transaction_id: str, decision: str, risk_level: str) -> None:
        """Update the decision and risk level of a transaction."""
        self.db.update_transaction_decision(transaction_id, decision, risk_level)

    # ---- For the Audit Log ----
    def get_all_overrides(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all override records for the audit log."""
        return self.db.get_all_overrides(limit)
