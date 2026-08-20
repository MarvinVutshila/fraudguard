# 🛡️ FraudGuard – AI-Powered Fraud Detection Platform

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![React](https://img.shields.io/badge/React-Frontend-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![XGBoost](https://img.shields.io/badge/XGBoost-Machine_Learning-orange)
![Docker](https://img.shields.io/badge/Docker-Container-blue)
![AWS](https://img.shields.io/badge/AWS-Glue_Athena_S3-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-Analytics-red)

> An end‑to‑end AI fraud detection platform built with Machine Learning, FastAPI, React, PostgreSQL, and human‑review workflows, deployed on AWS with automated ETL and Airflow pipelines.

---

## 🌐 Live Demos

- 🚀 **Main Application**: [https://fraudguard-434w.onrender.com/login](https://fraudguard-434w.onrender.com/login)  
- 📄 **Analytics Dashboard (Streamlit)**: [https://marvinvutshila.github.io/fraudguard-reports/](https://marvinvutshila.github.io/fraudguard-reports/)

---

## 🚀 Overview

FraudGuard is a banking fraud detection system that uses an **XGBoost machine learning model** to analyse transactions and classify them as:

- ✅ **Approved** – low risk, automatically passed.
- ⚖️ **Human Review** – suspicious, requires analyst decision.
- 🚫 **Blocked** – high risk, prevented.

The platform provides:

- Real‑time transaction monitoring with live feeds.
- Single‑transaction & batch CSV prediction.
- Human review workflow with full audit trails.
- Admin control centre with user management and 2FA.
- ML model insights (feature importance, metrics, auto‑retraining).
- **AWS‑backed data pipeline** (Glue, Athena, S3, Airflow).
- **Streamlit & Superset** analytics dashboards for deep insights.

---

## ✨ Features

### 🤖 Machine Learning
- XGBoost fraud detection model (99.82% accuracy).
- Feature engineering with 34 engineered transaction features.
- Fraud probability scoring and risk classification.
- On‑demand model retraining and evaluation.
- Explainable AI with SHAP feature importance.

### 📡 Real‑Time Monitoring
- Live transaction feed with auto‑refresh.
- Approval queue with pending reviews.
- Dashboard metrics (total transactions, blocked, pending reviews).
- Real‑time probability trend graphs.

### ⚖️ Human Review Workflow
- Suspicious transaction queue.
- Approve or block transactions with comments.
- Full audit history of all overrides.
- Analyst‑friendly UI with AI decision support.

### 📁 Batch Processing
- Drag‑and‑drop CSV uploads for bulk scoring.
- Automatic fraud prediction and decision generation.

### 🔐 Security
- JWT authentication with role‑based access (Admin / Analyst).
- Password hashing and 2FA setup (QR code).
- Protected admin routes and detailed audit logging.

### 📊 Analytics & Reporting
- **Streamlit Command Centre**: System overview, decision funnels, risk trends, user activity, API health, and audit logs.
- **Superset BI Dashboards**: Connected directly to Athena for advanced charting.
- **Automated Email Alerts**: Airflow alerts on successful/failed ETL runs.

---

## 🏗️ Architecture
React Frontend
│
│
FastAPI API
│
┌──────────────┼──────────────┐
│ │ │
XGBoost PostgreSQL JWT
ML Model Database Security
│
└── AWS Data Pipeline (S3, Glue, Athena, Airflow)
│
└── Streamlit / Superset Dashboards

text

### AWS & Data Infrastructure
- **AWS S3**: Stores raw, cleaned, and processed Parquet data.
- **AWS Glue**: Crawls S3 data and catalogs tables in `fraudguard_dwh`.
- **AWS Athena**: Query engine for the `silver_transactions`, `silver_login_logs`, and other tables.
- **Apache Airflow**: Orchestrates the ETL pipeline and sends Gmail/SMTP notifications for task status.
- **Streamlit & Superset**: Both connect directly to Athena for deep analytics.

---

## 🛠️ Technology Stack

| Layer | Tools |
|-------|-------|
| **Frontend** | React, Vite, JavaScript, CSS |
| **Backend** | FastAPI, Python, SQLAlchemy |
| **Database** | PostgreSQL |
| **Machine Learning** | XGBoost, Scikit‑learn, Pandas, NumPy, SHAP |
| **Data Infrastructure** | AWS S3, AWS Glue, AWS Athena, Apache Airflow |
| **Analytics** | Streamlit, Apache Superset |
| **Deployment** | Docker, GitHub Actions (CI/CD to EC2), Render |

---

## 📂 Project Structure
FraudGuard/
│
├── fraud_detection/ # Core ML & API logic
│ ├── api/ # FastAPI routes
│ ├── application/ # Services (prediction, assistant, etc.)
│ ├── core/ # Config & settings
│ ├── database/ # PostgreSQL connection
│ ├── infrastructure/ # Repositories
│ ├── ml/ # XGBoost, autoencoder, feature engineering
│ ├── models/ # Model loading & storage
│ └── utils/ # Helpers
│
├── frontend/ # React frontend
│ ├── public/ # Static assets
│ ├── src/ # Components, pages, contexts
│ └── package.json
│
├── models_store/ # Trained models & metrics
│ ├── best_model.pkl
│ ├── scaler.pkl
│ ├── retrain_status.json
│ └── ...
│
├── .github/workflows/ # GitHub Actions CI/CD
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.frontend
├── main.py # FastAPI entry point
├── requirements.txt
└── README.md

text

---

## ⚙️ Installation & Local Development

### 1. Clone the repository
```bash
git clone https://github.com/MarvinVutshila/fraudguard.git
cd fraudguard
2. Backend setup
bash
pip install -r requirements.txt
3. Frontend setup
bash
cd frontend
npm install
4. Run the application
Backend: python main.py (or uvicorn fraud_detection.main:app --reload)

Frontend: npm run dev

Access the API docs at http://localhost:8000/docs and the frontend at http://localhost:5173.

📊 Model Performance
Metric	Score
Accuracy	99.82%
Precision	90.00%
Recall	82.65%
F1 Score	86.17%
ROC AUC	98.16%
Trained on a real‑world transaction dataset with 34 engineered features.

📸 Screenshots
🔐 Application & Workflow
Live Feed Dashboard	Approval Queue
https://data/dashboard.png	https://data/HumanApproval.png
Transaction History	AI Assistant
https://data/TransactionHistory.png	https://data/ai_assistant.png
Single Predict	Batch Analysis
https://data/SingleTransactionPredict.png	https://data/BatchTransactionAnalysis.png
Model Info	Model Metrics
https://data/ModelInformation.png	https://data/model_metrics.png
System Monitoring	API Logs
https://data/monitoring.png	https://data/api_logs.png
Knowledge Base	Admin Control Centre
https://data/knowledge_base.png	https://data/AdminControlCentre.png
☁️ AWS & Data Infrastructure
AWS Console Home	S3 Buckets
https://data/aws_console_home.png	https://data/aws_s3_buckets.png
AWS Glue Crawler	AWS Glue Database
https://data/aws_glue_crawler.png	https://data/aws_glue_database.png
Athena Query Editor	ETL Script Output
https://data/athena_query_editor.png	https://data/etl_script_output.png
GitHub Actions
https://data/github_actions.png
🔄 Airflow & DevOps
Airflow DAG Runs	Airflow Email Notification
https://data/airflow_dag_runs.png	https://data/email_airflow_notifications.png
Airflow Email Detail	System Health
https://data/email_airflow_detail.png	https://data/system_health.png
📈 Streamlit Analytics
Overview	Users
https://data/streamlit_overview.png	https://data/streamlit_users.png
Overrides by Reviewer
https://data/streamlit_overrides.png
📊 Superset
Table View
https://data/superset_table_view.png
🚀 Deployment
The application is containerised with Docker and deployed via GitHub Actions to an AWS EC2 instance.

CI/CD: On every push to main, GitHub Actions builds and deploys the latest images automatically.

Render hosts the public demo application.

Airflow runs on the same EC2 instance, orchestrating daily ETL jobs and sending status emails.

👨‍💻 Author
Marvin Vutshila
Machine Learning Engineer · Full‑Stack Developer
GitHub

⭐ Support
If you find this project useful, please give it a ⭐ on GitHub!

text

---

### 🚀 Final step – push this README

1. Save the above as `README.md` in your `C:\Users\marvi\fraudguard` folder (overwrite the existing one).
2. In PowerShell (still in that folder), run:

```powershell
git add README.md
git commit -m "Final professional README with all 28 screenshots"
git push origin main
