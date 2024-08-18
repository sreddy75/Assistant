from fastapi import APIRouter, Depends
from src.backend.helpers.auth import get_current_user
from src.ui.components.assistant_initializer import initialize_assistant

router = APIRouter()

@router.post("/chat")
async def chat(message: str, user_id: int = Depends(get_current_user)):
    llm_os = initialize_assistant(user_id)
    response = llm_os.run(message)
    return {"response": response}

@router.get("/chat_history")
async def get_chat_history(user_id: int = Depends(get_current_user)):
    llm_os = initialize_assistant(user_id)
    history = llm_os.memory.get_chat_history()
    return {"history": history}