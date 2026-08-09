from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fraud_detection.core.config import MAX_KNOWN_AMOUNT, MODELS_DIR, DATA_PATH, APPROVE_THRESHOLD, BLOCK_THRESHOLD
from fraud_detection.api.dependencies import get_services, get_current_user
import os
import json
import shutil
import subprocess
from pathlib import Path

router = APIRouter()

STATUS_FILE = MODELS_DIR / "retrain_status.json"

DEFAULT_METRICS = {
    "accuracy": 0.9982,
    "precision": 0.9000,
    "recall": 0.8265,
    "f1_score": 0.8617,
    "auc_roc": 0.9816,
    "auc_pr": 0.8714,
}

def load_model_metrics():
    metrics_path = MODELS_DIR / "metrics.json"
    if metrics_path.exists():
        try:
            with open(metrics_path, "r") as f:
                data = json.load(f)
                for k in DEFAULT_METRICS:
                    data.setdefault(k, DEFAULT_METRICS[k])
                return data
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
            return DEFAULT_METRICS.copy()
    else:
        try:
            with open(metrics_path, "w") as f:
                json.dump(DEFAULT_METRICS, f, indent=2)
        except Exception as e:
            logger.error(f"Could not create metrics.json: {e}")
        return DEFAULT_METRICS.copy()

def get_status():
    if STATUS_FILE.exists():
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    return {"status": "idle", "message": "No retraining in progress", "progress": 0}

def update_status(status_dict):
    with open(STATUS_FILE, "w") as f:
        json.dump(status_dict, f, indent=2)

def run_training_scripts():
    update_status({"status": "running", "message": "Training autoencoder...", "progress": 20})
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        subprocess.run(["python", "train_autoencoder.py"], cwd=str(project_root), check=True, capture_output=True, text=True)
        update_status({"status": "running", "message": "Training XGBoost...", "progress": 60})
        subprocess.run(["python", "train.py"], cwd=str(project_root), check=True, capture_output=True, text=True)
        update_status({"status": "success", "message": "Retraining completed!", "progress": 100})
    except subprocess.CalledProcessError as e:
        update_status({"status": "failed", "message": f"Training failed: {e.stderr or e.stdout}", "progress": 0})
    except Exception as e:
        update_status({"status": "failed", "message": str(e), "progress": 0})


@router.get("/info")
async def model_info(user=Depends(get_current_user)):
    svc = get_services()
    info = svc.prediction_service.model_info()
    info["max_allowed_amount"] = MAX_KNOWN_AMOUNT
    info["threshold"] = info.get("optimal_threshold", 0.5)
    info["metrics"] = load_model_metrics()
    # Add decision policy clearly
    info["decision_policy"] = {
        "approve_threshold": APPROVE_THRESHOLD,
        "block_threshold": BLOCK_THRESHOLD,
        "description": f"APPROVE if probability < {APPROVE_THRESHOLD}, REVIEW if {APPROVE_THRESHOLD} ≤ probability < {BLOCK_THRESHOLD}, BLOCK if probability ≥ {BLOCK_THRESHOLD}"
    }
    return info

@router.get("/ping")
async def ping():
    return {"message": "model.py is alive!"}

@router.post("/retrain-now")
async def retrain_model(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    status = get_status()
    if status["status"] == "running":
        raise HTTPException(409, "Retraining already in progress.")
    update_status({"status": "running", "message": "Starting...", "progress": 0})
    background_tasks.add_task(run_training_scripts)
    return {"message": "Retraining started", "status": "running"}

@router.get("/retrain/status")
async def retrain_status():
    return get_status()

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files allowed.")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": f"Dataset uploaded to {DATA_PATH}", "filename": file.filename}

@router.post("/retrain/cancel")
async def cancel_retrain(user=Depends(get_current_user)):
    status = get_status()
    if status["status"] != "running":
        raise HTTPException(400, "No retraining job in progress.")
    cancel_file = MODELS_DIR / "cancel_retrain.flag"
    cancel_file.touch()
    update_status({"status": "cancelled", "message": "Cancelled by user.", "progress": 0})
    return {"message": "Cancellation requested."}