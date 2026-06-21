from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fraud_detection.database.postgres_db import Database

class StorageService:
    def __init__(self, db: Database):
        self.db = db

    def store(self, transaction_id: str, amount: float, probability: float,
              decision: str, risk_level: str, timestamp: Optional[datetime] = None) -> int:
        """
        Store a transaction in the database.
        If timestamp is not provided, uses current UTC time.
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

    def set_override(self, transaction_id: str, original_decision: str,
                     new_decision: str, overridden_by: str, reason: str) -> None:
        self.db.set_override(transaction_id, original_decision, new_decision,
                             overridden_by, reason)

    def count_transactions(self, decision_filter: Optional[str] = None) -> int:
        return self.db.count_transactions(decision_filter)

    def update_transaction_decision(self, transaction_id: str, decision: str, risk_level: str) -> None:
        self.db.update_transaction_decision(transaction_id, decision, risk_level)
