import os
import logging
import json
from typing import AsyncGenerator, Dict, Any, Optional

from groq import AsyncGroq

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        # This is the latest model as of now (free tier, fast)
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

    async def stream_response(self, message: str, conversation_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        from fraud_detection.assistant.data_fetcher import fetch_relevant_data
        from fraud_detection.assistant.prompt_builder import build_prompt

        data = await fetch_relevant_data(message, self.services, self.user)
        prompt = build_prompt(message, data, self.user)

        async for chunk in self.llm_client.stream_completion(prompt):
            yield chunk