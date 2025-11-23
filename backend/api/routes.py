from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import shutil
from pathlib import Path
import json
import asyncio
import logging

from core.state import create_initial_state
from orchestrator.central import CentralOrchestrator
from core.tools import Tools
from core.config import Config
from backend.core.workflow import WorkflowEngine
from backend.api.websocket import manager
from backend.core.state_manager import get_state_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Get global state manager
state_manager = get_state_manager()

class ChatMessage(BaseModel):
    project_id: str
    message: str

@router.get("/projects")
async def list_projects():
    """List all projects."""
    try:
        projects = state_manager.list_projects()
        return {"projects": projects, "count": len(projects)}
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/create")
async def create_project(
    name: str = Form(...),
    requirements: str = Form(...),
    type: str = Form("website"),
    enable_github: bool = Form(False),
    github_username: str = Form(""),
    github_token: str = Form(""),
    generate_tests: bool = Form(True),
    generate_devops: bool = Form(True),
    images: List[UploadFile] = File(None)
):
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    project_name = name.strip().replace(" ", "_")
    
    # Initialize workspace
    workspace_path = Path(Config.WORKSPACE_DIR) / project_name
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Handle Image Uploads
    image_paths = []
    if images:
        images_dir = workspace_path / "inspiration_images"
        images_dir.mkdir(exist_ok=True)
        for i, image in enumerate(images):
            if i >= 3: break # Limit to 3 images
            file_path = images_dir / image.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_paths.append(str(file_path))
    
    # Initialize Tools
    tools = Tools(workspace_path=str(workspace_path))
    
    # Initialize State
    initial_state = create_initial_state(
        task_id=project_id,
        project_name=project_name,
        requirements=requirements,
        workspace_path=str(workspace_path),
        user_context={
            "project_type": type,
            "enable_research": True,
            "inspiration_images": image_paths,
            "enable_github": enable_github,
            "github_username": github_username,
            "github_token": github_token,
            "generate_tests": generate_tests,
            "generate_devops": generate_devops
        }
    )
    
    orchestrator = CentralOrchestrator(tools)
    
    # Start workflow in background
    engine = WorkflowEngine(project_id, orchestrator, initial_state, connection_manager=manager, state_manager=state_manager)
    
    # Create project data
    project_data = {
        "state": initial_state,
        "tools": None,  # Can't serialize tools
        "orchestrator": None,  # Can't serialize orchestrator
        "engine": None,  # Can't serialize engine
        "status": "created",
        "logs": []
    }
    
    # Save to persistent storage
    state_manager.save_project(project_id, project_data)
    
    # Keep engine reference in memory for active execution
    # We'll create a separate in-memory dict for active engines
    if not hasattr(router, "_active_engines"):
        router._active_engines = {}
    
    router._active_engines[project_id] = {
        "engine": engine,
        "tools": tools,
        "orchestrator": orchestrator
    }
    
    asyncio.create_task(engine.run())
    
    return {
        "project_id": project_id,
        "project_name": project_name,
        "status": "started",
        "workspace": str(workspace_path),
        "image_count": len(image_paths)
    }

@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get complete project details."""
    project = state_manager.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Remove non-serializable fields
    safe_project = {
        "project_id": project_id,
        "state": project.get("state"),
        "status": project.get("status"),
        "logs": project.get("logs", [])
    }
    return safe_project

@router.get("/projects/{project_id}/status")
async def get_project_status(project_id: str):
    status = state_manager.get_project_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    return status

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    # Stop workflow if running
    if hasattr(router, "_active_engines") and project_id in router._active_engines:
        # Cancel the workflow
        del router._active_engines[project_id]
    
    # Delete from persistent storage
    success = state_manager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete project")
    
    return {"message": "Project deleted successfully", "project_id": project_id}

@router.post("/projects/{project_id}/resume")
async def resume_project(project_id: str):
    if not hasattr(router, "_active_engines"):
        router._active_engines = {}
    
    if project_id not in router._active_engines:
        raise HTTPException(status_code=404, detail="Project engine not found")
    
    engine = router._active_engines[project_id].get("engine")
    
    if engine:
        await engine.resume()
        return {"status": "resumed"}
    else:
        raise HTTPException(status_code=400, detail="Workflow engine not found for this project")

@router.post("/projects/{project_id}/restart")
async def restart_project(project_id: str, from_stage: Optional[str] = None):
    """Restart a failed or completed workflow."""
    project = state_manager.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    state = project.get("state")
    if not state:
        raise HTTPException(status_code=400, detail="Invalid project state")
    
    # Reset workflow state
    state["status"] = "pending"
    state["current_step"] = from_stage or "initialize"
    if from_stage:
        # Keep completed steps up to the restart point
        try:
            all_steps = ["requirements", "architecture", "developer", "qa", "devops"]
            restart_idx = all_steps.index(from_stage)
            state["steps_completed"] = all_steps[:restart_idx]
        except ValueError:
            state["steps_completed"] = []
    else:
        state["steps_completed"] = []
    
    # Save updated state
    state_manager.save_project(project_id, project)
    
    # Recreate workflow components
    workspace_path = Path(state["workspace_path"])
    tools = Tools(workspace_path=str(workspace_path))
    orchestrator = CentralOrchestrator(tools)
    engine = WorkflowEngine(project_id, orchestrator, state, connection_manager=manager, state_manager=state_manager)
    
    # Store in active engines
    if not hasattr(router, "_active_engines"):
        router._active_engines = {}
    
    router._active_engines[project_id] = {
        "engine": engine,
        "tools": tools,
        "orchestrator": orchestrator
    }
    
    # Start workflow
    asyncio.create_task(engine.run())
    
    return {"status": "restarted", "from_stage": from_stage or "beginning"}

@router.get("/projects/{project_id}/logs")
async def get_project_logs(project_id: str):
    """Get all logs for a project."""
    project = state_manager.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"logs": project.get("logs", [])}

@router.post("/chat")
async def chat_with_orchestrator(chat_req: ChatMessage):
    project_id = chat_req.project_id
    
    # Load project
    project = state_manager.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get active engine if available
    engine = None
    orchestrator = None
    if hasattr(router, "_active_engines") and project_id in router._active_engines:
        engine = router._active_engines[project_id].get("engine")
        orchestrator = router._active_engines[project_id].get("orchestrator")
    
    # Log user message
    if engine:
        await engine.broadcast(f"USER: {chat_req.message}")
    
    # Process with Orchestrator if available
    if orchestrator:
        response_text = await orchestrator.process_user_message(chat_req.message, project.get("state", {}))
    else:
        response_text = "Orchestrator not available. Please ensure the project is running."
    
    # Check for resume keywords in user message
    if "proceed" in chat_req.message.lower() or "continue" in chat_req.message.lower() or "resume" in chat_req.message.lower():
        if engine:
            await engine.resume()
            response_text += "\n\n[System] Resuming workflow..."
            
    if engine:
        await engine.broadcast(f"AI: {response_text}")
        
    return {"response": response_text}

@router.get("/projects/{project_id}/files")
async def get_project_files(project_id: str):
    """List all files in the project workspace."""
    project = state_manager.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace_path = Path(Config.WORKSPACE_DIR) / project["state"]["project_name"]
    
    files = []
    if workspace_path.exists():
        for path in workspace_path.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                rel_path = path.relative_to(workspace_path)
                files.append(str(rel_path).replace("\\", "/"))
                
    return {"files": files}

@router.get("/projects/{project_id}/files/content")
async def get_file_content(project_id: str, path: str):
    """Get content of a specific file."""
    project = state_manager.load_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace_path = Path(Config.WORKSPACE_DIR) / project["state"]["project_name"]
    file_path = workspace_path / path
    
    # Security check to prevent directory traversal
    try:
        file_path.resolve().relative_to(workspace_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except UnicodeDecodeError:
        return {"content": "[Binary or non-UTF-8 file]"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI-SOL Backend",
        "version": "2.0.0",
        "projects_count": len(state_manager.projects)
    }

@router.get("/config")
async def get_config():
    """Get system configuration."""
    return {
        "model_provider": Config.MODEL_PROVIDER,
        "model_name": Config.MODEL_NAME,
        "features": {
            "web_search": Config.ENABLE_WEB_SEARCH,
            "code_analysis": Config.ENABLE_CODE_ANALYSIS
        }
    }
