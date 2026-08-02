from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = PACKAGE_ROOT.parent

MODELS_DIR = BASE_DIR / "models_store"
DB_DSN = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/fraud")

# --- Add this line ---
DATA_PATH = BASE_DIR / "data" / "creditcard.csv"

API_KEY = os.getenv("API_KEY", "changeme")
API_KEY_NAME = "X-API-Key"
MAX_KNOWN_AMOUNT = 25691.16
APPROVE_THRESHOLD = float(os.getenv("APPROVE_THRESHOLD", "0.2"))
BLOCK_THRESHOLD   = float(os.getenv("BLOCK_THRESHOLD", "0.7"))
SHAP_TOP_N = 5
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")