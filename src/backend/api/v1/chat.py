import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from src.backend.helpers.auth import get_current_user
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager


router = APIRouter()

@router.post("/")
async def chat(
    message: str = Query(..., description="The message to send to the assistant"),
    assistant_id: int = Query(..., description="The ID of the assistant"),
    user_id: int = Depends(get_current_user),
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant_by_id(assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    async def stream_response():
        try:
            for chunk in assistant.run(message, stream=True):
                yield (json.dumps({"response": chunk}) + "\n").encode('utf-8')
                await asyncio.sleep(0.01)  # Small delay to ensure smooth streaming
        except Exception as e:
            yield (json.dumps({"error": str(e)}) + "\n").encode('utf-8')

    return StreamingResponse(stream_response(), media_type="application/json")

@router.get("/chat_history")
async def get_chat_history(
    assistant_id: int,
    user_id: int = Depends(get_current_user),
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant_by_id(assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    history = assistant.memory.get_chat_history()
    return {"history": history}