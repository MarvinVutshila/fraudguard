#!/usr/bin/env python3
"""
train_autoencoder.py - Unsupervised Anomaly Detector (RESOURCE SAFE)
====================================================================
- Uses VECTORIZED pandas operations (NO row-by-row loops)
- Adds memory cleanup (gc.collect) and sleep pauses between heavy stages
- Limits PyTorch threads to prevent CPU hogging
- Trains only on legitimate transactions (Class=0)
"""
import os
import time
import gc
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")

# ---------- Limit PyTorch CPU threads to prevent 100% CPU spike ----------
torch.set_num_threads(1)  # Use only 1 CPU thread for training
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH = "data/creditcard.csv"
MODELS_DIR = "models_store"
RANDOM_STATE = 42
EPOCHS = 40          # Reduced from 50 to save time (40 is enough)
BATCH_SIZE = 256     # Kept moderate to save RAM

# -------------- Autoencoder Architecture --------------
class Autoencoder(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16)  # Bottleneck
        )
        self.decoder = nn.Sequential(
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


def vectorized_feature_engineering(df):
    """
    VECTORIZED feature engineering (EXACTLY matches train.py).
    NO row-by-row loops - operates on entire DataFrame at once.
    """
    logger.info("Applying vectorized feature engineering...")
    df = df.copy()
    
    # Cyclical time encoding
    df["Hour"] = (df["Time"] // 3600) % 24
    df["Hour_sin"] = np.sin(2 * np.pi * df["Hour"] / 24)
    df["Hour_cos"] = np.cos(2 * np.pi * df["Hour"] / 24)
    
    # Amount transformations
    df["Log_Amount"] = np.log1p(df["Amount"])
    
    # Amount quantile bins (same as train.py)
    amount_bins = np.quantile(df["Amount"], np.linspace(0, 1, 11))
    df["Amount_Q"] = pd.cut(df["Amount"], bins=amount_bins, labels=False).fillna(0).astype(float)
    
    # Define final feature columns
    feature_cols = [f"V{i}" for i in range(1, 29)] + [
        "Hour", "Hour_sin", "Hour_cos", "Log_Amount", "Amount_Q"
    ]
    
    # Return only the features as a DataFrame
    return df[feature_cols], amount_bins, feature_cols


def main():
    start_time = time.time()
    logger.info("=== AUTOENCODER TRAINING (Resource Safe Mode) ===")

    # ---------- 1. LOAD DATA ----------
    logger.info(f"Loading dataset from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    logger.info(f"Shape: {df.shape} (Memory: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB)")
    y = df['Class'].values  # Extract target BEFORE we drop columns
    
    # GIVE CPU A BREATHER
    time.sleep(2)
    gc.collect()

    # ---------- 2. VECTORIZED FEATURE ENGINEERING ----------
    X, amount_bins, feature_cols = vectorized_feature_engineering(df)
    
    # FREE the original df to save memory
    del df
    gc.collect()
    time.sleep(2)  # Let the system settle

    logger.info(f"Feature matrix shape: {X.shape}")
    logger.info(f"Features: {feature_cols}")

    # ---------- 3. SCALE THE DATA ----------
    logger.info("Fitting StandardScaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    logger.info("Scaling complete.")

    # FREE the raw X to save memory
    del X
    gc.collect()
    time.sleep(2)

    # Save scaler immediately
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(scaler, f"{MODELS_DIR}/autoencoder_scaler.pkl")
    logger.info(f"Scaler saved to {MODELS_DIR}/autoencoder_scaler.pkl")

    # ---------- 4. SUBSET TO LEGITIMATE TRANSACTIONS (Class == 0) ----------
    X_train = X_scaled[y == 0]
    logger.info(f"Training on {len(X_train):,} legitimate transactions ({(len(X_train)/len(y)*100):.1f}% of data).")

    # FREE the full scaled array to save memory
    del X_scaled, y
    gc.collect()
    time.sleep(2)

    # ---------- 5. PYTORCH TRAINING ----------
    dataset = torch.utils.data.DataLoader(
        torch.tensor(X_train, dtype=torch.float32),
        batch_size=BATCH_SIZE,
        shuffle=True,
        pin_memory=False  # Keep it simple for CPU
    )

    model = Autoencoder(input_dim=X_train.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    # FREE the numpy array now that it's in PyTorch DataLoader
    del X_train
    gc.collect()

    logger.info(f"Starting Autoencoder training for {EPOCHS} epochs...")
    logger.info("(This may take 3-5 minutes. The system will pause briefly between epochs to cool down.)")

    for epoch in range(EPOCHS):
        epoch_loss = 0.0
        batch_count = 0
        
        for batch in dataset:
            optimizer.zero_grad()
            reconstruction = model(batch)
            loss = loss_fn(reconstruction, batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            batch_count += 1
        
        avg_loss = epoch_loss / batch_count
        
        # Log every 5 epochs to reduce console spam
        if epoch % 5 == 0 or epoch == EPOCHS - 1:
            logger.info(f"Epoch {epoch+1:3d}/{EPOCHS} | Avg Loss: {avg_loss:.8f}")
            # Give CPU a micro-break after heavy epochs
            if epoch % 10 == 0:
                time.sleep(1)
                gc.collect()

    # ---------- 6. SAVE ARTEFACTS ----------
    logger.info("Saving artefacts...")
    torch.save(model.state_dict(), f"{MODELS_DIR}/autoencoder.pth")
    joblib.dump(feature_cols, f"{MODELS_DIR}/autoencoder_features.pkl")
    joblib.dump(amount_bins, f"{MODELS_DIR}/autoencoder_amount_bins.pkl")

    logger.info(f"✅ All artefacts saved to {MODELS_DIR}/")
    logger.info(f"   - autoencoder.pth")
    logger.info(f"   - autoencoder_scaler.pkl")
    logger.info(f"   - autoencoder_features.pkl")
    logger.info(f"   - autoencoder_amount_bins.pkl")

    elapsed = time.time() - start_time
    logger.info(f"Training completed in {elapsed/60:.2f} minutes.")

if __name__ == "__main__":
    main()