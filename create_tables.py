import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Create transactions table
cur.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    amount FLOAT,
    fraud_probability FLOAT,
    decision TEXT,
    risk_level TEXT,
    features JSONB,
    explanation JSONB
)
""")

# Create overrides table
cur.execute("""
CREATE TABLE IF NOT EXISTS transaction_overrides (
    transaction_id TEXT PRIMARY KEY,
    new_decision TEXT,
    reason TEXT,
    overridden_by TEXT,
    overridden_at TIMESTAMP DEFAULT NOW()
)
""")

conn.commit()
cur.close()
conn.close()
print("✅ Tables created successfully")
