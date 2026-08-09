import os
import logging
import json
from typing import AsyncGenerator, Dict, Any, Optional

from groq import AsyncGroq
from fraud_detection.database.postgres_db import Database

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    async def stream_completion(self, prompt: str):
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield {"type": "token", "content": content}
            yield {"type": "done"}
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            yield {"type": "error", "content": f"Assistant temporarily unavailable: {str(e)}"}


class AssistantService:
    def __init__(self, services, user: dict):
        self.services = services
        self.user = user
        self.llm_client = GroqClient()
        self.db = Database()

    async def stream_response(self, message: str, conversation_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        from fraud_detection.assistant.data_fetcher import fetch_relevant_data
        from fraud_detection.assistant.prompt_builder import build_prompt

        # --- Detect login attempt queries ---
        login_keywords = ["failed login", "login attempts", "failed login attempts", "brute force", "unauthorized"]
        if any(kw in message.lower() for kw in login_keywords):
            # Fetch login logs
            logs = self.db.get_login_logs(limit=20)
            total_failures = self.db.get_total_failed_logins_last_24h()
            # Get per-user failure counts
            with self.db._get_cursor() as cur:  # if _get_cursor exists; else use get_connection()
                cur.execute("""
                    SELECT username, COUNT(*) as cnt
                    FROM login_logs
                    WHERE success = false AND timestamp > NOW() - INTERVAL '24 hours'
                    GROUP BY username
                    ORDER BY cnt DESC
                """)
                user_failures = [{"username": r[0], "count": r[1]} for r in cur.fetchall()]

            # Build a structured summary to inject into data
            summary = {
                "total_failures_24h": total_failures,
                "recent_logs": logs[:10],
                "users_with_failures": user_failures,
                "analysis": "High" if total_failures > 20 else "Medium" if total_failures > 5 else "Low"
            }
            # Inject into the data dictionary
            data = await fetch_relevant_data(message, self.services, self.user)
            data["login_security"] = summary
        else:
            data = await fetch_relevant_data(message, self.services, self.user)

        prompt = build_prompt(message, data, self.user)
        async for chunk in self.llm_client.stream_completion(prompt):
            yield chunk