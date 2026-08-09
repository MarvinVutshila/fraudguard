from typing import Dict, Any
import json

def build_prompt(query: str, data: Dict[str, Any], user: dict) -> str:
    casual_phrases = ["thanks", "thank you", "okay", "ok", "got it", "👍", "cool", "great"]
    is_casual = any(phrase in query.lower() for phrase in casual_phrases)

    system = f"""You are FraudGuard AI Assistant, a knowledgeable fraud analyst assistant.
You have access to real-time transaction data, system metrics, and a knowledge base about the FraudGuard platform.
Your role is to provide clear, concise, and accurate answers.

Current user: {user.get('sub', 'unknown')} (role: {user.get('role', 'analyst')})
{ "You are an admin and have full access to all data." if user.get('role') == 'admin' else "You are an analyst. You cannot access admin-only data like user management or full API logs." }

Answer using only the provided data and knowledge base. Do not invent statistics or facts. If the data doesn't contain the answer, say so.

{ "If the user says 'thanks', 'okay', or similar casual acknowledgements, respond politely and concisely (e.g., 'You're welcome!' or 'Glad to help!') without generating a summary or using data." if is_casual else "" }

FORMATTING RULES – FOLLOW THESE STRICTLY:
- For tabular data, **always use a markdown table** with header row and separator row (`---`).
- If a pre‑formatted markdown table is provided (e.g., `blocked_transactions_md` or `overrides_md`), **use that exact table** – do not rewrite it.
- For transaction lists, use these column headings exactly: Transaction ID, Amount, Risk Score, Risk Level, Time.
- For overrides, use: Transaction ID, Original, New Decision, Analyst, Reason, Timestamp.
- For security summaries (login attempts), structure it as:
  🔐 Authentication Security Summary
  -----------------------------------
  Total failed attempts (last 24h): X
  Distinct users affected: X
  Top offending IPs: (if available)
  Risk assessment: Low / Medium / High
  Recommendation: (actionable advice)
- Keep explanations brief. Use bullet points for steps.
- If data is missing, simply state "No data available".
- Do not include extra vertical bars or symbols outside the table.
- Keep overall response professional and under 600 tokens.

Now answer the user query using the data provided below.
"""

    kb_entries = data.get("knowledge_base", [])
    kb_text = ""
    if kb_entries:
        kb_text = "\n=== KNOWLEDGE BASE ===\n"
        for entry in kb_entries:
            kb_text += f"Q: {entry['question']}\nA: {entry['answer']}\n\n"
    else:
        kb_text = "No relevant knowledge base entries found for this query."

    data_text = ""
    if not is_casual:
        # If we have login_security data, format it prominently
        login_security = data.get("login_security")
        if login_security:
            summary = login_security
            data_text += f"""🔐 AUTHENTICATION SECURITY SUMMARY
-----------------------------------
Total failed attempts (last 24h): {summary.get('total_failures_24h', 0)}
Distinct users with failures: {len(summary.get('users_with_failures', []))}
Risk assessment: {summary.get('analysis', 'Unknown')}

Recent failed attempts (last 10):
"""
            for log in summary.get('recent_logs', [])[:10]:
                data_text += f"- {log.get('timestamp')} | {log.get('username')} | IP: {log.get('ip')}\n"
            data_text += "\n"

        blocked_md = data.get("blocked_transactions_md", "")
        overrides_md = data.get("overrides_md", "")

        tx_summary = data.get("transaction_summary", {})
        if tx_summary:
            lines = []
            lines.append(f"Total transactions: {tx_summary.get('total', 0)}")
            lines.append(f"Today: {tx_summary.get('today', 0)}")
            lines.append(f"Approved: {tx_summary.get('decision_counts', {}).get('APPROVE', 0)}")
            lines.append(f"Blocked: {tx_summary.get('decision_counts', {}).get('BLOCK', 0)}")
            lines.append(f"Pending Review: {tx_summary.get('decision_counts', {}).get('REVIEW', 0)}")
            lines.append(f"Average Risk: {tx_summary.get('average_probability', 0):.2%}")
            lines.append(f"Average Amount: ${tx_summary.get('average_amount', 0):.2f}")
            data_text += "SUMMARY:\n" + "\n".join(lines) + "\n\n"

        if blocked_md:
            data_text += f"BLOCKED TRANSACTIONS:\n{blocked_md}\n"
        if overrides_md:
            data_text += f"RECENT OVERRIDES:\n{overrides_md}\n"

        if data.get("system_health"):
            h = data["system_health"]
            data_text += f"SYSTEM HEALTH: {h.get('status', 'Unknown')} (CPU: {h.get('cpu', 'N/A')}, Memory: {h.get('memory', 'N/A')})\n"
        if data.get("api_metrics"):
            api = data["api_metrics"]
            data_text += f"API: Latency {api.get('avg_latency_ms', 'N/A')} ms, Error Rate {api.get('error_rate', 'N/A')}%\n"

        data_text += "\nRAW DATA (for reference):\n" + json.dumps(data, indent=2, default=str, ensure_ascii=False)

    full_prompt = f"""{system}

{"DATA SUMMARY:" if not is_casual else ""}
{data_text if not is_casual else ""}

{kb_text}
USER QUERY:
{query}

ASSISTANT RESPONSE:"""
    return full_prompt