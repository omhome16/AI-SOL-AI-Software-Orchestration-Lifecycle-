from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from backend.services.project_service import ProjectService
from backend.core.state_manager import StateManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Import the singleton getter from projects router
from backend.api.routers.projects import get_project_service

class ChatRequest(BaseModel):
    message: str
    project_id: str

@router.post("/chat")
async def chat_with_orchestrator(
    chat_req: ChatRequest,
    service: ProjectService = Depends(get_project_service)
):
    """Chat with the orchestrator for a specific project."""
    
    logger.info(f"📨 Chat message received for project {chat_req.project_id}: '{chat_req.message}'")
    
    # Detect approval messages
    if "approve" in chat_req.message.lower():
        logger.info(f"✅ APPROVAL DETECTED - will resume workflow for {chat_req.project_id}")
    
    response = await service.process_chat_message(chat_req.project_id, chat_req.message)
    
    logger.info(f"📤 Chat response: action={response.get('action')}, message preview={response.get('message', 'N/A')[:50]}...")
    
    return {"response": response}

@router.post("/projects/{project_id}/resume")
async def resume_workflow(
    project_id: str,
    service: ProjectService = Depends(get_project_service)
):
    """Resume a paused workflow."""
    logger.info(f"🔄 Resume workflow request for project {project_id}")
    result = await service.resume_workflow(project_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
