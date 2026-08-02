from typing import Dict, Any
import json

def build_prompt(query: str, data: Dict[str, Any], user: dict) -> str:
    # Detect casual acknowledgements
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
- Keep explanations brief. Use bullet points for steps.
- If data is missing, simply state "No data available".
- Do not include extra vertical bars or symbols outside the table.
- Keep the overall response professional and under 600 tokens.

Now answer the user query using the data provided below.
"""

    # Build knowledge section
    kb_entries = data.get("knowledge_base", [])
    kb_text = ""
    if kb_entries:
        kb_text = "\n=== KNOWLEDGE BASE ===\n"
        for entry in kb_entries:
            kb_text += f"Q: {entry['question']}\nA: {entry['answer']}\n\n"
    else:
        kb_text = "No relevant knowledge base entries found for this query."

    # Prepare data text – if pre‑formatted tables exist, include them; otherwise include raw JSON.
    data_text = ""
    if not is_casual:
        # Use pre‑formatted tables if available
        blocked_md = data.get("blocked_transactions_md", "")
        overrides_md = data.get("overrides_md", "")
        
        # Build a clean summary from the structured data
        summary_lines = []
        tx_summary = data.get("transaction_summary", {})
        if tx_summary:
            summary_lines.append(f"Total transactions: {tx_summary.get('total', 0)}")
            summary_lines.append(f"Today: {tx_summary.get('today', 0)}")
            summary_lines.append(f"Approved: {tx_summary.get('decision_counts', {}).get('APPROVE', 0)}")
            summary_lines.append(f"Blocked: {tx_summary.get('decision_counts', {}).get('BLOCK', 0)}")
            summary_lines.append(f"Pending Review: {tx_summary.get('decision_counts', {}).get('REVIEW', 0)}")
            summary_lines.append(f"Average Risk: {tx_summary.get('average_probability', 0):.2%}")
            summary_lines.append(f"Average Amount: ${tx_summary.get('average_amount', 0):.2f}")
        
        summary_text = "\n".join(summary_lines)
        
        # Combine with pre‑formatted tables
        data_text = f"SUMMARY:\n{summary_text}\n\n"
        if blocked_md:
            data_text += f"BLOCKED TRANSACTIONS:\n{blocked_md}\n"
        if overrides_md:
            data_text += f"RECENT OVERRIDES:\n{overrides_md}\n"
        
        # Add other metrics if needed
        if data.get("system_health"):
            health = data["system_health"]
            data_text += f"SYSTEM HEALTH: {health.get('status', 'Unknown')} (CPU: {health.get('cpu', 'N/A')}, Memory: {health.get('memory', 'N/A')})\n"
        if data.get("api_metrics"):
            api = data["api_metrics"]
            data_text += f"API: Latency {api.get('avg_latency_ms', 'N/A')} ms, Error Rate {api.get('error_rate', 'N/A')}%\n"
        
        # Also include raw JSON for any extra context (optional, but we can include it)
        data_text += "\nRAW DATA (for reference):\n" + json.dumps(data, indent=2, default=str, ensure_ascii=False)

    full_prompt = f"""{system}

{"DATA SUMMARY:" if not is_casual else ""}
{data_text if not is_casual else ""}

{kb_text}
USER QUERY:
{query}

ASSISTANT RESPONSE:"""
    return full_prompt