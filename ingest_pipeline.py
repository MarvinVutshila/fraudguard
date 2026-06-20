#!/usr/bin/env python
"""
Data ingestion pipeline for FraudGuard.
Reads a CSV, splits into batches, and sends each batch to the /predict/batch API.
Resumable – saves progress in a state file.
"""

import os
import sys
import json
import time
import logging
import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Any
from tqdm import tqdm

# ------------------ CONFIGURATION (from environment or defaults) ------------------
API_URL = os.getenv("API_URL", "https://fraudguard-434w.onrender.com/predict/batch")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))          # number of transactions per batch
CSV_FILE = os.getenv("CSV_FILE", "data/test_transactions.csv")
STATE_FILE = os.getenv("STATE_FILE", "ingest_state.json")
LOG_FILE = os.getenv("LOG_FILE", "ingest_log.txt")
TIMEOUT = 60  # seconds per API call

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ------------------ STATE MANAGEMENT ------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_index": 0}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

# ------------------ MAIN INGESTION FUNCTION ------------------
def ingest_csv(file_path: str, batch_size: int = BATCH_SIZE):
    if not os.path.exists(file_path):
        logger.error(f"CSV file not found: {file_path}")
        return

    # Load the CSV
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        return

    # Ensure required columns exist
    required_cols = ["Amount"]
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Required column '{col}' not found in CSV.")
            return

    # Optional: generate transaction_id if missing
    if "transaction_id" not in df.columns:
        logger.info("'transaction_id' column not found – generating IDs.")
        df["transaction_id"] = [f"AUTO-{i}" for i in range(len(df))]

    total_rows = len(df)
    logger.info(f"Loaded {total_rows} rows from {file_path}")

    # Load progress state
    state = load_state()
    start_index = state.get("last_index", 0)
    if start_index >= total_rows:
        logger.info("All rows already processed. Nothing to do.")
        return

    logger.info(f"Starting ingestion from row {start_index}")

    # Process in batches
    for start in tqdm(range(start_index, total_rows, batch_size), desc="Processing batches"):
        end = min(start + batch_size, total_rows)
        chunk = df.iloc[start:end]

        # Build the payload (list of dicts)
        transactions = []
        for _, row in chunk.iterrows():
            tx = {
                "transaction_id": str(row.get("transaction_id", f"BATCH-{datetime.now().timestamp()}-{start}")),
                "Amount": float(row["Amount"]),
                "Time": float(row.get("Time", 0.0)),
            }
            # Add V1..V28
            for i in range(1, 29):
                col = f"V{i}"
                tx[col] = float(row.get(col, 0.0))
            transactions.append(tx)

        # Send to API
        try:
            response = requests.post(API_URL, json=transactions, timeout=TIMEOUT)
            response.raise_for_status()
            result = response.json()
            predictions = result.get("predictions", [])
            logger.info(f"Batch {start//batch_size + 1}: got {len(predictions)} predictions")
            # Optional: save predictions for later analysis
            # chunk['fraud_probability'] = predictions
            # chunk.to_csv(f"batch_results_{start}.csv", index=False)

        except requests.exceptions.Timeout:
            logger.error(f"Timeout processing batch at row {start}. Will retry later.")
            # Save state so we can resume from this batch
            save_state({"last_index": start})
            break
        except Exception as e:
            logger.error(f"Failed to process batch at row {start}: {e}")
            save_state({"last_index": start})
            break

        # Update state after successful batch
        save_state({"last_index": end})

    logger.info("Ingestion complete!")

if __name__ == "__main__":
    ingest_csv(CSV_FILE)
