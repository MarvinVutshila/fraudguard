import os
import sys
import json
import logging
import pandas as pd
import requests
from datetime import datetime
from tqdm import tqdm

API_URL = os.getenv("API_URL", "https://fraudguard-434w.onrender.com/predict/batch")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 100))
CSV_FILE = os.getenv("CSV_FILE", "data/simulation.csv")
STATE_FILE = "ingest_state.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_index": 0}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def ingest_csv():
    if not os.path.exists(CSV_FILE):
        logger.error(f"CSV not found: {CSV_FILE}")
        return
    df = pd.read_csv(CSV_FILE)
    total = len(df)
    logger.info(f"Loaded {total} rows")

    state = load_state()
    start = state.get("last_index", 0)
    if start >= total:
        logger.info("All rows already processed. Nothing to do.")
        return

    end_target = min(start + DAILY_LIMIT, total)
    logger.info(f"Processing rows {start} to {end_target-1} (limit: {DAILY_LIMIT})")

    processed = 0
    for i in tqdm(range(start, total, BATCH_SIZE)):
        end = min(i + BATCH_SIZE, total)
        if processed >= DAILY_LIMIT:
            logger.info(f"Reached daily limit of {DAILY_LIMIT} transactions. Stopping for today.")
            break

        chunk = df.iloc[i:end]
        transactions = []
        for _, row in chunk.iterrows():
            tx = {
                # 🔥 FIXED: Use lowercase 'amount' to match backend!
                "amount": float(row["Amount"]),    # <-- Fixed here
                "Time": float(row.get("Time", 0)),
            }
            # Add transaction_id if available, else let backend generate
            if "transaction_id" in row:
                tx["transaction_id"] = str(row["transaction_id"])
            # Add V1..V28
            for v in range(1, 29):
                tx[f"V{v}"] = float(row.get(f"V{v}", 0.0))
            transactions.append(tx)

        try:
            r = requests.post(API_URL, json=transactions, timeout=60)
            r.raise_for_status()
            predictions = r.json().get('predictions', [])
            logger.info(f"Batch {i//BATCH_SIZE+1}: got {len(predictions)} predictions")
            save_state({"last_index": end})
            processed += len(chunk)
        except Exception as e:
            logger.error(f"Failed at row {i}: {e}")
            # Log the response body if available for debugging
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text[:200]}")
            save_state({"last_index": i})
            break

    logger.info(f"Run complete. Processed {processed} transactions today.")

if __name__ == "__main__":
    ingest_csv()
