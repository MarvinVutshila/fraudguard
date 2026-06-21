import os
import sys
import json
import logging
import pandas as pd
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from tqdm import tqdm

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
API_URL = os.getenv("API_URL", "https://fraudguard-434w.onrender.com/predict/batch")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 100))
CSV_FILE = os.getenv("CSV_FILE", "data/simulation.csv")
DATABASE_URL = os.getenv("DATABASE_URL")
STATE_KEY = "ingest_last_index"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Database state helpers (table created automatically)
# ------------------------------------------------------------------
def ensure_state_table():
    """Create the pipeline_state table if it doesn't exist."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("State table ensured.")

def load_state():
    """Load the last processed index from the database."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT value FROM pipeline_state WHERE key = %s;", (STATE_KEY,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"last_index": int(row[0])}
    return {"last_index": 0}

def save_state(state):
    """Save the last processed index to the database."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pipeline_state (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
        """,
        (STATE_KEY, str(state["last_index"]))
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.debug(f"State saved: last_index = {state['last_index']}")

# ------------------------------------------------------------------
# Main ingestion
# ------------------------------------------------------------------
def ingest_csv():
    ensure_state_table()

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
        for idx, row in chunk.iterrows():
            # Generate transaction_id if missing
            tx_id = row.get("transaction_id") if "transaction_id" in row and pd.notna(row["transaction_id"]) else None
            if tx_id is None:
                tx_id = f"AUTO-{i + idx}"
            tx = {
                "transaction_id": str(tx_id),
                "Amount": float(row["Amount"]),
                "Time": float(row.get("Time", 0)),
            }
            for v in range(1, 29):
                col = f"V{v}"
                tx[col] = float(row.get(col, 0.0))
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
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text[:200]}")
            save_state({"last_index": i})
            break

    logger.info(f"Run complete. Processed {processed} transactions today.")

if __name__ == "__main__":
    ingest_csv()
