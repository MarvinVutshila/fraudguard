# 🛡️ FraudGuard – AI-Powered Fraud Detection Platform

> **An end-to-end fraud detection platform that combines machine learning, real-time transaction monitoring, human review workflows, and administrative controls into a single web application.**

FraudGuard is a production-style banking platform designed to detect fraudulent financial transactions using an **XGBoost machine learning model**. It combines automated fraud detection with human-in-the-loop decision making, allowing analysts to review suspicious transactions before final approval.

The application consists of a **React frontend**, a **FastAPI backend**, **PostgreSQL database**, and a **Python machine learning pipeline** for model training and inference.

---

# 📸 Screenshots

## Login

![Login](assets/loginPage.png)

---

## Live Monitoring Dashboard

![Dashboard](assets/dashboard.png)

---

# 🚀 Key Features

### 🤖 Machine Learning

* XGBoost fraud detection model
* Real-time fraud probability scoring
* Feature engineering pipeline
* SHAP explainability support
* Configurable decision thresholds
* Model performance dashboard

---

### 📡 Live Transaction Monitoring

* Live transaction feed
* Automatic refresh
* Fraud probability scoring
* Risk level classification
* Decision tracking
* Search and filtering

---

### ⚖️ Human Approval Workflow

Transactions classified as **REVIEW** are routed to analysts for manual investigation.

Analysts can:

* Approve transactions
* Block transactions
* Record review reasons
* View previous decisions
* Export audit history

---

### 📋 Transaction History

* Complete audit trail
* Override history
* Risk filtering
* CSV export
* Search by transaction ID

---

### 🔍 Single Prediction

Predict fraud probability for an individual transaction using:

* Amount
* Time
* PCA Features (V1–V28)

Optional SHAP explanations help explain model predictions.

---

### 📁 Batch Analysis

Upload CSV files for bulk fraud analysis.

The platform scores every transaction and returns:

* Fraud probability
* Decision
* Risk level

---

### 🧠 Model Information

View detailed model metadata including:

* Model version
* Accuracy
* Precision
* Recall
* F1 Score
* ROC AUC
* Decision thresholds
* Top contributing features

---

### 👤 Administration

Secure administration panel with:

* User management
* Role management
* Account approval
* User blocking
* Login audit logs
* Security alerts
* Activity monitoring

---

### 🔒 Authentication & Security

* JWT Authentication
* Role-Based Access Control (RBAC)
* Protected administrator accounts
* Login auditing
* Failed login tracking
* Secure API endpoints

---

# 🏗️ System Architecture

```text
                    ┌──────────────────┐
                    │   React Frontend │
                    └─────────┬────────┘
                              │
                         REST API
                              │
                    ┌─────────▼─────────┐
                    │      FastAPI      │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
 Machine Learning      PostgreSQL Database     Authentication
     Engine            Transactions & Users         JWT

```

---

# 🛠️ Technology Stack

## Frontend

* React
* Vite
* JavaScript
* CSS
* Chart.js

## Backend

* FastAPI
* Python
* SQLAlchemy
* PostgreSQL
* JWT Authentication

## Machine Learning

* XGBoost
* Scikit-learn
* SHAP
* Pandas
* NumPy

## DevOps

* Docker
* Docker Compose
* GitHub Actions

---

# 📂 Project Structure

```text
FraudGuard/

├── frontend/                 # React Frontend
├── fraud_detection/          # Backend Application
│   ├── api/
│   ├── application/
│   ├── core/
│   ├── infrastructure/
│   ├── ml/
│   ├── models/
│   ├── schemas/
│   └── services/
│
├── models_store/             # Trained ML Models
├── tests/
├── data/
├── .github/
├── train.py
├── ingest_pipeline.py
├── evaluate_model.py
├── create_admin.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/FraudGuard.git
cd FraudGuard
```

Install Python dependencies

```bash
pip install -r requirements.txt
```

Install frontend dependencies

```bash
cd frontend
npm install
```

Run the backend

```bash
python main.py
```

Run the frontend

```bash
npm run dev
```

---

# 📊 Machine Learning Performance

| Metric    |      Score |
| --------- | ---------: |
| Accuracy  | **99.82%** |
| Precision | **90.00%** |
| Recall    | **82.65%** |
| F1 Score  | **86.17%** |
| ROC AUC   | **98.16%** |

---

# 🔄 Workflow

1. Incoming transaction received
2. Feature engineering applied
3. XGBoost model predicts fraud probability
4. Decision assigned:

   * **Approve**
   * **Review**
   * **Block**
5. Analysts review flagged transactions
6. Audit log updated
7. Dashboard refreshed in real time

---

# 🌟 Future Enhancements

* Real-time WebSocket streaming
* Email and SMS fraud alerts
* Multi-factor authentication (MFA)
* Explainable AI dashboard
* Multi-tenant support
* Kubernetes deployment
* CI/CD pipeline enhancements

---

# 👨‍💻 Author

**Marvin Vutshila**

Computer Science Student

Machine Learning & Software Engineering Enthusiast

GitHub: https://github.com/YOUR_USERNAME

LinkedIn: https://linkedin.com/in/YOUR_PROFILE

---

# 📄 License

This project is licensed under the MIT License.

---

⭐ If you found this project useful, please consider giving it a **Star** on GitHub.
