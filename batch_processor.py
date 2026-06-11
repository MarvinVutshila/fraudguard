import os
import json
import logging
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

# -------------------------------
# Configuration (env variables)
# -------------------------------
API_URL = os.environ.get("API_URL", "https://your-api.onrender.com/predict")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://user:pass@host:5432/fraud_sim"
)
SIMULATION_FILE = os.environ.get("SIMULATION_FILE", "data/simulation.csv")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 50))
LOOP_WHEN_DONE = os.environ.get("LOOP_WHEN_DONE", "false").lower() == "true"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("fraud_sim")

# -------------------------------
# Database setup
# -------------------------------
Base = declarative_base()

class SimulationState(Base):
    __tablename__ = "simulation_state"
    id = Column(Integer, primary_key=True)
    last_index = Column(Integer, nullable=False, default=0)

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, index=True)         # row index in csv
    prediction_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    predicted_class = Column(Integer, nullable=True)     # 0 or 1
    probability = Column(Float, nullable=True)
    raw_response = Column(JSON, nullable=True)

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# -------------------------------
# State helpers
# -------------------------------
def get_state():
    """Return the last processed index (0 if never run)."""
    with SessionLocal() as session:
        state = session.query(SimulationState).first()
        if state is None:
            state = SimulationState(last_index=0)
            session.add(state)
            session.commit()
            return 0
        return state.last_index

def set_state(index):
    """Persist the new last processed index."""
    with SessionLocal() as session:
        state = session.query(SimulationState).first()
        if state is None:
            state = SimulationState(last_index=index)
            session.add(state)
        else:
            state.last_index = index
        session.commit()

# -------------------------------
# Prediction storage
# -------------------------------
def save_prediction(transaction_id, predicted_class, probability, raw_response):
    """Insert one prediction record."""
    with SessionLocal() as session:
        pred = Prediction(
            transaction_id=transaction_id,
            predicted_class=predicted_class,
            probability=probability,
            raw_response=raw_response,
        )
        session.add(pred)
        session.commit()
        logger.debug(f"Saved prediction for transaction {transaction_id}")

# -------------------------------
# Main simulation logic
# -------------------------------
def run_batch():
    df = pd.read_csv(SIMULATION_FILE)
    total_rows = len(df)

    # Get starting point
    start = get_state()
    if start >= total_rows:
        if LOOP_WHEN_DONE:
            logger.info("Data exhausted, resetting to start (LOOP_WHEN_DONE=true).")
            start = 0
        else:
            logger.info("All data has been processed. Exiting.")
            return

    end = min(start + BATCH_SIZE, total_rows)
    batch = df.iloc[start:end]
    logger.info(f"Processing rows {start} → {end} of {total_rows}")

    # Process each transaction
    for idx, row in batch.iterrows():
        transaction_id = int(idx)               # original DataFrame index
        # Remove the Class column before sending
        payload = row.drop("Class").to_dict()

        try:
            resp = requests.post(API_URL, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed for transaction {transaction_id}: {e}")
            # Optional: retry logic or dead‑letter queue
            continue

        # Parse API response (adjust to your actual response structure)
        predicted_class = data.get("prediction")        # 0 or 1
        probability = data.get("probability", None)

        save_prediction(
            transaction_id=transaction_id,
            predicted_class=predicted_class,
            probability=probability,
            raw_response=data,
        )
        logger.info(f"Transaction {transaction_id} → class={predicted_class}, prob={probability}")

    # Update state *after* successful batch
    set_state(end)
    logger.info(f"Batch completed. State updated to index {end}")

if __name__ == "__main__":
    # Optional CLI flag to reset state (run manually)
    import sys
    if "--reset" in sys.argv:
        logger.warning("Resetting simulation state to 0.")
        set_state(0)
    else:
        run_batch()
