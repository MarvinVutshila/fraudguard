┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│      🛡️ FRAUD DETECTION SYSTEM – PRODUCTION ML + API + DASHBOARD             │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ End-to-end fraud detection using XGBoost (trained on the Kaggle Credit      │
│ Card Fraud dataset), served via a modular FastAPI backend, with an          │
│ HTML/JavaScript dashboard and PostgreSQL for transaction history.           │
│ Fully containerised and deployable on Render + Neon + Netlify/Vercel.       │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🎯 SYSTEM ARCHITECTURE                                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ User / CSV                                                                   │
│      │                                                                       │
│      ▼                                                                       │
│ HTML/JS Dashboard                                                            │
│      │                                                                       │
│      ▼                                                                       │
│ FastAPI Backend                                                              │
│      ├──────────► PostgreSQL / Neon Database                                │
│      │                                                                       │
│      └──────────► Trained XGBoost Model                                     │
│                            │                                                  │
│                            ▼                                                  │
│                     SHAP Explanations                                         │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 📁 PROJECT STRUCTURE                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ fraud_detection/                                                             │
│ ├── .env.example                                                             │
│ ├── .gitignore                                                               │
│ ├── Dockerfile                                                               │
│ ├── docker-compose.yml                                                       │
│ ├── requirements.txt                                                         │
│ ├── main.py                                                                  │
│ ├── train.py                                                                 │
│ ├── evaluate_model.py                                                        │
│ ├── live_stream_review_focused.py                                            │
│ ├── tests/                                                                   │
│ │   ├── __init__.py                                                          │
│ │   └── test_connection.py                                                   │
│ ├── frontend/                                                                │
│ │   ├── index.html                                                           │
│ │   └── Marvin.jpg                                                           │
│ ├── models_store/                                                            │
│ │   ├── best_model.pkl                                                       │
│ │   ├── scaler.pkl                                                           │
│ │   ├── amount_bins.pkl                                                      │
│ │   ├── feature_names.pkl                                                    │
│ │   └── optimal_threshold.pkl                                                │
│ └── fraud_detection/                                                         │
│     ├── api/                                                                 │
│     │   ├── dependencies.py                                                  │
│     │   ├── auth.py                                                          │
│     │   └── routes/                                                          │
│     │       ├── health.py                                                    │
│     │       ├── model.py                                                     │
│     │       ├── predictions.py                                               │
│     │       ├── transactions.py                                              │
│     │       ├── history.py                                                   │
│     │       ├── ingest.py                                                    │
│     │       └── auth.py                                                      │
│     ├── application/services/                                                │
│     │   ├── prediction_service.py                                            │
│     │   └── decision_service.py                                              │
│     ├── infrastructure/                                                      │
│     │   ├── database/                                                        │
│     │   └── repositories/                                                    │
│     ├── ml/                                                                  │
│     │   ├── feature_engineering.py                                           │
│     │   └── inference/                                                       │
│     │       ├── model_loader.py                                              │
│     │       └── explainability.py                                            │
│     ├── schemas/                                                             │
│     ├── core/                                                                │
│     └── utils/                                                               │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🧠 MODEL PERFORMANCE                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ ROC-AUC                           : 0.9816                                  │
│ F1 Score (threshold 0.9244)       : 0.8677                                  │
│ Recall @ threshold 0.70           : 85.7%                                   │
│ False Positive Rate @ 0.70        : 0.07%                                   │
│                                                                              │
│ Status: READY FOR LOW-FALSE-ALARM FRAUD DETECTION                           │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🚀 DEPLOYMENT STACK                                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ API        → Render                                                          │
│ Database   → Neon PostgreSQL                                                 │
│ Dashboard  → Netlify / Vercel                                                │
│                                                                              │
│ Render Free Tier:                                                           │
│ • 750 hours/month                                                            │
│ • Auto-deploy from GitHub                                                    │
│ • Sleeps after 15 minutes idle                                               │
│                                                                              │
│ Neon Free Tier:                                                             │
│ • 0.5 GB storage                                                             │
│ • Serverless PostgreSQL                                                      │
│ • Scales to zero                                                             │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🧪 LIVE WORKFLOW                                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ CSV Upload                                                                   │
│      ▼                                                                       │
│ Dashboard Sends Request                                                      │
│      ▼                                                                       │
│ FastAPI Predict Endpoint                                                     │
│      ▼                                                                       │
│ XGBoost Model + SHAP                                                         │
│      ▼                                                                       │
│ APPROVE / REVIEW / BLOCK Decision                                            │
│      ▼                                                                       │
│ Store Results in PostgreSQL                                                  │
│      ▼                                                                       │
│ Display History Dashboard                                                    │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⚠️ PRODUCTION NOTES                                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ • Render free instances experience cold starts.                              │
│ • Neon should be used instead of Render PostgreSQL.                          │
│ • Dataset uses PCA features V1–V28 from Kaggle dataset.                      │
│ • Real banking systems would use actual transaction features.                │
│ • This project demonstrates production-style ML engineering practices.       │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🔮 INDUSTRY FEATURES ALREADY PRESENT                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ ✅ Machine Learning Model (XGBoost)                                          │
│ ✅ Explainable AI (SHAP)                                                     │
│ ✅ FastAPI REST API                                                          │
│ ✅ PostgreSQL Persistence                                                    │
│ ✅ Dashboard Interface                                                       │
│ ✅ Modular Architecture                                                      │
│ ✅ Docker Support                                                            │
│ ✅ Environment Configuration                                                 │
│ ✅ Deployment Ready                                                          │
│ ✅ Transaction History                                                       │
│ ✅ Risk Scoring Engine                                                       │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 👨‍💻 AUTHOR                                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ Marvin                                                                       │
│ Data Science & AI Engineer                                                   │
│                                                                              │
│ Educational / Research Use                                                   │
│ Portfolio-Ready Production ML Project                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
