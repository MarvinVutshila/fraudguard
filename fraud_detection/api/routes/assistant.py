from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import logging

from fraud_detection.api.dependencies import get_services, verify_token
from fraud_detection.application.services.assistant_service import AssistantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: dict = Depends(verify_token),  # verify_token returns a dict
    services=Depends(get_services)
):
    """
    Streams an AI assistant response.
    """
    try:
        assistant = AssistantService(services, user)
        
        async def stream_generator():
            async for chunk in assistant.stream_response(request.message, request.conversation_id):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        logger.error(f"Assistant chat error: {e}")
        raise HTTPException(status_code=500, detail="Assistant service error")