# 🛡️ FraudGuard – AI-Powered Fraud Detection Platform

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?logo=postgresql)
![XGBoost](https://img.shields.io/badge/XGBoost-Machine%20Learning-orange)
![Docker](https://img.shields.io/badge/Docker-Container-blue?logo=docker)
![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?logo=githubactions)
![License](https://img.shields.io/badge/License-MIT-green)

> **An end-to-end AI-powered fraud detection platform combining Machine Learning, FastAPI, React, PostgreSQL, and Human-in-the-Loop decision making to detect, monitor, investigate, and manage fraudulent financial transactions in real time.**

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
- Running Application
- API Features
- Model Performance
- Workflow
- Future Improvements
- Author
- License


---

# 🚀 Overview

FraudGuard is a production-style banking fraud detection platform designed to demonstrate how Artificial Intelligence can be integrated into modern financial systems.

The system evaluates transactions using an **XGBoost Machine Learning model** and assigns:

- ✅ Approved
- ⚖️ Human Review
- 🚫 Blocked


The platform includes:

- React Dashboard
- FastAPI Backend
- PostgreSQL Database
- XGBoost Fraud Model
- Human Approval Workflow
- Audit Logging
- JWT Authentication
- Admin Management Centre


---

# 🌐 Live Demo

Frontend:

```
YOUR_DEPLOYMENT_URL
```

Backend API:

```
http://localhost:8000/docs
```


---

# 📸 Application Screenshots


## 🔐 Login Page

Secure JWT authentication with role-based access.

<img src="./loginPage.png" width="900">


---

## 📡 Transaction Dashboard

Real-time fraud monitoring dashboard.

<img src="./dashboard.png" width="900">


---

## ⚖️ Human Approval Queue

Analysts review suspicious transactions.

<img src="./HumanApproval.png" width="900">


---

## 📝 Approval Audit

Complete history of analyst decisions.

<img src="./ApprovalAudit.png" width="900">


---

## 📋 Transaction History

Search, filter and export transaction records.

<img src="./TransactionHistory.png" width="900">


---

## 🔍 Single Transaction Prediction

Predict fraud probability for individual transactions.

<img src="./SingleTransactionPredict.png" width="900">


---

## 📁 Batch Transaction Analysis

Upload CSV files and analyse thousands of transactions.

<img src="./BatchTransactionAnalysis.png" width="900">


---

## 🧠 Model Information

Machine learning metrics and feature importance.

<img src="./ModelInformation.png" width="900">


---

# 🛡️ Administration Centre


## Admin Dashboard

<img src="./AdminControlCentre.png" width="900">


---

## User Management

<img src="./AdminControlCentre1.png" width="900">


---

## Login Audit Logs

<img src="./AdminControlCentre2.png" width="900">


---

## User Activity Monitoring

<img src="./AdminControlCentre3.png" width="900">


---

# ✨ Features


## 🤖 Machine Learning

- XGBoost fraud classification
- Feature engineering
- Fraud probability scoring
- Risk classification
- Configurable thresholds
- SHAP explainability


---

## 📡 Real-Time Monitoring

- Live transaction feed
- Fraud detection scoring
- Risk level classification
- Dashboard analytics
- Filtering and search


---

## ⚖️ Human Approval Workflow

- Manual transaction review
- Approve / Block decisions
- Analyst comments
- Override tracking
- Approval history


---

## 📋 Transaction Management

- Transaction history
- Search
- Filtering
- CSV export
- Audit trail


---

## 🔍 Fraud Prediction

Supports:

- Transaction amount
- Time features
- PCA Features V1-V28


Provides:

- Fraud probability
- Decision
- Risk level


---

## 📁 Batch Processing

Upload transaction datasets.

Returns:

- Fraud probability
- Decision
- Risk category


---

## 👥 Administration

Includes:

- User management
- Role management
- Account control
- Login monitoring
- Activity tracking


---

# 🔒 Security

Implemented:

- JWT Authentication
- Role Based Access Control
- Password hashing
- Login auditing
- Protected admin access
- Secure REST API


---

# 🏗️ System Architecture


```
                React Frontend
                      |
                      |
                  REST API
                      |
                      |
                 FastAPI Backend
                      |
        --------------------------------
        |              |               |
        |              |               |
    XGBoost        PostgreSQL       JWT Auth
   ML Model        Database        Security

```


---

# 🧠 Machine Learning Pipeline


```
Transaction Data

        |
        v

Feature Engineering

        |
        v

Train XGBoost Model

        |
        v

Model Evaluation

        |
        v

Save Model

        |
        v

FastAPI Prediction API

        |
        v

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


## Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- JWT


## Machine Learning

- XGBoost
- Scikit-learn
- Pandas
- NumPy
- SHAP


## DevOps

- Docker
- Docker Compose
- GitHub Actions


---

# 📂 Project Structure


```
FraudGuard

│
├── .github/
│
├── data/
│   └── simulation.csv
│
├── fraud_detection/
│
├── frontend/
│
├── models_store/
│
├── tests/
│
├── AdminControlCentre.png
├── AdminControlCentre1.png
├── AdminControlCentre2.png
├── AdminControlCentre3.png
├── ApprovalAudit.png
├── BatchTransactionAnalysis.png
├── HumanApproval.png
├── ModelInformation.png
├── SingleTransactionPredict.png
├── TransactionHistory.png
├── dashboard.png
├── loginPage.png
│
├── Dockerfile
├── docker-compose.yml
├── train.py
├── main.py
└── README.md

```


---

# ⚙️ Installation


Clone repository:

```bash
git clone https://github.com/YOUR_USERNAME/FraudGuard.git

cd FraudGuard
```


Install backend:

```bash
pip install -r requirements.txt
```


Install frontend:

```bash
cd frontend

npm install
```


---

# ▶️ Running Application


Start database:

```bash
docker compose up
```


Run backend:

```bash
python main.py
```


Backend:

```
http://localhost:8000
```


Swagger:

```
http://localhost:8000/docs
```


Run frontend:

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

- Authentication
- JWT Authorization
- Fraud Prediction
- Batch Prediction
- Transaction Monitoring
- Approval Queue
- Audit Logs
- User Management
- Model Information


---

# 📊 Machine Learning Performance


| Metric | Score |
|-|-|
| Accuracy | 99.82% |
| Precision | 90.00% |
| Recall | 82.65% |
| F1 Score | 86.17% |
| ROC AUC | 98.16% |


---

# 🔄 Fraud Detection Workflow


```
Incoming Transaction

        |

        v

Feature Engineering

        |

        v

XGBoost Prediction

        |

        v

Fraud Probability

        |

        v


Approve  ---> Complete

Review   ---> Human Analyst

Block    ---> Reject


        |

        v

Audit Log Updated

        |

        v

Dashboard Refresh

```


---

# 🌟 Future Improvements

- WebSocket real-time updates
- Email alerts
- SMS notifications
- MFA authentication
- Explainable AI dashboard
- Kubernetes deployment
- Prometheus monitoring
- Grafana dashboards


---

# 👨‍💻 Author


## Marvin Vutshila

Computer Science Student

Machine Learning Engineer

Full Stack Developer


GitHub:

```
https://github.com/YOUR_USERNAME
```


LinkedIn:

```
https://linkedin.com/in/YOUR_LINKEDIN
```


---

# 📄 License

MIT License


---

# ⭐ Support

If you like this project, consider giving it a ⭐ on GitHub.

Thank you for visiting **FraudGuard** 🚀
