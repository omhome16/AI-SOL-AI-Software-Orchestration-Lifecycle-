from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Form, File, UploadFile
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import shutil
from pathlib import Path

from backend.services.project_service import ProjectService
from backend.core.state_manager import StateManager
from backend.core.config import Config

router = APIRouter()

# Singleton instance to persist active engines across requests
_project_service_instance = None

# Dependency to get ProjectService (singleton)
def get_project_service():
    global _project_service_instance
    if _project_service_instance is None:
        state_manager = StateManager()
        _project_service_instance = ProjectService(state_manager)
    return _project_service_instance

class ProjectRequest(BaseModel):
    project_name: str
    requirements: str
    enable_github: bool = False
    github_username: str = ""
    github_token: str = ""
    generate_tests: bool = False
    generate_devops: bool = False

@router.post("/create")
async def create_project(
    name: str = Form(...),
    type: str = Form(...),
    requirements: str = Form(...),
    enable_github: str = Form("false"),
    github_username: str = Form(""),
    github_token: str = Form(""),
    generate_tests: str = Form("true"),
    generate_devops: str = Form("true"),
    images: List[UploadFile] = File(default=[]),
    background_tasks: BackgroundTasks = None,
    service: ProjectService = Depends(get_project_service)
):
    """Create a new project and start the workflow."""
    try:
        # Convert string booleans to actual booleans
        enable_github_bool = enable_github.lower() == "true"
        generate_tests_bool = generate_tests.lower() == "true"
        generate_devops_bool = generate_devops.lower() == "true"
        
        # Prepare project data
        project_data = {
            "project_name": name,
            "project_type": type,
            "requirements": requirements,
            "enable_github": enable_github_bool,
            "github_username": github_username,
            "github_token": github_token,
            "generate_tests": generate_tests_bool,
            "generate_devops": generate_devops_bool
        }
        
        # Create project
        project_state = await service.create_project(project_data)
        project_id = project_state["project_id"]
        
        # Save uploaded images if any
        if images:
            workspace_dir = Path(Config.WORKSPACE_DIR) / project_id / "inspiration_images"
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            for img in images:
                if img.filename:
                    file_path = workspace_dir / img.filename
                    with file_path.open("wb") as buffer:
                        shutil.copyfileobj(img.file, buffer)
        
        # DON'T start workflow here - let configuration page do it!
        # await service.start_workflow(project_id, background_tasks)
        
        return {"project_id": project_id, "status": "created", "message": "Project created successfully"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def list_projects(service: ProjectService = Depends(get_project_service)):
    """List all projects."""
    return {"projects": service.list_projects()}

@router.get("/{project_id}")
async def get_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """Get project details."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/{project_id}")
async def delete_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """Delete a project."""
    success = service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "message": "Project deleted"}

@router.post("/{project_id}/restart")
async def restart_project(
    project_id: str, 
    background_tasks: BackgroundTasks,
    service: ProjectService = Depends(get_project_service)
):
    """Restart a project workflow."""
    try:
        await service.start_workflow(project_id, background_tasks)
        return {"status": "restarted", "message": "Workflow restarted"}
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/logs")
async def get_project_logs(project_id: str, service: ProjectService = Depends(get_project_service)):
    """Get project logs."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"logs": project.get("logs", [])}

@router.get("/{project_id}/status")
async def get_project_status(project_id: str, service: ProjectService = Depends(get_project_service)):
    """Get project status."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "status": project.get("status", "unknown"),
        "current_step": project.get("current_step"),
        "completed": project.get("completed", False),
        "steps_completed": project.get("steps", []),
        "generated_files": project.get("files", [])
    }

@router.post("/{project_id}/start-workflow")
async def start_workflow(
    project_id: str,
    background_tasks: BackgroundTasks,
    service: ProjectService = Depends(get_project_service)
):
    """Start workflow after configuration is complete."""
    try:
        await service.start_workflow(project_id, background_tasks)
        return {"status": "started", "message": "Workflow started successfully"}
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
