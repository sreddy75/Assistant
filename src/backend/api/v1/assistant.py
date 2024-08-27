from typing import Dict
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from src.backend.schemas.code_tool_schemas import ProjectLoadRequest
from src.backend.kr8.tools.code_tools import CodeTools
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
            "has_knowledge_base": assistant.knowledge_base is not None            
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

@router.get("/get-introduction/{assistant_id}")
async def get_introduction(
    assistant_id: int,
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant_by_id(assistant_id)
    if assistant:
        return {"introduction": assistant.introduction}
    raise HTTPException(status_code=404, detail="Assistant not found")

@router.post("/load-project")
async def load_project(
    request: ProjectLoadRequest = Body(...),
    assistant_manager: AssistantManager = Depends(get_assistant_manager)
):
    assistant = assistant_manager.get_assistant_by_id(request.assistant_id)
    if assistant:
        if hasattr(assistant, 'tools'):
            code_tools = next((tool for tool in assistant.tools if isinstance(tool, CodeTools)), None)
            if code_tools:
                try:
                    result = code_tools.load_project(
                        project_name=request.project_name,
                        project_type=request.project_type,
                        directory_content=request.directory_content
                    )
                    return {"result": result}
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error loading project: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="CodeTools not found in assistant")
        else:
            raise HTTPException(status_code=400, detail="Assistant does not have tools attribute")
    else:
        raise HTTPException(status_code=404, detail="Assistant not found")