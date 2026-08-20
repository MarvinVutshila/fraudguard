# 🛡️ FraudGuard – AI-Powered Fraud Detection Platform

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![React](https://img.shields.io/badge/React-Frontend-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![XGBoost](https://img.shields.io/badge/XGBoost-Machine_Learning-orange)
![Docker](https://img.shields.io/badge/Docker-Container-blue)
![AWS](https://img.shields.io/badge/AWS-Glue_Athena_S3-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-Analytics-red)

> An end‑to‑end AI fraud detection platform built with Machine Learning, FastAPI, React, PostgreSQL, and human‑review workflows, deployed on AWS with automated ETL pipelines.

---

## 🌐 Live Demos

- 🚀 **Main Application**: [https://fraudguard-434w.onrender.com/login](https://fraudguard-434w.onrender.com/login)  
- 📄 **Analytics Dashboard (Streamlit)**: [https://marvinvutshila.github.io/fraudguard-reports/](https://marvinvutshila.github.io/fraudguard-reports/)

---

## 🚀 Overview

FraudGuard is a banking fraud detection system that uses an **XGBoost machine learning model** to analyse transactions and classify them as:

- ✅ **Approved** – low risk, automatically passed
- ⚖️ **Human Review** – suspicious, requires analyst decision
- 🚫 **Blocked** – high risk, prevented

The platform provides:

- Real‑time transaction monitoring
- Single‑transaction & batch prediction
- Human review workflow with audit trails
- Admin control centre with user management
- ML model insights (feature importance, metrics)
- **AWS‑backed data pipeline** (Glue, Athena, S3)
- **Streamlit analytics dashboard** for deep insights

---

## ✨ Features

### 🤖 Machine Learning
- XGBoost fraud detection model (99.82% accuracy)
- Feature engineering with 34 features
- Fraud probability scoring and risk classification
- Model retraining and evaluation
- Explainable AI with SHAP feature importance

### 📡 Real‑Time Monitoring
- Live transaction feed
- Approval queue with 350+ pending items
- Dashboard metrics (total transactions, blocked, pending reviews)
- Probability trend graphs

### ⚖️ Human Review Workflow
- Suspicious transaction queue
- Approve or block transactions with comments
- Full audit history of all overrides
- Analyst‑friendly UI

### 📁 Batch Processing
- Upload CSV files for bulk scoring
- Automatic fraud prediction and decision generation

### 🔐 Security
- JWT authentication with role‑based access (Admin / Analyst)
- Password hashing and 2FA setup (QR code)
- Protected admin routes and audit logging

### 📊 Analytics & Reporting
- **Streamlit dashboard** with system overview, decision funnel, risk trends, user activity, API health, and audit logs
- **Superset integration** for advanced charting and exploration (connected to Athena)

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
└── AWS Data Pipeline (Glue, Athena, S3)
│
└── Streamlit / Superset Dashboards

text

### AWS Data Pipeline
- **AWS Glue** crawls raw data from S3 and creates tables in the Data Catalog.
- **AWS Athena** serves as the query engine for the `fraudguard_dwh` database (with `silver_transactions`, `silver_login_logs`, etc.).
- **Streamlit** and **Superset** connect directly to Athena for analytics.

---

## 🛠️ Technology Stack

| Layer | Tools |
|-------|-------|
| **Frontend** | React, Vite, JavaScript, CSS |
| **Backend** | FastAPI, Python, SQLAlchemy |
| **Database** | PostgreSQL |
| **Machine Learning** | XGBoost, Scikit‑learn, Pandas, NumPy, SHAP |
| **Data Infrastructure** | AWS Glue, Athena, S3 |
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
🔐 Login Page
https://data/loginPage.png

📊 Main Dashboard (Live Feed)
https://data/dashboard.png

⚖️ Approval Queue
https://data/HumanApproval.png

📝 Audit Log
https://data/ApprovalAudit.png

📋 Transaction History
https://data/TransactionHistory.png

🔍 Single Transaction Prediction
https://data/SingleTransactionPredict.png

📁 Batch Analysis
https://data/BatchTransactionAnalysis.png

🧠 Model Info & Metrics
https://data/ModelInformation.png

🛡️ Admin Control Centre
https://data/AdminControlCentre.png
https://data/AdminControlCentre1.png
https://data/AdminControlCentre2.png
https://data/AdminControlCentre3.png

📈 Analytics Dashboard (Streamlit)
https://data/streamlit_overview.png
(You can add your own screenshot of the Streamlit dashboard)

📊 Superset Charts (Athena)
https://data/superset_chart.png

🔄 AWS Glue Crawler & Athena
https://data/glue_crawler.png
https://data/athena_query.png

🚀 Deployment
The application is containerised with Docker and deployed via GitHub Actions to an AWS EC2 instance.

CI/CD: On every push to main, GitHub Actions builds and deploys the latest images.

Render hosts the public demo (login page).

👨‍💻 Author
Marvin Vutshila
Machine Learning Engineer · Full‑Stack Developer
GitHub

⭐ Support
If you find this project useful, please give it a ⭐ on GitHub!

text

---

## 🖼️ How to Add the Screenshots

1. **Place your images** inside the `data/` folder (as you already have). Ensure the filenames match those in the README (e.g., `loginPage.png`, `dashboard.png`, etc.).
2. **If you have additional screenshots** (like the Streamlit dashboard or Superset charts), rename them accordingly and add the paths.
3. **Commit and push** the updated `README.md` and the `data/` folder to GitHub.

```bash
git add README.md data/
git commit -m "Update README with comprehensive documentation and screenshots"
git push origin main
