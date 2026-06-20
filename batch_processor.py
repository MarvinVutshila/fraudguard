import pandas as pd
import requests
import json
import os
import time
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==================== CONFIGURATION ====================
API_URL = "https://fraud-detection-i9wm.onrender.com/predict"
SIMULATION_FILE = "data/simulation.csv"
STATE_FILE = "state.json"
RESULTS_FILE = "results.csv"
BATCH_SIZE = 50
REQUEST_TIMEOUT = 60                    # increased to 60 seconds
MAX_ATTEMPTS = 3                        # retry on timeout
RETRY_DELAY = 5                         # seconds between retries
RESULT_BUFFER_LIMIT = 100

# ==================== SESSION WITH RETRIES (for HTTP errors) ====================
def create_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# ==================== STATE MANAGEMENT ====================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"index": 0}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def save_results_batch(results):
    if not results:
        return
    df = pd.DataFrame(results)
    if not os.path.exists(RESULTS_FILE):
        df.to_csv(RESULTS_FILE, index=False)
    else:
        df.to_csv(RESULTS_FILE, mode="a", header=False, index=False)

# ==================== MAIN ====================
def main():
    if not os.path.exists(SIMULATION_FILE):
        print(f"Error: {SIMULATION_FILE} not found")
        return

    df = pd.read_csv(SIMULATION_FILE)
    total = len(df)
    print(f"Loaded {total} transactions")

    session = create_session()
    state = load_state()
    start = state["index"]

    if start >= total:
        print("All transactions already processed.")
        return

    end = min(start + BATCH_SIZE, total)
    batch = df.iloc[start:end]
    print(f"Processing rows {start}–{end-1} (of {total})")

    results_buffer = []
    # We'll update state after each transaction to avoid re‑processing many if interrupted
    current_index = start

    for idx, row in batch.iterrows():
        payload = row.drop("Class").to_dict() if "Class" in df.columns else row.to_dict()

        # Retry loop for timeouts
        success = False
        for attempt in range(MAX_ATTEMPTS):
            try:
                resp = session.post(API_URL, json=payload, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                success = True
                break
            except requests.exceptions.Timeout:
                print(f"  Timeout on {idx} (attempt {attempt+1}/{MAX_ATTEMPTS})")
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  Failed after {MAX_ATTEMPTS} attempts, skipping transaction {idx}")
            except Exception as e:
                print(f"  Error on {idx}: {e}")
                break   # don't retry on non‑timeout errors

        if not success:
            continue

        is_fraud = data.get("is_fraud")
        predicted_class = 1 if is_fraud else 0
        probability = data.get("fraud_probability")
        decision = data.get("decision")
        risk_level = data.get("risk_level")

        results_buffer.append({
            "transaction_id": idx,
            "prediction_time": datetime.now(timezone.utc).isoformat(),
            "predicted_class": predicted_class,
            "probability": probability,
            "decision": decision,
            "risk_level": risk_level,
            "raw_response": json.dumps(data)
        })

        print(f"  {idx}: fraud={is_fraud}, prob={probability:.4f}, decision={decision}")

        # Save state after each transaction (optional but safer)
        current_index = idx + 1
        save_state({"index": current_index})

        if len(results_buffer) >= RESULT_BUFFER_LIMIT:
            save_results_batch(results_buffer)
            results_buffer = []

    # Final flush
    if results_buffer:
        save_results_batch(results_buffer)

    # Update state to end of batch (if we didn't already)
    final_index = max(current_index, end)
    save_state({"index": final_index})
    print(f"Batch done. Next index = {final_index}")

if __name__ == "__main__":
    main()