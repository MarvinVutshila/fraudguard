import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import re

# ✅ Import the module-level get_connection function
from fraud_detection.database.postgres_db import get_connection

logger = logging.getLogger(__name__)

async def fetch_relevant_data(query: str, services, user: dict) -> Dict[str, Any]:
    data = {
        "query": query,
        "user": user.get("sub", "unknown"),
        "role": user.get("role", "analyst")
    }

    # 1. Transactions
    all_txs = services.storage_service.get_transactions(limit=1000, offset=0, decision=None)
    today = datetime.now().date()
    today_txs = [tx for tx in all_txs if tx.get("timestamp") and tx["timestamp"].date() == today]
    
    total_tx = len(all_txs)
    today_tx = len(today_txs)
    avg_amount = sum(tx.get("amount", 0) for tx in all_txs) / total_tx if total_tx else 0
    avg_risk = sum(tx.get("probability", 0) for tx in all_txs) / total_tx if total_tx else 0
    
    decisions = {}
    risk_levels = {}
    for tx in all_txs:
        dec = tx.get("decision", "UNKNOWN")
        decisions[dec] = decisions.get(dec, 0) + 1
        rl = tx.get("risk_level", "UNKNOWN")
        risk_levels[rl] = risk_levels.get(rl, 0) + 1

    data["transaction_summary"] = {
        "total": total_tx,
        "today": today_tx,
        "average_amount": round(avg_amount, 2),
        "average_probability": round(avg_risk, 4),
        "decision_counts": decisions,
        "risk_level_counts": risk_levels
    }

    # 2. Blocked transactions (list + pre‑formatted markdown)
    blocked_txs = [tx for tx in all_txs if tx.get("decision") == "BLOCK"]
    blocked_txs.sort(key=lambda tx: tx.get("timestamp", datetime.min), reverse=True)
    blocked_list = [
        {
            "transaction_id": tx.get("transaction_id"),
            "amount": tx.get("amount"),
            "probability": tx.get("probability"),
            "risk_level": tx.get("risk_level"),
            "timestamp": tx.get("timestamp").isoformat() if tx.get("timestamp") else None
        }
        for tx in blocked_txs[:20]
    ]
    data["blocked_transactions"] = blocked_list

    # Pre‑formatted markdown table for blocked transactions
    blocked_md = ""
    if blocked_list:
        blocked_md = "| Transaction ID | Amount | Risk Score | Risk Level | Time |\n"
        blocked_md += "| --- | --- | --- | --- | --- |\n"
        for tx in blocked_list:
            blocked_md += f"| {tx['transaction_id']} | ${tx['amount']:.2f} | {tx['probability']:.2%} | {tx['risk_level']} | {tx['timestamp']} |\n"
    data["blocked_transactions_md"] = blocked_md

    # 3. Overrides (list + pre‑formatted markdown)
    overrides = services.storage_service.get_all_overrides(limit=50)
    recent_override_list = [
        {
            "transaction_id": o.get("transaction_id"),
            "original_decision": o.get("model"),
            "new_decision": o.get("human_decision"),
            "analyst": o.get("analyst"),
            "reason": o.get("reason"),
            "timestamp": o.get("timestamp").isoformat() if o.get("timestamp") else None
        }
        for o in overrides[:10]
    ]
    data["overrides"] = {
        "total": len(overrides),
        "recent": recent_override_list
    }

    # Pre‑formatted markdown table for overrides
    overrides_md = ""
    if recent_override_list:
        overrides_md = "| Transaction ID | Original | New Decision | Analyst | Reason | Timestamp |\n"
        overrides_md += "| --- | --- | --- | --- | --- | --- |\n"
        for o in recent_override_list:
            reason = o['reason'] or '—'
            overrides_md += f"| {o['transaction_id']} | {o['original_decision']} | {o['new_decision']} | {o['analyst']} | {reason} | {o['timestamp']} |\n"
    data["overrides_md"] = overrides_md

    # 4. Model info
    if hasattr(services.prediction_service, 'artefacts'):
        artefacts = services.prediction_service.artefacts
        data["model_info"] = {
            "type": type(artefacts.model).__name__,
            "features": len(artefacts.feature_names) if artefacts.feature_names else 0,
            "threshold": artefacts.threshold if hasattr(artefacts, 'threshold') else None
        }
    else:
        data["model_info"] = {"status": "available"}

    # 5. SHAP explanation
    if "explain" in query.lower():
        tx_id_match = re.search(r"txn-[a-f0-9]+|FRAUD-\d+", query, re.IGNORECASE)
        if tx_id_match:
            tx_id = tx_id_match.group(0)
            tx = services.storage_service.get_transaction(tx_id)
            if tx and tx.get("features"):
                explanation = {}
                if hasattr(services.prediction_service, 'explain'):
                    explanation = services.prediction_service.explain(tx)
                data["shap_explanation"] = explanation

    # 6. System health
    data["system_health"] = await fetch_system_health()

    # 7. API metrics
    data["api_metrics"] = await fetch_api_metrics()

    # 8. Login logs
    data["login_logs"] = await fetch_login_logs(services, user.get("role", "analyst"))

    # 9. Knowledge Base
    kb_entries = services.storage_service.db.get_knowledge_base_entries(search=query, limit=5)
    data["knowledge_base"] = kb_entries

    return data

async def fetch_system_health() -> Dict[str, Any]:
    try:
        sql = """
            SELECT cpu_percent, memory_used_mb, memory_total_mb, db_connections, timestamp
            FROM system_health
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
        if row:
            cpu = row[0]
            memory_used = row[1]
            memory_total = row[2]
            db_conn = row[3]
            memory_percent = (memory_used / memory_total) * 100 if memory_total else 0
            status = "Healthy" if cpu < 80 and memory_percent < 85 else "Degraded"
            return {
                "cpu": f"{cpu}%",
                "memory": f"{memory_used:.0f} MB / {memory_total:.0f} MB ({memory_percent:.1f}%)",
                "db_connections": db_conn,
                "timestamp": row[4].isoformat() if row[4] else None,
                "status": status
            }
    except Exception as e:
        logger.warning(f"Failed to fetch system health: {e}")
    return {"status": "No recent health data recorded"}

async def fetch_api_metrics() -> Dict[str, Any]:
    try:
        sql = """
            SELECT
                AVG(response_time) as avg_latency,
                COUNT(*) FILTER (WHERE status_code >= 400) * 1.0 / COUNT(*) as error_rate
            FROM api_requests
            WHERE timestamp > NOW() - INTERVAL '24 hours';
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
        if row and row[0] is not None:
            return {
                "avg_latency_ms": round(row[0], 1),
                "error_rate": round(row[1] * 100, 1) if row[1] else 0.0
            }
    except Exception as e:
        logger.warning(f"Failed to fetch API metrics: {e}")
    return {"avg_latency_ms": "No data", "error_rate": "No data"}

async def fetch_login_logs(services, role: str) -> Dict[str, Any]:
    try:
        db = services.storage_service.db
        total_failed = db.get_total_failed_logins_last_24h()
        recent_failures = db.get_login_logs(limit=10, offset=0, username=None)
        recent_failures = [
            {
                "username": row.get("username"),
                "ip": row.get("ip"),
                "timestamp": row.get("timestamp").isoformat() if row.get("timestamp") else None
            }
            for row in recent_failures if not row.get("success")
        ]
        result = {
            "total_failed_last_24h": total_failed,
            "recent_failures": recent_failures[:5]
        }
        if role == "admin":
            brute_force = db.get_brute_force_alerts(minutes=15, threshold=5)
            result["brute_force_alerts"] = [
                {
                    "username": alert.get("username"),
                    "attempts": alert.get("attempts"),
                    "last_attempt": alert.get("last_attempt").isoformat() if alert.get("last_attempt") else None,
                    "ips": alert.get("ips")
                }
                for alert in brute_force
            ]
        else:
            result["brute_force_alerts"] = "Not available for analysts"
        return result
    except Exception as e:
        logger.warning(f"Failed to fetch login logs: {e}")
        return {"total_failed_last_24h": "No data", "recent_failures": []}