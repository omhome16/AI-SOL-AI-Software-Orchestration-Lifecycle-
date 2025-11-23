import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from backend.core.state_manager import StateManager
from backend.core.workflow import WorkflowEngine
from orchestrator.central import CentralOrchestrator
from backend.core.config import Config

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        # In-memory storage for active engines and orchestrators
        # Key: project_id, Value: {"engine": WorkflowEngine, "orchestrator": CentralOrchestrator}
        self._active_engines: Dict[str, Dict[str, Any]] = {}

    async def create_project(self, project_req: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project and initialize its state."""
        project_name = project_req.get("project_name")
        requirements = project_req.get("requirements")
        
        # Create initial state
        project_id = f"proj-{int(datetime.now().timestamp())}"
        
        # Initialize state with defaults
        initial_state = {
            "project_id": project_id,
            "name": project_name,  # IMPORTANT: Store as "name" not "project_name"
            "project_name": project_name,  # Keep both for compatibility
            "type": project_req.get("project_type", "website"),  # Add type at top level
            "requirements": requirements,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "steps": [],
            "steps_completed": [],
            "logs": [],
            "files": [],
            "generated_files": [],  # Track generated files with metadata
            "current_step": None,
            "completed": False,
            # User context for LLM
            "user_context": {
                "project_name": project_name,
                "project_type": project_req.get("project_type", "website"),
                "requirements": requirements
            },
            # Advanced options
            "enable_github": project_req.get("enable_github", False),
            "github_username": project_req.get("github_username", ""),
            "github_token": project_req.get("github_token", ""),
            "generate_tests": project_req.get("generate_tests", False),
            "generate_devops": project_req.get("generate_devops", False)
        }
        
        # Save to persistent storage
        self.state_manager.save_project(project_id, initial_state)
        
        logger.info(f"[PROJECT] Created new project: {project_name} (ID: {project_id})")
        
        return initial_state

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project details."""
        return self.state_manager.load_project(project_id)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        return self.state_manager.list_projects()

    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        # Stop active engine if running
        if project_id in self._active_engines:
            del self._active_engines[project_id]
            
        return self.state_manager.delete_project(project_id)

    async def start_workflow(self, project_id: str, background_tasks=None) -> Dict[str, Any]:
        """Start or resume a workflow for a project."""
        logger.info(f"[WORKFLOW] Starting workflow for project {project_id}")
        
        project_data = self.get_project(project_id)
        if not project_data:
            raise ValueError("Project not found")
            
        state = project_data
        
        # CRITICAL: Add project name to state for LLM branding
        project_name = project_data.get("name") or project_data.get("project_name", "Unnamed Project")
        state["project_name"] = project_name
        
        if "user_context" not in state:
            state["user_context"] = {}
        state["user_context"]["project_name"] = project_name
        
        # ADD CONFIGURATION TO STATE FOR LLM
        if "configuration" in project_data:
            state["user_context"]["configuration"] = project_data["configuration"]
            logger.info(f"[WORKFLOW] Added configuration to LLM context: {list(project_data['configuration'].keys())}")
        
        # ADD IMAGES TO STATE FOR LLM  
        from pathlib import Path
        from backend.core.config import Config
        
        # Check for inspiration images (from requirements page)
        inspiration_dir = Path(Config.WORKSPACE_DIR) / project_id / "inspiration_images"
        if inspiration_dir.exists():
            image_files = list(inspiration_dir.glob("*"))
            if image_files:
                state["user_context"]["inspiration_images"] = [str(img) for img in image_files]
                logger.info(f"[WORKFLOW] Found {len(image_files)} inspiration images")
        
        logger.info(f"[WORKFLOW] Project name: '{project_name}'")
        logger.info(f"[WORKFLOW] Project type: {state.get('user_context', {}).get('project_type', 'unknown')}")
        
        # Import WebSocket manager
        from backend.api.websocket import manager as websocket_manager
        
        # Initialize Orchestrator
        orchestrator = CentralOrchestrator(tools=[])
        
        # Initialize Workflow Engine with WebSocket connection manager
        logger.info(f"[WORKFLOW] Creating WorkflowEngine instance")
        engine = WorkflowEngine(
            project_id, 
            orchestrator, 
            state, 
            connection_manager=websocket_manager,
            state_manager=self.state_manager
        )
        
        # Store active instances
        self._active_engines[project_id] = {
            "engine": engine,
            "orchestrator": orchestrator
        }
        
        logger.info(f"[WORKFLOW] Stored engine in _active_engines for {project_id}")
        logger.info(f"[WORKFLOW] Active engines count: {len(self._active_engines)}")
        logger.info(f"[WORKFLOW] Engine stored successfully: {project_id in self._active_engines}")
        
        # Start workflow in background
        logger.info(f"[WORKFLOW] Launching workflow engine as background task")
        if background_tasks:
            background_tasks.add_task(engine.run)
        else:
            asyncio.create_task(engine.run())
        
        logger.info(f"[WORKFLOW] Workflow started successfully for {project_id}")
        return {"status": "started", "project_id": project_id}

    async def resume_workflow(self, project_id: str) -> Dict[str, Any]:
        """Resume a paused workflow."""
        logger.info(f"[WORKFLOW] Attempting to resume workflow for {project_id}")
        
        if project_id in self._active_engines:
            engine = self._active_engines[project_id]["engine"]
            await engine.resume()
            logger.info(f"[WORKFLOW] Workflow resumed for {project_id}")
            return {"status": "resumed"}
        else:
            logger.warning(f"[WORKFLOW] No active engine found for {project_id}")
            return {"status": "error", "message": "Workflow not active in memory. Please use restart."}

    async def process_chat_message(self, project_id: str, message: str) -> Dict[str, Any]:
        """Process a chat message for a project."""
        # Get active components
        if project_id not in self._active_engines:
             logger.warning(f"[CHAT] Project {project_id} not active in memory")
             return {"status": "error", "message": "Project not active. Please restart the project."}
             
        workflow_engine = self._active_engines[project_id].get("engine")
        chat_orchestrator = self._active_engines[project_id].get("orchestrator")
        
        if not chat_orchestrator:
             return {"status": "error", "message": "Chat orchestrator not initialized"}

        # Add user message to history
        chat_orchestrator.add_to_history(project_id, "user", message)
        
        # Process the message
        logger.info(f"[CHAT] Sending message to orchestrator")
        response = await chat_orchestrator.process_message(project_id, message)
        logger.info(f"[CHAT] Orchestrator response action: {response.get('action')}")
        
        # === APPROVAL WORKFLOW INTEGRATION ===
        # If user approved, automatically resume the workflow
        if response.get("action") == "resume_workflow" or response.get("action") == "approve":
            logger.info(f"[APPROVAL] Detected approval action for {project_id}")
            if workflow_engine:
                logger.info(f"[APPROVAL] Resuming workflow engine")
                await workflow_engine.resume()
                logger.info(f"[APPROVAL] Workflow resumed successfully for project {project_id}")
            else:
                logger.error(f"[APPROVAL] Cannot resume - no workflow engine found")
        
        # Add AI response to history
        chat_orchestrator.add_to_history(project_id, "ai", response["message"], 
                                        metadata={"buttons": response.get("buttons")})
        
        # Broadcast via WebSocket if engine is available
        if workflow_engine:
            # Broadcast user message
            logger.info(f"[CHAT] Broadcasting user message via WebSocket")
            await workflow_engine.broadcast({
                "type": "CHAT_MESSAGE",
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Broadcast AI response
            logger.info(f"[CHAT] Broadcasting AI response via WebSocket")
            await workflow_engine.broadcast({
                "type": "CHAT_RESPONSE",
                "role": "ai",
                "content": response["message"],
                "timestamp": datetime.now().isoformat(),
                "buttons": response.get("buttons", []),
                "action": response.get("action")
            })
        
        logger.info(f"[CHAT] Message processing complete")
        return response

    def get_active_engine(self, project_id: str) -> Optional[WorkflowEngine]:
        """Get the active workflow engine for a project."""
        if project_id in self._active_engines:
            return self._active_engines[project_id]["engine"]
        return None
