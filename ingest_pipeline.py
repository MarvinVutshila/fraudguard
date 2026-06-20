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
        logger.info("All done.")
        return
    for i in tqdm(range(start, total, BATCH_SIZE)):
        end = min(i + BATCH_SIZE, total)
        chunk = df.iloc[i:end]
        transactions = []
        for _, row in chunk.iterrows():
            tx = {
                "transaction_id": str(row.get("transaction_id", f"AUTO-{i}")),
                "Amount": float(row["Amount"]),
                "Time": float(row.get("Time", 0))
            }
            for v in range(1, 29):
                tx[f"V{v}"] = float(row.get(f"V{v}", 0.0))
            transactions.append(tx)
        try:
            r = requests.post(API_URL, json=transactions, timeout=60)
            r.raise_for_status()
            logger.info(f"Batch {i//BATCH_SIZE+1}: got {len(r.json().get('predictions', []))} predictions")
            save_state({"last_index": end})
        except Exception as e:
            logger.error(f"Failed at row {i}: {e}")
            save_state({"last_index": i})
            break
    logger.info("Done")

if __name__ == "__main__":
    ingest_csv()
