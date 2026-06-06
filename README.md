# 🛡️ Fraud Detection System – Production ML + API + Dashboard

End‑to‑end fraud detection using **XGBoost** (trained on the Kaggle Credit Card Fraud dataset), served via a modular **FastAPI** backend, with an **HTML/JS dashboard** and **PostgreSQL** for history. Fully containerised and deployable for free on Render + Neon + Netlify (or Vercel).

## 🎯 Real System Architecture (current)

```mermaid
graph LR
    User["User / CSV"] --> Dashboard["HTML/JS Dashboard"]
    Dashboard --> API["FastAPI Backend"]
    API --> DB[("PostgreSQL / Neon")]
    API --> Model["Trained XGBoost Model"]
    Model --> SHAP["SHAP Explanations"]
    DB --> Dashboard

📁 Project Structure (after refactor)
text
fraud_detection/
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── main.py                         # FastAPI entry point (root endpoint added)
├── train.py                        # training script (keep for retraining)
├── evaluate_mode.py                # evaluation script
├── live_stream_review_focused.py   # optional streaming review
├── tests/
│   ├── __init__.py
│   └── test_connection.py          # DB connection test
├── frontend/                       # static dashboard
│   ├── index.html                  # modern HTML/JS dashboard
│   └── Marvin.jpg
├── models_store/                   # trained artefacts (excluded from git)
│   ├── best_model.pkl
│   ├── scaler.pkl
│   ├── amount_bins.pkl
│   ├── feature_names.pkl
│   └── optimal_threshold.pkl
└── fraud_detection/                # main package – modular layers
    ├── api/
    │   ├── dependencies.py
    │   ├── auth.py
    │   └── routes/                 # split route files
    │       ├── health.py
    │       ├── model.py
    │       ├── predictions.py
    │       ├── transactions.py
    │       ├── history.py
    │       ├── ingest.py
    │       └── auth.py
    ├── application/
    │   └── services/
    │       ├── prediction_service.py
    │       └── decision_service.py
    ├── infrastructure/
    │   ├── database/               # session, connection pool
    │   └── repositories/           # postgres_transaction_repository.py
    ├── ml/
    │   ├── feature_engineering.py
    │   └── inference/
    │       ├── model_loader.py
    │       └── explainability.py
    ├── schemas/                    # Pydantic models
    ├── core/                       # config
    └── utils/                      # legacy helpers (keep for reference)
🧠 Model Performance (on test set)
Metric	Value
ROC‑AUC	0.9816
F1 (threshold 0.9244)	0.8677
Recall at threshold 0.7	85.7%
False positive rate (0.7)	0.07%
→ Ready for low‑false‑alarm fraud detection.

🚀 Free Deployment Options
We use three free services:

Component	Platform	Free limits
API	Render	750 hours/month, spins down after 15 min idle
Database	Neon	0.5 GB storage, serverless, scales to zero
Dashboard	Netlify / Vercel	Unlimited static hosting
Step 1 – Neon Database
Sign up at neon.tech (GitHub login).

Create a project → copy the connection string (postgresql://…).

Keep it – you'll need it for Render.

Step 2 – Deploy FastAPI on Render
Push your code to GitHub (e.g., MarvinVutshila/fraud-detection).

Log into Render → New Web Service → connect repo.

Use these settings:

Field	Value
Name	fraud-detection-api
Environment	Python
Build Command	python -m pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
Start Command	uvicorn main:app --host 0.0.0.0 --port 10000
Instance Type	Free
Add Environment Variables (secrets):

Key	Value
DATABASE_URL	(the Neon connection string)
JWT_SECRET_KEY	a strong random string (generate one)
STREAM_PASSWORD	(optional, for live stream)
API_KEY	changeme (or a random string)
Click Create Web Service.
✅ After ~3‑5 minutes, your API is live at https://fraud-detection-api.onrender.com.
Test: https://fraud-detection-api.onrender.com/health → {"status":"ok"}

Step 3 – Deploy the HTML/JS Dashboard on Netlify (or Vercel)
The dashboard is a static site in the frontend/ folder.

Push it to the same GitHub repo.

On Netlify:

Drag & drop the frontend/ folder, or connect the repo and set Publish directory to frontend.

The dashboard will call your Render API URL.
In frontend/index.html, update API_BASE to your Render URL (or use a config file).

Alternatively, serve the dashboard directly from the FastAPI app (add StaticFiles middleware) – then you only deploy the API.

🧪 Testing the Live System
Open the dashboard URL.

Upload a CSV with columns: Time, Amount, V1, V2, …, V28 (exactly as the original dataset).

The dashboard sends a batch request to the API.

The API returns fraud probability, decision (APPROVE / REVIEW / BLOCK), risk level, and SHAP explanations.

Results are stored in Neon and displayed in the dashboard's history.

🔁 Updating
API: push changes to GitHub → Render auto‑re deploys.

Database: manage via Neon console.

Dashboard: push changes to GitHub → Netlify auto‑re deploys.

⚠️ Important Notes for Production
Cold starts: Render spins down after 15 minutes – the first request may take 30‑50 seconds.

Never use Render's free PostgreSQL – it expires after 30 days. Always use Neon or Supabase.

The model expects all V1‑V28 features – your CSV must include them (they are PCA components from the original dataset).
In a real‑world deployment you would replace V1…V28 with actual banking features; this is a proof‑of‑concept using the Kaggle dataset.

🛠 Troubleshooting
Problem	Solution
Build fails on Render	Ensure runtime.txt contains python-3.11.0 (if used) and build command upgrades pip/setuptools.
ModuleNotFoundError	Verify all dependencies are in requirements.txt (especially psycopg2-binary, fastapi, uvicorn).
Database connection refused	Check DATABASE_URL secret; Neon database may be paused → resume it.
API returns 500 on /predict	Look at Render logs – likely a missing model file or column name mismatch.
Dashboard cannot reach API	Update the dashboard’s API_BASE to the Render URL and ensure CORS is allowed (already enabled in main.py).
📜 License
Educational / research use only. Not for live financial systems without proper validation.

👨‍💻 Author
Marvin – Data Science & AI Engineer

Installation (local development)
bash
# Clone the repo
git clone https://github.com/MarvinVutshila/fraud-detection.git
cd fraud-detection

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
.\venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database URL and secrets

# Run the API
python main.py
Now open http://localhost:8000 – you will see the API root endpoint with links to /docs (Swagger UI).
The static dashboard (if served via the API) would be at http://localhost:8000/static (optional).

