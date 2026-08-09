import os
import logging
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MODELS_DIR = Path(os.getenv("MODELS_DIR", "/home/ubuntu/fraudguard/models_store"))
APPROVE_THRESHOLD = float(os.getenv("APPROVE_THRESHOLD", "0.20"))
BLOCK_THRESHOLD = float(os.getenv("BLOCK_THRESHOLD", "0.85"))

# Use the Docker container's credentials
DB_DSN = "postgresql://marvin:smygsSmEKygWoDEQXrqYNws49pPRbsfO@127.0.0.1:5432/fraud"

MAX_KNOWN_AMOUNT = float(os.getenv("MAX_KNOWN_AMOUNT", "1000000.0"))
DATA_PATH = os.getenv("DATA_PATH", "data/transactions.csv")
SHAP_TOP_N = int(os.getenv("SHAP_TOP_N", "10"))

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_this_in_production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "marvin@support.co.za")
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+27 82 123 4567")
