import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.backend.helpers.auth import get_current_user
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager


router = APIRouter()
class ChatRequest(BaseModel):
    message: str
    assistant_id: int

@router.post("/")
async def chat(
    request: ChatRequest,
    user_id: int = Depends(get_current_user),
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant_by_id(request.assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    async def stream_response():
        try:
            buffer = ""
            chunk_size = 20  # Adjust this value to control streaming speed (larger value = faster)
            delay = 0.05  # Adjust this value to control delay between chunks (smaller value = faster)
            
            for chunk in assistant.run(request.message, stream=True):
                if chunk:  # Only process non-empty chunks
                    buffer += chunk
                    while len(buffer) >= chunk_size:
                        yield json.dumps({"response": buffer[:chunk_size]}) + "\n"
                        buffer = buffer[chunk_size:]
                        await asyncio.sleep(delay)
            
            if buffer:  # Yield any remaining content in the buffer
                yield json.dumps({"response": buffer}) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

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