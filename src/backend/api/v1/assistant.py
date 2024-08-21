from fastapi import APIRouter, Depends, HTTPException, Query
from src.backend.kr8.assistant.assistant_manager import get_assistant_manager, AssistantManager

router = APIRouter()

@router.get("/get-assistant")
async def get_assistant(
    user_id: int,
    org_id: int,
    user_role: str,
    user_nickname: str,
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant(user_id, org_id, user_role, user_nickname)
    return {"assistant_id": id(assistant)}

@router.get("/assistant-info/{assistant_id}")
async def get_assistant_info(
    assistant_id: int,
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant_by_id(assistant_id)
    if assistant:
        return {
            "has_knowledge_base": assistant.knowledge_base is not None,
            # Add other necessary information about the assistant
        }
    return {"error": "Assistant not found"}

@router.post("/create-run")
async def create_run(
    assistant_id: int = Query(..., description="The ID of the assistant"),
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant_by_id(assistant_id)
    if assistant:
        try:
            run_id = assistant.create_run()
            return {"run_id": run_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not create LLM OS run: {str(e)}")
    else:
        raise HTTPException(status_code=404, detail="Assistant not found")