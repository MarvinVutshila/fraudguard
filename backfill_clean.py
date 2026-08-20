import requests
import boto3
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"
S3_BUCKET = "fraudguard-warehouse-2026"
S3_PREFIX = "raw/transactions"
AUTH_HEADER = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXJ2aW5tYWtodWJlbGEwNEBnbWFpbC5jb20iLCJyb2xlIjoiYWRtaW4iLCJleHAiOjE3ODcwMDI0MTMsInR5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3ODcwMDA2MTN9.M-lFB_FJZfePQcWkxtU5K2JwF2L18RkEDYk_NuP1teQ"
}

s3 = boto3.client('s3')

def main():
    print("🚀 Fetching exact 48,768 records (sequential)...")
    page = 1
    limit = 1000
    total = 0
    all_records = []
    partition_date = datetime.utcnow().strftime("%Y-%m-%d")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    while True:
        url = f"{API_BASE_URL}/transactions?page={page}&limit={limit}"
        resp = requests.get(url, headers=AUTH_HEADER)
        if resp.status_code != 200:
            print(f"❌ API returned {resp.status_code}, stopping.")
            break
        data = resp.json()
        records = data.get("transactions", [])
        if not records:
            print("✅ No more records. Backfill complete.")
            break
        all_records.extend(records)
        total += len(records)
        print(f"📄 Page {page}: {len(records)} records (Total: {total})")
        page += 1

    if all_records:
        key = f"{S3_PREFIX}/dt={partition_date}/backfill_clean_{timestamp}_{len(all_records)}.json"
        content = "\n".join(json.dumps(r) for r in all_records)
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=content.encode('utf-8'))
        print(f"✅ Uploaded {len(all_records)} clean records to s3://{S3_BUCKET}/{key}")
    else:
        print("🟡 No records found.")

if __name__ == "__main__":
    main()
