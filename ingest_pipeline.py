import os
import sys
import time
import json
import logging
import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Any
from tqdm import tqdm

# ------------------ CONFIGURATION (from env or defaults) ------------------
API_URL = os.getenv("API_URL", "https://fraudguard-434w.onrender.com/predict/batch")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
CSV_FILE = os.getenv("CSV_FILE", "data/test_transactions.csv")
STATE_FILE = os.getenv("STATE_FILE", "ingest_state.json")
LOG_FILE = os.getenv("LOG_FILE", "ingest_log.txt")

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

# ------------------ MAIN PIPELINE ------------------
def ingest_csv(file_path: str, batch_size: int = BATCH_SIZE):
    if not os.path.exists(file_path):
        logger.error(f"CSV file not found: {file_path}")
        return

    df = pd.read_csv(file_path)
    total_rows = len(df)
    logger.info(f"Loaded {total_rows} rows from {file_path}")

    state = load_state()
    start_index = state.get("last_index", 0)
    if start_index >= total_rows:
        logger.info("All rows already processed. Nothing to do.")
        return

    logger.info(f"Starting ingestion from row {start_index}")

    for start in tqdm(range(start_index, total_rows, batch_size), desc="Processing batches"):
        end = min(start + batch_size, total_rows)
        chunk = df.iloc[start:end]

        transactions = []
        for _, row in chunk.iterrows():
            tx = {
                "transaction_id": row.get("transaction_id", f"BATCH-{datetime.now().timestamp()}-{start}"),
                "Amount": float(row["Amount"]),
                "Time": float(row.get("Time", 0)),
            }
            for i in range(1, 29):
                col = f"V{i}"
                tx[col] = float(row.get(col, 0.0))
            transactions.append(tx)

        try:
            response = requests.post(API_URL, json=transactions, timeout=60)
            response.raise_for_status()
            result = response.json()
            predictions = result.get("predictions", [])
            logger.info(f"Batch {start//batch_size + 1}: got {len(predictions)} predictions")
            # Optionally save predictions to file
            # chunk['fraud_probability'] = predictions
            # chunk.to_csv(f"batch_results_{start}.csv", index=False)
        except Exception as e:
            logger.error(f"Failed to process batch at row {start}: {e}")
            save_state({"last_index": start})
            break

        save_state({"last_index": end})

    logger.info("Ingestion complete!")

if __name__ == "__main__":
    ingest_csv(CSV_FILE)
