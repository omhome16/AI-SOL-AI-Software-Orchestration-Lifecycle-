"""
Centralized File Management System for AI-SOL

Handles:
- File generation with versioning
- Duplicate prevention
- Event emission
- File retrieval and listing
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from backend.core.config import Config
from backend.core.event_bus import get_event_bus, WorkflowEvent, EventType, EventSeverity

logger = logging.getLogger(__name__)


class FileManager:
    """Centralized file management to prevent duplicates and handle versioning."""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.workspace_dir = Path(Config.WORKSPACE_DIR)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_project_dir(self, project_id: str) -> Path:
        """Get the workspace directory for a specific project."""
        project_dir = self.workspace_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
    
    def _generate_file_hash(self, content: str) -> str:
        """Generate a hash of file content for duplicate detection."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_versioned_filename(self, directory: Path, filename: str) -> str:
        """
        Get a versioned filename if the file already exists.
        
        Examples:
            requirements.md -> requirements.md (if doesn't exist)
            requirements.md -> requirements_v2.md (if exists)
            requirements_v2.md -> requirements_v3.md (if v2 exists)
        """
        file_path = directory / filename
        
        if not file_path.exists():
            return filename
        
        # Extract name and extension
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            base_name, extension = name_parts
        else:
            base_name = filename
            extension = ""
        
        # Find next available version number
        version = 2
        while True:
            versioned_name = f"{base_name}_v{version}"
            if extension:
                versioned_name += f".{extension}"
            
            versioned_path = directory / versioned_name
            if not versioned_path.exists():
                return versioned_name
            
            version += 1
            
            # Safety limit
            if version > 100:
                logger.warning(f"Too many versions for {filename}, using timestamp")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return f"{base_name}_{timestamp}.{extension}" if extension else f"{base_name}_{timestamp}"
    
    async def save_generated_file(
        self, 
        project_id: str, 
        filename: str, 
        content: str,
        doc_type: str = "document",
        agent_name: str = "Unknown",
        auto_focus: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a generated file with versioning and emit event.
        
        Args:
            project_id: Project ID
            filename: Desired filename
            content: File content
            doc_type: Type of document (requirements, architecture, code, etc.)
            agent_name: Name of the agent that generated this file
            auto_focus: Whether to automatically focus this file in UI
            metadata: Additional metadata
        
        Returns:
            Dict with file info including path, filename, etc.
        """
        try:
            project_dir = self._get_project_dir(project_id)
            
            # Check for versioning
            final_filename = self._get_versioned_filename(project_dir, filename)
            file_path = project_dir / final_filename
            
            # Write file
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"Saved file: {file_path}")
            
            # Prepare file info
            file_info = {
                "filename": final_filename,
                "path": str(file_path.relative_to(self.workspace_dir)),
                "full_path": str(file_path),
                "doc_type": doc_type,
                "content": content[:500] + "..." if len(content) > 500 else content,  # Preview
                "full_content": content,
                "auto_focus": auto_focus,
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "size_bytes": len(content.encode('utf-8')),
                "content_hash": self._generate_file_hash(content),
                "metadata": metadata or {}
            }
            
            # Emit FILE_GENERATED event
            await self._emit_file_event(project_id, file_info)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            raise
    
    async def _emit_file_event(self, project_id: str, file_info: Dict[str, Any]):
        """Emit a FILE_GENERATED event via event bus."""
        try:
            # Emit workflow event
            await self.event_bus.emit(WorkflowEvent(
                event_type=EventType.FILE_GENERATED,
                timestamp=file_info["timestamp"],
                project_id=project_id,
                agent=file_info["agent"],
                message=f"Generated file: {file_info['filename']}",
                severity=EventSeverity.SUCCESS,
                data=file_info
            ))
            
            logger.info(f"Emitted FILE_GENERATED event for {file_info['filename']}")
            
        except Exception as e:
            logger.error(f"Failed to emit file event: {e}")
    
    def get_file_content(self, project_id: str, relative_path: str) -> Optional[str]:
        """
        Get file content by relative path.
        
        Args:
            project_id: Project ID
            relative_path: Relative path from project directory
        
        Returns:
            File content or None if not found
        """
        try:
            project_dir = self._get_project_dir(project_id)
            file_path = project_dir / relative_path
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            # Security check: ensure file is within project directory
            if not str(file_path.resolve()).startswith(str(project_dir.resolve())):
                logger.error(f"Security violation: attempted to access file outside project directory")
                return None
            
            return file_path.read_text(encoding='utf-8')
            
        except Exception as e:
            logger.error(f"Failed to read file {relative_path}: {e}")
            return None
    
    def list_files(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all files in a project.
        
        Args:
            project_id: Project ID
        
        Returns:
            List of file info dictionaries
        """
        try:
            project_dir = self._get_project_dir(project_id)
            files = []
            
            # Recursively find all files
            for file_path in project_dir.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(project_dir)
                    
                    files.append({
                        "filename": file_path.name,
                        "path": str(relative_path),
                        "full_path": str(file_path),
                        "size_bytes": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files for project {project_id}: {e}")
            return []
    
    def file_exists(self, project_id: str, filename: str) -> bool:
        """Check if a file exists in the project directory."""
        project_dir = self._get_project_dir(project_id)
        return (project_dir / filename).exists()


# Global instance
_file_manager = None

def get_file_manager() -> FileManager:
    """Get the global FileManager instance."""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager
