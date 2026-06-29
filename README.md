# 🛡️ FraudGuard – AI‑Powered Transaction Monitoring

An end‑to‑end fraud detection platform with real‑time predictions, risk scoring, human override workflows, admin controls, and a beautiful React dashboard.  
Built with FastAPI (Python) + React (Vite) + PostgreSQL + ML (XGBoost/SHAP).

---

![Dashboard](dashboard.png)

## 📸 Screenshots

| | | |
|:-------------------------:|:-------------------------:|:-------------------------:|
| ![Admin Control Centre](AdminControlCentre.png) | ![Admin Control Centre 2](AdminControlCentre1.png) | ![Admin Control Centre 3](AdminControlCentre2.png) |
| **Admin Panel** | **User Management** | **System Settings** |
| ![Approval Audit](ApprovalAudit.png) | ![Batch Transaction Analysis](BatchTransactionAnalysis.png) | ![Human Approval](HumanApproval.png) |
| **Approval Audit Trail** | **Batch Analysis** | **Manual Review Queue** |
| ![Model Information](ModelInformation.png) | ![Single Transaction Predict](SingleTransactionPredict.png) | ![Transaction History](TransactionHistory.png) |
| **Model Performance** | **Single Prediction** | **Full Transaction History** |
| ![Login Page](loginPage.png) | ![Dashboard](dashboard.png) | |
| **Secure Login** | **Main Dashboard** | |

---

## 📑 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker](#docker)
- [Environment Variables](#-environment-variables)
- [API Endpoints](#-api-endpoints)
- [Machine Learning Pipeline](#-machine-learning-pipeline)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

- **Real‑time Fraud Detection** – Predict risk (LOW / MEDIUM / HIGH / CRITICAL) instantly with XGBoost model.
- **Human Override Workflow** – Analysts can approve / block / review transactions, with full audit trail.
- **Batch Analysis** – Upload CSV files to score hundreds of transactions at once.
- **Model Explainability** – SHAP explanations show why a transaction was flagged.
- **Admin Control Centre** – Manage users, roles, and system parameters.
- **Historical Dashboard** – Search, filter, and export the entire transaction history.
- **Approval Queue** – Pending reviews are clearly listed for analysts.
- **JWT Authentication** – Secure login with role‑based access (admin, analyst, viewer).
- **Auto‑generated Reports** – GitHub Actions cron job updates a live `reports.json` for external dashboards.

---

## 🧰 Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| **Backend**    | Python 3.11, FastAPI, SQLAlchemy    |
| **Frontend**   | React 18, Vite, CSS Modules         |
| **Database**   | PostgreSQL                          |
| **ML**         | XGBoost, SHAP, scikit‑learn          |
| **Infra**      | Docker, Render, GitHub Actions      |

---

## 🗂️ Project Structure
fraudguard/
├── frontend/ # React app (Vite)
│ ├── src/
│ │ ├── pages/ # Dashboard, History, Predict, Admin, etc.
│ │ ├── components/ # Navbar, Sidebar, StatCard, ThemeToggle
│ │ ├── context/ # ThemeContext
│ │ ├── services/ # api.js (Axios)
│ │ ├── App.jsx
│ │ └── main.jsx
│ ├── public/ # Static assets
│ ├── .env.production # Production env vars (no secrets)
│ └── package.json
│
├── fraud_detection/ # Backend (FastAPI)
│ ├── api/routes/ # Endpoints: auth, admin, transactions, model, etc.
│ ├── core/config.py # Settings and env vars
│ ├── database/ # Postgres connection and session
│ ├── ml/ # Model loader, inference, explainability
│ ├── schemas/ # Pydantic models
│ ├── services/ # Decision service, storage
│ └── main.py # FastAPI app entrypoint
│
├── models_store/ # Serialized ML models and artefacts
├── tests/ # Unit / integration tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── train.py # Model training script
├── ingest_pipeline.py # Data ingestion
├── run_report.py # GitHub Actions report generator
└── README.md

text

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+ and npm
- PostgreSQL (or use the Docker Compose file)
- (Optional) Docker

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/MarvinVutshila/fraudguard-reports.git
   cd fraudguard-reports
Backend setup

bash
cd fraud_detection
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Edit with your DATABASE_URL and other vars
python main.py            # API runs on http://localhost:8000
Frontend setup

bash
cd frontend
npm install
npm run dev               # Dev server on http://localhost:5173
Database & initial data

The first run will create tables automatically (if configured).

To seed test data, use python ingest_pipeline.py.

Docker
bash
docker-compose up --build
This starts the backend, frontend, and a PostgreSQL container.
Access the dashboard at http://localhost:3000.

⚙️ Environment Variables
All configuration is done through environment variables. Never commit real secrets to the repo!

Variable	Description	Default
DATABASE_URL	PostgreSQL connection string	Required
SECRET_KEY	JWT secret key	change-me-in-prod
MODEL_PATH	Path to saved model	models_store/
REFRESH_INTERVAL	Dashboard auto‑refresh (seconds)	30
VITE_API_BASE_URL	Backend URL for frontend	http://localhost:8000
Refer to .env.example for a full list.

📡 API Endpoints
Method	Route	Description
POST	/auth/login	User login (returns JWT)
POST	/transactions/predict	Predict single transaction
POST	/transactions/batch	Batch prediction (CSV upload)
GET	/transactions	List / filter transactions
POST	/admin/override	Override a transaction decision
GET	/model/info	Model metrics and metadata
GET	/health	Health check
All protected endpoints require Authorization: Bearer <token>.

🤖 Machine Learning Pipeline
Training: train.py uses historical data (test_transactions.csv) to train an XGBoost classifier with hyperparameter tuning.

Feature Engineering: Handles amount, time, user behaviour, etc. (see ml/feature_engineering.py).

Explainability: SHAP values are generated for every prediction to show why a transaction is risky.

Model Storage: Trained model and preprocessors are saved in models_store/ and loaded at runtime.

🌍 Deployment
Render (Backend + Frontend)
Connect your GitHub repo.

Create a Web Service for the backend (Dockerfile) and a Static Site for the frontend (frontend/dist).

Set all environment variables in the Render dashboard.

The render.yaml blueprint can automate this.

GitHub Pages (Dashboard only)
The separate fraudguard-reports repo serves a live report dashboard that consumes data/reports.json, updated every hour by GitHub Actions.

🤝 Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you’d like to change.
Please ensure that all secrets are removed before pushing.

📝 License
MIT © Marvin Vutshila
