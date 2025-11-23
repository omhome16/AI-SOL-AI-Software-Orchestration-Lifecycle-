from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pathlib import Path
import shutil
from typing import List

from backend.services.project_service import ProjectService
from backend.core.state_manager import StateManager
from backend.core.config import Config

router = APIRouter()

# Dependency to get ProjectService
def get_project_service():
    state_manager = StateManager()
    return ProjectService(state_manager)

@router.get("/projects/{project_id}/files")
async def get_project_files(project_id: str, service: ProjectService = Depends(get_project_service)):
    """List all files in the project workspace."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace_path = Path(Config.WORKSPACE_DIR) / project.get("project_name", project_id)
    
    files = []
    if workspace_path.exists():
        for path in workspace_path.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                rel_path = path.relative_to(workspace_path)
                files.append(str(rel_path).replace("\\", "/"))
                
    return {"files": files}

@router.get("/projects/{project_id}/files/content")
async def get_file_content(project_id: str, path: str, service: ProjectService = Depends(get_project_service)):
    """Get content of a specific file."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace_path = Path(Config.WORKSPACE_DIR) / project.get("project_name", project_id)
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


from pydantic import BaseModel

class SaveFileRequest(BaseModel):
    content: str


@router.put("/projects/{project_id}/files/content")
async def save_file_content(
    project_id: str,
    path: str,
    req: SaveFileRequest,
    service: ProjectService = Depends(get_project_service)
):
    """Save edited file content back to the file."""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace_path = Path(Config.WORKSPACE_DIR) / project.get("project_name", project_id)
    file_path = workspace_path / path
    
    # Security check to prevent directory traversal
    try:
        file_path.resolve().relative_to(workspace_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"success": True, "message": "File saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    project_id: str = Form(...)
):
    """Upload an inspiration image."""
    try:
        # We need to load the project to get the name, but for now we can use project_id if we don't have the service handy
        # Or we can instantiate the service here
        state_manager = StateManager()
        project = state_manager.load_project(project_id)
        
        if not project:
             # Fallback: try to find project by ID in active projects if not saved yet (unlikely with new architecture)
             # Or just use a temp directory. But we want it in the project workspace.
             # If project not found, we can't save it to the correct place.
             raise HTTPException(status_code=404, detail="Project not found")

        project_name = project.get("project_name", project_id)
        
        # Create images directory in project workspace
        save_dir = Path(Config.WORKSPACE_DIR) / project_name / "inspiration_images"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"filename": file.filename, "path": str(file_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
