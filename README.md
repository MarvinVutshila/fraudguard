# 🛡️ FraudGuard – AI-Powered Fraud Detection Platform

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?logo=postgresql)
![XGBoost](https://img.shields.io/badge/XGBoost-Machine%20Learning-orange)
![Docker](https://img.shields.io/badge/Docker-Container-blue?logo=docker)
![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?logo=githubactions)
![License](https://img.shields.io/badge/License-MIT-green)

> **An end-to-end AI-powered fraud detection platform that combines Machine Learning, FastAPI, React, PostgreSQL, and Human-in-the-Loop decision making to detect, monitor, investigate, and manage fraudulent financial transactions in real time.**

---

# 📖 Table of Contents

- Overview
- Features
- Screenshots
- System Architecture
- Technology Stack
- Machine Learning Pipeline
- Project Structure
- Installation
- Running the Application
- API Features
- Model Performance
- Workflow
- Future Improvements
- Author
- License

---

# 🚀 Overview

FraudGuard is a production-style banking fraud detection platform designed to demonstrate how machine learning can be integrated into modern financial systems.

The platform automatically evaluates every incoming transaction using an **XGBoost classification model**. Based on the fraud probability, transactions are automatically:

- ✅ Approved
- ⚖️ Sent for Human Review
- 🚫 Blocked

Fraud analysts can manually investigate suspicious transactions before making the final decision.

The application combines:

- React Frontend
- FastAPI REST API
- PostgreSQL Database
- XGBoost Machine Learning
- Human Approval Workflow
- Audit Logging
- Authentication & Authorization
- Administrative Dashboard

---

# 🌐 Live Demo

### Frontend

YOUR_DEPLOYMENT_URL

### Backend API

http://localhost:8000/docs

---

# 📸 Application Screenshots

---

## 🔐 Login

Secure JWT authentication with role-based access.

![Login](assets/loginPage.png)

---

## 📡 Live Transaction Dashboard

Monitor transactions in real time with fraud probability scoring.

![Dashboard](assets/dashboard.png)

---

## ⚖️ Human Approval Queue

Transactions requiring analyst review before approval.

![Approval Queue](assets/HumanApproval.png)

---

## 📝 Approval Audit Log

Complete history of analyst decisions.

![Approval Audit](assets/ApprovalAudit.png)

---

## 📋 Transaction History

Searchable audit trail with filtering and CSV export.

![Transaction History](assets/TransactionHistory.png)

---

## 🔍 Single Transaction Prediction

Predict fraud probability for a single transaction.

![Single Prediction](assets/SingleTransactionPredict.png)

---

## 📁 Batch Transaction Analysis

Upload CSV files for large-scale fraud detection.

![Batch Analysis](assets/BatchTransactionAnalysis.png)

---

## 🧠 Model Information

Model metrics, thresholds and feature importance.

![Model Information](assets/ModelInformation.png)

---

# 🛡️ Administration Centre

### Dashboard

![Admin Dashboard](assets/AdminControlCentre.png)

---

### User Management

![User Management](assets/AdminControlCentre1.png)

---

### Login Audit Logs

![Login Logs](assets/AdminControlCentre2.png)

---

### User Activity

![Activity](assets/AdminControlCentre3.png)

---

# ✨ Features

## 🤖 Machine Learning

- XGBoost fraud detection model
- Feature Engineering
- Fraud probability prediction
- Configurable decision thresholds
- SHAP Explainability
- Model metadata dashboard

---

## 📡 Live Monitoring

- Live transaction feed
- Fraud probability scoring
- Risk classification
- Auto refresh
- Search & filtering
- Dashboard analytics

---

## ⚖️ Human Approval Workflow

- Manual transaction review
- Approve / Block decisions
- Analyst comments
- Override tracking
- Approval history

---

## 📋 Transaction Management

- Full audit trail
- Search transactions
- CSV Export
- Risk filtering
- Decision filtering

---

## 🔍 Fraud Prediction

Predict fraud probability for a single transaction.

Supports:

- Amount
- Time
- PCA Features (V1–V28)

Optional SHAP explanations.

---

## 📁 Batch Analysis

Upload CSV files and score thousands of transactions simultaneously.

Results include:

- Fraud Probability
- Decision
- Risk Level

---

## 🧠 Model Dashboard

Displays:

- Accuracy
- Precision
- Recall
- F1 Score
- ROC AUC
- Thresholds
- Feature Importance

---

## 👥 User Administration

- User management
- Role management
- Block/unblock users
- Account approval
- Login history
- Activity monitoring

---

## 🔒 Security

- JWT Authentication
- Role-Based Access Control (RBAC)
- Password hashing
- Login auditing
- Protected admin accounts
- Secure REST API

---

# 🏗️ System Architecture

```text
                ┌────────────────────────────┐
                │       React Frontend       │
                └──────────────┬─────────────┘
                               │
                          REST API
                               │
                ┌──────────────▼─────────────┐
                │          FastAPI           │
                └──────────────┬─────────────┘
                               │
       ┌───────────────────────┼────────────────────────┐
       │                       │                        │
       ▼                       ▼                        ▼
 Machine Learning       PostgreSQL Database     Authentication
    XGBoost              Users & Transactions         JWT
```

---

# 🧠 Machine Learning Pipeline

```text
Transaction Data
        │
        ▼
Feature Engineering
        │
        ▼
Train XGBoost Model
        │
        ▼
Model Evaluation
        │
        ▼
Save Model
        │
        ▼
FastAPI Prediction Service
        │
        ▼
React Dashboard
```

---

# 🛠️ Technology Stack

## Frontend

- React
- Vite
- JavaScript
- CSS
- Chart.js

---

## Backend

- FastAPI
- Python
- SQLAlchemy
- PostgreSQL
- JWT Authentication

---

## Machine Learning

- XGBoost
- Scikit-learn
- Pandas
- NumPy
- SHAP

---

## DevOps

- Docker
- Docker Compose
- GitHub Actions

---

# 📂 Project Structure

```text
FraudGuard
│
├── .github/
│   └── workflows/
│
├── data/
│
├── fraud_detection/
│   ├── api/
│   ├── application/
│   ├── core/
│   ├── database/
│   ├── infrastructure/
│   ├── ml/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── utils/
│
├── frontend/
│   ├── public/
│   └── src/
│
├── models_store/
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── train.py
├── ingest_pipeline.py
├── main.py
└── README.md
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/FraudGuard.git
cd FraudGuard
```

Install backend dependencies

```bash
pip install -r requirements.txt
```

Install frontend dependencies

```bash
cd frontend
npm install
```

---

# ▶️ Running the Application

### Start PostgreSQL

```bash
docker compose up
```

---

### Run the Backend

```bash
python main.py
```

Backend runs on:

```
http://localhost:8000
```

Swagger Documentation:

```
http://localhost:8000/docs
```

---

### Run the Frontend

```bash
cd frontend
npm run dev
```

Frontend:

```
http://localhost:5173
```

---

# 🔌 API Features

- User Authentication
- JWT Authorization
- Predict Fraud
- Batch Prediction
- Transaction Monitoring
- Approval Queue
- Transaction History
- User Management
- Login Audit
- Model Information

---

# 📊 Machine Learning Performance

| Metric | Score |
|---------|-------|
| Accuracy | **99.82%** |
| Precision | **90.00%** |
| Recall | **82.65%** |
| F1 Score | **86.17%** |
| ROC AUC | **98.16%** |

---

# 🔄 Fraud Detection Workflow

```text
Incoming Transaction
          │
          ▼
 Feature Engineering
          │
          ▼
 XGBoost Prediction
          │
          ▼
Fraud Probability
          │
          ▼
 ┌────────┼─────────┐
 │        │         │
 ▼        ▼         ▼
Approve  Review   Block
           │
           ▼
 Human Analyst Review
           │
           ▼
 Audit Log Updated
           │
           ▼
 Dashboard Refresh
```

---

# 🌟 Future Improvements

- Real-time WebSocket updates
- Email fraud alerts
- SMS notifications
- Multi-factor authentication (MFA)
- Explainable AI dashboard
- Multi-tenant architecture
- Kubernetes deployment
- CI/CD deployment pipeline
- Grafana monitoring
- Prometheus metrics

---

# 👨‍💻 Author

## Marvin Vutshila

Computer Science Student

Machine Learning Engineer

Full Stack Developer

### GitHub

https://github.com/YOUR_GITHUB_USERNAME

### LinkedIn

https://linkedin.com/in/YOUR_LINKEDIN

---

# 📄 License

This project is licensed under the MIT License.

---

## ⭐ Support

If you enjoyed this project or found it useful, consider giving it a **⭐ Star** on GitHub.

It helps others discover the project and motivates future development.

Thank you for visiting **FraudGuard**!
