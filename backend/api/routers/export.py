"""
Project Export to ZIP functionality
Allows users to download their complete generated project as a ZIP file
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import zipfile
import tempfile
import logging
from pathlib import Path
from backend.core.state_manager import get_state_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{project_id}/zip")
async def export_project_zip(project_id: str):
    """
    Export all project files as a ZIP archive
    
    Args:
        project_id: ID of the project to export
        
    Returns:
        ZIP file download
    """
    try:
        state_manager = get_state_manager()
        project = state_manager.load_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_name = project.get("project_name", project_id)
        project_dir = Path(f"outputs/{project_id}/{project_name}")
        
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project files not found")
        
        # Create temporary ZIP file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            zip_path = tmp_file.name
        
        # Create ZIP archive
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all project files
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, project_dir.parent)
                    zipf.write(file_path, arcname)
            
            # Add configuration file
            import json
            config_data = {
                "project_id": project_id,
                "project_name": project_name,
                "configuration": project.get("user_context", {}).get("configuration", {}),
                "type": project.get("type", "unknown"),
                "created_at": project.get("created_at", "unknown")
            }
            zipf.writestr("project_config.json", json.dumps(config_data, indent=2))
        
        logger.info(f"Created ZIP export for project {project_id}")
        
        # Return ZIP file
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{project_name}.zip",
            background=None  # File will be cleaned up automatically
        )
        
    except Exception as e:
        logger.error(f"Failed to export project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
