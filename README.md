# 🛡️ FraudGuard: Enterprise Real-Time Fraud Detection Platform

![FraudGuard Overview](data/dashboard.png)

## 📖 Project Overview

**FraudGuard** is an end-to-end, full-stack Machine Learning platform designed to detect fraudulent financial transactions in real-time. Built with a highly scalable microservices architecture, it bridges the gap between advanced machine learning anomaly detection and actionable human-in-the-loop operational workflows. 

The system continuously monitors incoming transactions, instantly classifying them as legitimate, suspicious (queued for manual review), or fraudulent. It features an **AI Assistant** powered by SHAP values to explain complex model predictions to human analysts in plain text, comprehensive cloud-native data pipelines, and deep analytics dashboards.

---

## ✨ Key Features

- **⚡ Real-Time & Batch ML Inference**: Utilizes advanced deep learning Autoencoder models deployed via FastAPI for sub-millisecond fraud scoring. Supports both live single predictions and bulk batch analysis.
- **🧠 Explainable AI (XAI)**: Integrated SHAP (SHapley Additive exPlanations) explainer provides human-readable context for *why* a transaction was flagged, empowering risk analysts to make confident decisions.
- **👥 Human-in-the-Loop Workflow**: A dedicated Analyst Dashboard with an Approval Queue allowing teams to override or confirm suspicious transactions, generating clean labeled data for future model retraining.
- **☁️ Cloud-Native Data Lake**: Built on AWS S3, automatically crawled and cataloged by AWS Glue, and queried via Amazon Athena for highly scalable analytical workloads.
- **🔄 Automated Pipelines & DevOps**: Orchestrated via Apache Airflow with automated email alerts for pipeline states. CI/CD automation powered by GitHub Actions.
- **📊 Advanced Analytics**: Multi-platform BI integration featuring Streamlit for operational analytics and Apache Superset for deep, slice-and-dice transactional insights.

---

## 🛠️ Architecture & Tech Stack

- **Frontend:** React 19, Vite, Chart.js, Tailwind/CSS
- **Backend & ML Server:** Python, FastAPI, PostgreSQL
- **Machine Learning:** PyTorch (Autoencoders), Scikit-Learn, SHAP
- **Data Engineering & Cloud (AWS):** S3 (Data Lake), AWS Glue (Crawler & ETL), Amazon Athena
- **DataOps & DevOps:** Apache Airflow, GitHub Actions
- **Business Intelligence:** Streamlit, Apache Superset

---

## 📸 System Gallery

### 🚀 Application & Workflow

| Live Feed Dashboard | Approval Queue |
|:---:|:---:|
| ![Dashboard](data/dashboard.png) | ![HumanApproval](data/HumanApproval.png) |

| Transaction History | AI Assistant |
|:---:|:---:|
| ![TransactionHistory](data/TransactionHistory.png) | ![AI Assistant](data/ai_assistant.png) |

| Single Predict | Batch Analysis |
|:---:|:---:|
| ![SingleTransactionPredict](data/SingleTransactionPredict.png) | ![Batch](data/BatchTransactionAnalysis.png) |

| Model Info | Model Metrics |
|:---:|:---:|
| ![ModelInformation](data/ModelInformation.png) | ![Model Metrics](data/model_metrics.png) |

| System Monitoring | API Logs |
|:---:|:---:|
| ![Monitoring](data/monitoring.png) | ![API Logs](data/api_logs.png) |

| Knowledge Base | Admin Control Centre |
|:---:|:---:|
| ![Knowledge Base](data/knowledge_base.png) | ![Admin](data/AdminControlCentre.png) |

### ☁️ AWS & Data Infrastructure

| AWS Console Home | S3 Buckets |
|:---:|:---:|
| ![AWS Home](data/aws_console_home.png) | ![S3](data/aws_s3_buckets.png) |

| AWS Glue Crawler | AWS Glue Database |
|:---:|:---:|
| ![Glue Crawler](data/aws_glue_crawler.png) | ![Glue DB](data/aws_glue_database.png) |

| Athena Query Editor | ETL Script Output |
|:---:|:---:|
| ![Athena](data/athena_query_editor.png) | ![ETL](data/etl_script_output.png) |

| GitHub Actions |
|:---:|
| ![Actions](data/github_actions.png) |

### ⚙️ Airflow & DevOps

| Airflow DAG Runs | Airflow Email Notification |
|:---:|:---:|
| ![Airflow](data/airflow_dag_runs.png) | ![Email Notif](data/email_airflow_notifications.png) |

| Airflow Email Detail | System Health |
|:---:|:---:|
| ![Email Detail](data/email_airflow_detail.png) | ![Health](data/system_health.png) |

### 📈 Streamlit Analytics

| Overview | Users |
|:---:|:---:|
| ![Streamlit Overview](data/streamlit_overview.png) | ![Users](data/streamlit_users.png) |

| Overrides by Reviewer |
|:---:|
| ![Overrides](data/streamlit_overrides.png) |

### 📉 Superset

| Table View |
|:---:|
| ![Superset Table](data/superset_table_view.png) |
