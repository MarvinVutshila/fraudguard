import random
from fastapi import APIRouter, HTTPException
from fraud_detection.database.postgres_db import Database

router = APIRouter(prefix="/samples", tags=["samples"])

@router.get("/fraud")
async def get_fraud_sample():
    """Return a random fraudulent transaction from the database."""
    db = Database()
    # We'll use the existing transactions table for now, or a sample table
    # For simplicity, use the transactions table if you have stored some
    # But we need a reliable source – let's read from CSV if available
    import pandas as pd
    from fraud_detection.core.config import DATA_PATH
    try:
        df = pd.read_csv(DATA_PATH)
        frauds = df[df['Class'] == 1]
        if len(frauds) == 0:
            raise HTTPException(404, "No fraud samples found.")
        row = frauds.sample(n=1).iloc[0]
        result = {
            "transaction_id": f"FRAUD-{random.randint(1000,9999)}",
            "Amount": float(row["Amount"]),
            "Time": float(row["Time"]),
        }
        for i in range(1, 29):
            result[f"V{i}"] = float(row[f"V{i}"])
        return result
    except Exception as e:
        raise HTTPException(500, detail=f"Error reading dataset: {str(e)}")

@router.get("/normal")
async def get_normal_sample():
    """Return a random normal transaction from the database."""
    import pandas as pd
    from fraud_detection.core.config import DATA_PATH
    try:
        df = pd.read_csv(DATA_PATH)
        normals = df[df['Class'] == 0]
        if len(normals) == 0:
            raise HTTPException(404, "No normal samples found.")
        row = normals.sample(n=1).iloc[0]
        result = {
            "transaction_id": f"NORMAL-{random.randint(1000,9999)}",
            "Amount": float(row["Amount"]),
            "Time": float(row["Time"]),
        }
        for i in range(1, 29):
            result[f"V{i}"] = float(row[f"V{i}"])
        return result
    except Exception as e:
        raise HTTPException(500, detail=f"Error reading dataset: {str(e)}")