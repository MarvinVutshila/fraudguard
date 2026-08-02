from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fraud_detection.api.routes import transactions

app = FastAPI(title="FraudGuard API", version="1.0")

# CORS settings (allows your frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect your transactions router (this includes the new /ingest endpoint)
app.include_router(transactions.router)