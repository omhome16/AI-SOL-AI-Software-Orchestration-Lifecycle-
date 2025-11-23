"""
Persistent State Manager for AI-SOL projects.
Handles saving and loading project state to/from disk.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent storage of project states."""
    
    def __init__(self, storage_path: str = "./workspace/.state"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.tz = ZoneInfo("Asia/Kolkata")
        self.load_all_projects()
    
    def _serialize_for_json(self, obj: Any, seen: Optional[set] = None) -> Any:
        """
        Recursively serialize objects to JSON-compatible format, avoiding circular references.
        
        Args:
            obj: Object to serialize
            seen: Set of object ids already processed (for circular reference detection)
            
        Returns:
            JSON-serializable object
        """
        if seen is None:
            seen = set()
        
        # Handle primitives directly (they don't have circular references)
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Get object id to track circular references for complex objects
        obj_id = id(obj)
        
        # If we've seen this object before, it's a circular reference
        if obj_id in seen:
            return f"<circular reference: {type(obj).__name__}>"
        
        # Add to seen set for complex objects
        seen.add(obj_id)
        
        try:
            # Handle different types
            if isinstance(obj, (list, tuple)):
                result = [self._serialize_for_json(item, seen.copy()) for item in obj]
                seen.discard(obj_id)
                return result
            elif isinstance(obj, dict):
                result = {key: self._serialize_for_json(value, seen.copy()) for key, value in obj.items()}
                seen.discard(obj_id)
                return result
            elif hasattr(obj, 'model_dump'):
                # Pydantic v2
                try:
                    dumped = obj.model_dump()
                    result = self._serialize_for_json(dumped, seen.copy())
                    seen.discard(obj_id)
                    return result
                except Exception:
                    seen.discard(obj_id)
                    return str(obj)
            elif hasattr(obj, 'dict'):
                # Pydantic v1
                try:
                    dumped = obj.dict()
                    result = self._serialize_for_json(dumped, seen.copy())
                    seen.discard(obj_id)
                    return result
                except Exception:
                    seen.discard(obj_id)
                    return str(obj)
            elif hasattr(obj, '__dict__'):
                # Regular class instance
                try:
                    result = self._serialize_for_json(obj.__dict__, seen.copy())
                    seen.discard(obj_id)
                    return result
                except Exception:
                    seen.discard(obj_id)
                    return str(obj)
            else:
                # Fallback to string representation
                seen.discard(obj_id)
                return str(obj)
        except Exception as e:
            seen.discard(obj_id)
            logger.error(f"Serialization error for {type(obj).__name__}: {e}")
            return f"<serialization error: {type(obj).__name__}>"
    
    def save_project(self, project_id: str, project_data: Dict[str, Any]) -> bool:
        """
        Save project state to disk.
        
        Args:
            project_id: Unique project identifier
            project_data: Complete project state dictionary
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Add metadata
            project_data["last_saved"] = datetime.now(self.tz).isoformat()
            
            # Serialize to avoid circular references
            safe_data = self._serialize_for_json(project_data)
            
            # Save to disk
            file_path = self.storage_path / f"{project_id}.json"
            file_path.write_text(
                json.dumps(safe_data, indent=2),
                encoding="utf-8"
            )
            
            # Update in-memory cache
            self.projects[project_id] = safe_data
            
            logger.info(f"Saved project state: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save project {project_id}: {e}")
            return False
    
    def load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Load project state from disk.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Optional[Dict]: Project data if found, None otherwise
        """
        try:
            # Check cache first
            if project_id in self.projects:
                return self.projects[project_id]
            
            # Load from disk
            file_path = self.storage_path / f"{project_id}.json"
            if file_path.exists():
                data = json.loads(file_path.read_text(encoding="utf-8"))
                self.projects[project_id] = data
                logger.info(f"Loaded project state: {project_id}")
                return data
            else:
                logger.warning(f"Project not found: {project_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load project {project_id}: {e}")
            return None
    
    def load_all_projects(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all projects on startup.
        
        Returns:
            Dict: All loaded projects
        """
        try:
            count = 0
            for file in self.storage_path.glob("*.json"):
                project_id = file.stem
                try:
                    data = json.loads(file.read_text(encoding="utf-8"))
                    self.projects[project_id] = data
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to load project file {file}: {e}")
            
            logger.info(f"Loaded {count} projects from disk")
            return self.projects
            
        except Exception as e:
            logger.error(f"Failed to load projects: {e}")
            return {}
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete project state from disk and memory.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            bool: True if delete successful, False otherwise
        """
        try:
            # Remove from disk
            file_path = self.storage_path / f"{project_id}.json"
            if file_path.exists():
                file_path.unlink()
            
            # Remove from memory
            if project_id in self.projects:
                del self.projects[project_id]
            
            logger.info(f"Deleted project: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects with basic metadata.
        
        Returns:
            List[Dict]: List of project summaries
        """
        summaries = []
        for project_id, data in self.projects.items():
            state = data.get("state", {})
            summaries.append({
                "project_id": project_id,
                "project_name": state.get("project_name", "Unknown"),
                "status": state.get("status", "unknown"),
                "current_step": state.get("current_step", ""),
                "steps_completed": state.get("steps_completed", []),
                "created_at": state.get("created_at", ""),
                "last_saved": data.get("last_saved", "")
            })
        return summaries
    
    def update_project_state(self, project_id: str, state_updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in project state.
        
        Args:
            project_id: Unique project identifier
            state_updates: Dictionary of state updates
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            project = self.load_project(project_id)
            if not project:
                logger.error(f"Cannot update non-existent project: {project_id}")
                return False
            
            # Update state fields
            if "state" not in project:
                project["state"] = {}
            
            project["state"].update(state_updates)
            
            # Save updated project
            return self.save_project(project_id, project)
            
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            return False
    
    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project status summary.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Optional[Dict]: Status summary if found, None otherwise
        """
        project = self.load_project(project_id)
        if not project:
            return None
        
        # Support both nested "state" and flat structure
        state = project.get("state", project)
        return {
            "project_id": project_id,
            "status": state.get("status", "unknown"),
            "current_step": state.get("current_step"),
            "steps_completed": state.get("steps_completed", []),
            "generated_files": state.get("generated_files", [])
        }
    
    def clear_all(self) -> bool:
        """
        Clear all project data (use with caution).
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for file in self.storage_path.glob("*.json"):
                file.unlink()
            self.projects.clear()
            logger.warning("Cleared all project data")
            return True
        except Exception as e:
            logger.error(f"Failed to clear projects: {e}")
            return False


# Global instance
_state_manager_instance: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """
    Get or create the global StateManager instance.
    
    Returns:
        StateManager: The global state manager instance
    """
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance
