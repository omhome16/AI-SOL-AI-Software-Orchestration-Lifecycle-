"""
AI-SOL Workflow Engine
Manages the execution of AI-SOL workflow stages with interactive pause/resume capability.
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from backend.core.config import Config
from backend.core.event_bus import get_event_bus, WorkflowEvent, EventType, EventSeverity
from backend.core.master_orchestrator import MasterOrchestrator
from backend.core.markdown_formatter import get_markdown_formatter
from orchestrator.central import CentralOrchestrator
from agents.requirements import RequirementsAgent
from agents.architect import ArchitectAgent
from agents.developer import DeveloperAgent
from agents.qa import QAAgent
from agents.devops import DevOpsAgent
from agents.chat_agent import ChatAgent

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Manages the execution of the AI-SOL workflow stages with interactive pause/resume.
    Supports human-in-the-loop review at each stage.
    """

    def __init__(self, project_id: str, orchestrator: CentralOrchestrator, state: Dict[str, Any], 
                 connection_manager=None, state_manager=None):
        """
        Initialize the workflow engine.
        
        Args:
            project_id: Unique project identifier
            orchestrator: Central orchestrator for agent coordination
            state: Project state dictionary
            connection_manager: WebSocket connection manager for real-time updates
            state_manager: State persistence manager
        """
        self.project_id = project_id
        self.orchestrator = orchestrator
        self.state = state
        self.tools = orchestrator.tools
        self.connection_manager = connection_manager
        self.state_manager = state_manager
        self.pause_event = asyncio.Event()
        self.event_bus = get_event_bus()
        self.markdown_formatter = get_markdown_formatter()
        
        # Initialize ChatAgent for all communication
        self.chat_agent = ChatAgent(project_id, websocket_manager=connection_manager)
        
        # Initialize MasterOrchestrator for intelligent workflow guidance
        self.master_orchestrator = MasterOrchestrator(project_id, context_store=None)
        
        logger.info(f"[INIT] WorkflowEngine initialized for project {project_id}")

    async def broadcast(self, message):
        """
        Send a message to the frontend via WebSocket.
        
        Args:
            message: String message or dict with type/data
        """
        if self.connection_manager:
            try:
                if isinstance(message, dict):
                    await self.connection_manager.broadcast_json(message, self.project_id)
                else:
                    await self.connection_manager.broadcast(message, self.project_id)
            except Exception as e:
                logger.warning(f"Failed to broadcast message: {e}")
        
        # Save to logs if state_manager available
        if self.state_manager:
            try:
                project = self.state_manager.load_project(self.project_id)
                if project:
                    if "logs" not in project:
                        project["logs"] = []
                    log_entry = message["message"] if isinstance(message, dict) and "message" in message else str(message)
                    project["logs"].append(log_entry)
                    self.state_manager.save_project(self.project_id, project)
            except Exception as e:
                logger.warning(f"Failed to save log to state: {e}")

    async def resume(self):
        """Resume the workflow from a paused state."""
        logger.info(f"🔄 Resuming workflow for {self.project_id}")
        self.pause_event.set()

    async def _send_greeting(self):
        """Send greeting message to user when workflow starts."""
        try:
            await self.chat_agent.send_greeting()
            logger.info("[SUCCESS] Greeting sent via ChatAgent")
        except Exception as e:
            logger.error(f"Failed to send greeting: {e}")
            # Fallback to direct broadcast
            await self.broadcast({
                "type": "CHAT_RESPONSE",
                "message": "Workflow started. Analyzing your requirements...",
                "action": "workflow_greeting",
                "timestamp": datetime.now().isoformat(),
                "buttons": []
            })

    async def _request_user_review(self, stage_name: str):
        """
        Request user review after stage completion.
        Pauses workflow until user approves via chat.
        
        Args:
            stage_name: Name of the completed stage
        """
        logger.info(f"[REVIEW] Requesting user review for {stage_name}")
        
        generated_files = self.state.get("generated_files", [])
        stage_files = [f for f in generated_files if stage_name in f.get("metadata", {}).get("stage", "")]
        file_names = [f["filename"] for f in stage_files] if stage_files else [f"{stage_name}.md"]
        
        stage_messages = {
            "requirements": f"📋 Requirements document generated: {', '.join(file_names)}. Please review in the file viewer.",
            "architecture": f"🏗️ Architecture design completed: {', '.join(file_names)}. Please review.",
            "developer": f"💻 Code implementation finished: {', '.join(file_names)}. Please review.",
            "qa": f"🧪 Testing completed: {', '.join(file_names)}. Please review.",
            "devops": f"🚀 DevOps configuration ready: {', '.join(file_names)}. Please review."
        }
        
        message = stage_messages.get(stage_name, f"✅ {stage_name.capitalize()} complete. File: {', '.join(file_names)}")
        
        # Notify user file is ready
        await self.broadcast({
            "type": "CHAT_RESPONSE",
            "message": message,
            "action": "file_ready",
            "timestamp": datetime.now().isoformat(),
            "buttons": []
        })
        
        # Send AWAITING_REVIEW event to show approve button
        await self.broadcast({
            "type": "AWAITING_REVIEW",
            "stage": stage_name,
            "files": file_names,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update state
        self.state["status"] = "awaiting_review"
        self.state["awaiting_review"] = True
        self.state["review_stage"] = stage_name
        
        # Emit event
        await self.event_bus.emit(WorkflowEvent(
            event_type=EventType.APPROVAL_REQUESTED,
            timestamp=datetime.now().isoformat(),
            project_id=self.project_id,
            stage=stage_name,
            agent="WorkflowEngine",
            message=f"Requesting approval for {stage_name}",
            severity=EventSeverity.INFO,
            data={"files": file_names}
        ))
        
        # Wait for user approval
        logger.info(f"[PAUSED] Workflow paused, waiting for approval of {stage_name}")
        await self.pause_event.wait()
        
        # Clear pause state
        self.pause_event.clear()
        self.state["status"] = "running"
        self.state["awaiting_review"] = False
        self.state["review_stage"] = None
        
        # Notify user we're proceeding
        await self.broadcast({
            "type": "CHAT_RESPONSE",
            "message": f"Proceeding to next stage...",
            "action": "approved",
            "timestamp": datetime.now().isoformat(),
            "buttons": []
        })
        
        logger.info(f"[APPROVED] User approved {stage_name}, resuming workflow")
    
    async def resume(self):
        """
        Resume the paused workflow.
        Called when user approves a stage.
        """
        logger.info(f"[RESUME] Resume called, setting pause_event")
        self.pause_event.set()
        logger.info(f"[RESUME] Pause event set, workflow will continue")

    async def run(self):
        """Run the full workflow through all stages."""
        heartbeat_task = None
        try:
            logger.info(f"[START] Starting workflow for {self.project_id}")
            await self.broadcast("LOG:Workflow started")
            
            await self.event_bus.emit(WorkflowEvent(
                event_type=EventType.WORKFLOW_STARTED,
                timestamp=datetime.now().isoformat(),
                project_id=self.project_id,
                message="AI-SOL workflow started",
                severity=EventSeverity.INFO
            ))
            
            # Send greeting
            await self._send_greeting()
            
            # Start heartbeat to show activity
            heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Get user preferences
            user_context = self.state.get("user_context", {})
            generate_tests = user_context.get("generate_tests", True)
            generate_devops = user_context.get("generate_devops", True)
            
            # === STAGE 1: Requirements ===
            await self._run_stage("requirements", RequirementsAgent)
            await self._save_checkpoint("requirements")
            await self._request_user_review("requirements")
            
            # === STAGE 2: Architecture ===
            await self._run_stage("architecture", ArchitectAgent)
            await self._save_checkpoint("architecture")
            await self._request_user_review("architecture")
            
            # === STAGE 3: Developer ===
            dev_agent = DeveloperAgent(self.tools)
            qa_agent = QAAgent(self.tools)
            self.orchestrator.register_agents({'developer': dev_agent, 'qa': qa_agent})
            
            await self._run_stage("developer", DeveloperAgent, use_orchestrator=True)
            await self._save_checkpoint("developer")
            await self._request_user_review("developer")
            
            # === STAGE 4: QA (Conditional) ===
            if str(generate_tests).lower() == "true":
                await self._run_stage("qa", QAAgent)
                await self._save_checkpoint("qa")
                await self._request_user_review("qa")
            else:
                logger.info("[SKIP] Skipping QA stage (disabled by user)")
                await self.broadcast("LOG:Skipping QA stage (disabled by user)")
                self.state["steps_completed"].append("qa")
            
            # === STAGE 5: DevOps (Conditional) ===
            if str(generate_devops).lower() == "true":
                await self._run_stage("devops", DevOpsAgent)
                await self._save_checkpoint("devops")
            else:
                logger.info("[SKIP] Skipping DevOps stage (disabled by user)")
                await self.broadcast("LOG:Skipping DevOps stage (disabled by user)")
                self.state["steps_completed"].append("devops")
            
            # Workflow complete
            logger.info(f"[COMPLETE] Workflow completed for {self.project_id}")
            self.state["status"] = "completed"
            await self.broadcast("COMPLETED:Workflow finished successfully")
            
        except Exception as e:
            logger.error(f"[ERROR] Workflow failed for {self.project_id}: {e}", exc_info=True)
            self.state["status"] = "failed"
            self.state["error"] = str(e)
            await self.broadcast(f"ERROR:{str(e)}")
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()

    async def _heartbeat(self):
        """Periodically send signals to show workflow is active."""
        while True:
            await asyncio.sleep(10)
            if self.state.get("status") == "running":
                await self.broadcast("LOG:Working...")

    async def _save_checkpoint(self, stage_name: str):
        """
        Save workflow state after completing a stage.
        
        Args:
            stage_name: Name of the completed stage
        """
        if self.state_manager:
            try:
                # Save state directly to avoid nesting/recursion since self.state IS the project state
                self.state_manager.save_project(self.project_id, self.state)
                logger.info(f"[CHECKPOINT] Saved after {stage_name}")
            except Exception as e:
                logger.warning(f"Failed to save checkpoint: {e}")

    async def _save_and_broadcast_file(self, stage_name: str, output: Dict[str, Any]):
        """
        Generate markdown file from agent output and broadcast to frontend.
        Uses LLM-based markdown formatter for human-readable output.
        
        Args:
            stage_name: Name of the stage (requirements, architecture, etc.)
            output: Raw agent output with Pydantic models
        """
        try:
            from backend.utils.file_manager import get_file_manager
            file_manager = get_file_manager()
            
            # Detect project type from state
            project_type = self.state.get("user_context", {}).get("project_type", "website")
            
            # Use LLM formatter to create beautiful markdown
            logger.info(f"[FORMAT] Formatting {stage_name} output with LLM formatter (type={project_type})")
            content = await self.markdown_formatter.format(stage_name, output, project_type)
            
            filename = f"{stage_name}.md"
            
            # Save file using file manager
            file_info = await file_manager.save_generated_file(
                project_id=self.project_id,
                filename=filename,
                content=content,
                doc_type=stage_name,
                agent_name=f"{stage_name.capitalize()}Agent",
                auto_focus=True,
                metadata={"stage": stage_name, "project_type": project_type}
            )
            
            # Add to state
            if "generated_files" not in self.state:
                self.state["generated_files"] = []
            self.state["generated_files"].append(file_info)
            
            # Broadcast FILE_GENERATED event to frontend
            await self.broadcast({
                "type": "FILE_GENERATED",
                "filename": file_info["filename"],
                "path": file_info["path"],
                "doc_type": file_info["doc_type"],
                "content": content[:200],  # Preview
                "full_content": content,
                "auto_focus": True,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"[SUCCESS] Generated and broadcast file: {filename} ({len(content)} chars)")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to save/broadcast file for {stage_name}: {e}", exc_info=True)

    async def _run_stage(self, stage_name: str, AgentClass, use_orchestrator=False):
        """
        Execute a specific workflow stage.
        
        Args:
            stage_name: Name of the stage
            AgentClass: Agent class to instantiate
            use_orchestrator: Whether to use central orchestrator for this stage
        """
        logger.info(f"[STAGE] Starting stage: {stage_name}")
        await self.broadcast(f"STARTED:{stage_name}")
        self.state["current_step"] = stage_name
        
        agent_name = AgentClass.__name__ if not use_orchestrator else "CentralOrchestrator"
        
        # Emit stage started event
        await self.event_bus.emit(WorkflowEvent(
            event_type=EventType.STAGE_STARTED,
            timestamp=datetime.now().isoformat(),
            project_id=self.project_id,
            stage=stage_name,
            agent=agent_name,
            message=f"Starting {stage_name} stage",
            severity=EventSeverity.INFO
        ))
        
        # Check if already completed
        if stage_name in self.state.get("steps_completed", []):
            logger.info(f"[SKIP] Stage {stage_name} already completed, skipping")
            await self.broadcast(f"LOG:Skipping {stage_name} (already done)")
            return

        try:
            # Special handling for developer stage with orchestrator
            if use_orchestrator and stage_name == "developer":
                await self.broadcast(f"LOG:Starting Developer Agent (Orchestrated)...")
                
                await self.event_bus.emit(WorkflowEvent(
                    event_type=EventType.AGENT_THINKING,
                    timestamp=datetime.now().isoformat(),
                    project_id=self.project_id,
                    stage=stage_name,
                    agent="CentralOrchestrator",
                    message="Orchestrator executing build plan...",
                    severity=EventSeverity.INFO
                ))
                
                build_res = await self.orchestrator.execute_build_plan(self.state)
                self.state["developer_output"] = build_res
                
                if build_res.get("success", True):
                    self.state["steps_completed"].append(stage_name)
                    await self.broadcast(f"LOG:Developer stage finished")
                    
                    await self.event_bus.emit(WorkflowEvent(
                        event_type=EventType.STAGE_COMPLETED,
                        timestamp=datetime.now().isoformat(),
                        project_id=self.project_id,
                        stage=stage_name,
                        agent="CentralOrchestrator",
                        message=f"Completed {stage_name} stage successfully",
                        severity=EventSeverity.SUCCESS
                    ))
                return

            # Standard agent execution
            await self.broadcast(f"LOG:Running {stage_name} agent...")
            
            # Announce agent start via ChatAgent
            agent_descriptions = {
                "requirements": "Analyzing your requirements and creating specifications",
                "architecture": "Designing the system architecture and components",
                "developer": "Generating code and implementing the solution",
                "qa": "Creating tests and validating the implementation",
                "devops": "Setting up deployment and infrastructure"
            }
            description = agent_descriptions.get(stage_name, "Working on your project")
            await self.chat_agent.announce_agent_start(stage_name.capitalize(), description)
            
            await self.event_bus.emit(WorkflowEvent(
                event_type=EventType.AGENT_THINKING,
                timestamp=datetime.now().isoformat(),
                project_id=self.project_id,
                stage=stage_name,
                agent=agent_name,
                message=f"{agent_name} analyzing and planning...",
                severity=EventSeverity.INFO
            ))
            
            # Create agent instance
            agent = AgentClass(self.tools)
            agent.set_log_callback(self.broadcast)
            
            # Execute agent
            logger.info(f"[EXEC] Executing {stage_name} agent...")
            output = await agent.execute(self.state)
            logger.info(f"[SUCCESS] Agent execution complete for {stage_name}")
            
            # Update state with output
            self.state.update(output)
            
            # Generate and broadcast markdown file
            logger.info(f"[FILE] Generating markdown file for {stage_name}...")
            await self._save_and_broadcast_file(stage_name, output)
            logger.info(f"[SUCCESS] File generation complete for {stage_name}")
            
            # Check for success
            is_success = (
                output.get("success", False) or
                output.get(f"{stage_name}_output", {}).get("success", False) or
                output.get("status") == "awaiting_review" or
                stage_name in output.get("steps_completed", [])
            )

            if not is_success:
                # Check for explicit errors in output
                errors = output.get("errors", [])
                if errors:
                    error_msg = f"Stage {stage_name} failed with errors: {errors}"
                else:
                    error_msg = output.get("error", f"Stage {stage_name} failed - no success indicator")
                
                logger.error(f"[ERROR] {error_msg}")
                raise Exception(error_msg)
            
            logger.info(f"[CHECK] Success check for {stage_name}: {is_success}")
            
            if is_success:
                # Mark as completed
                if stage_name not in self.state.get("steps_completed", []):
                    self.state.setdefault("steps_completed", []).append(stage_name)
                
                await self.broadcast(f"LOG:{stage_name} agent finished successfully")
                
                # Announce agent completion via ChatAgent
                summary = f"Generated {len(output.get('generated_files', []))} file(s)"
                await self.chat_agent.announce_agent_complete(stage_name.capitalize(), summary)
                
                await self.event_bus.emit(WorkflowEvent(
                    event_type=EventType.STAGE_COMPLETED,
                    timestamp=datetime.now().isoformat(),
                    project_id=self.project_id,
                    stage=stage_name,
                    agent=agent_name,
                    message=f"Completed {stage_name} stage successfully",
                    data={"output": output},
                    severity=EventSeverity.SUCCESS
                ))
            else:
                error_msg = output.get("error", f"Stage {stage_name} failed - no success indicator")
                raise Exception(error_msg)
        
        except Exception as e:
            logger.error(f"[ERROR] Stage {stage_name} failed: {e}", exc_info=True)
            await self.event_bus.emit(WorkflowEvent(
                event_type=EventType.STAGE_FAILED,
                timestamp=datetime.now().isoformat(),
                project_id=self.project_id,
                stage=stage_name,
                agent=agent_name,
                message=f"Stage {stage_name} failed: {str(e)}",
                data={"error": str(e)},
                severity=EventSeverity.ERROR
            ))
            raise
