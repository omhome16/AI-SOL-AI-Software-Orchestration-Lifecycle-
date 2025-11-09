from zoneinfo import ZoneInfo
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from core.state import WorkflowState, TaskStatus
from orchestrator.central import CentralOrchestrator
from agents.requirements import RequirementsAgent
from agents.architect import ArchitectAgent
from agents.developer import DeveloperAgent
from agents.qa import QAAgent
from agents.devops import DevOpsAgent
from typing import Literal, Any, Dict
from datetime import datetime
from core.config import Config
import os
# Import necessary for modification logic
import time
import logging

logger = logging.getLogger(__name__)


class WorkflowGraph:
    """LangGraph workflow with all agents"""

    def get_graph(self) -> StateGraph:
        """Get the graph."""
        return self.graph

    def get_app(self):
        """Get the app."""
        return self.app

    def __init__(self, tools: Any):
        self.tools = tools

        # Initialize all agents
        self.orchestrator = CentralOrchestrator(tools)
        self.requirements_agent = RequirementsAgent(tools)
        self.architect_agent = ArchitectAgent(tools)
        self.developer_agent = DeveloperAgent(tools)
        self.qa_agent = QAAgent(tools)
        self.devops_agent = DevOpsAgent(tools)

        # Build graph
        self.graph = self._build_graph()
        self.memory = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.memory)

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow"""

        workflow = StateGraph(WorkflowState)

        # Add agent nodes
        #
        # --- FIX 1: Renamed node "requirements" to "run_requirements" ---
        #
        workflow.add_node("run_requirements", self.requirements_agent.execute)
        workflow.add_node("architecture", self.architect_agent.execute)
        workflow.add_node("developer", self.developer_agent.execute)
        workflow.add_node("qa", self.qa_agent.execute)
        workflow.add_node("devops", self.devops_agent.execute)
        workflow.add_node("finalize", self._finalize)

        # Define workflow edges
        #
        # --- FIX 2: Updated START edge ---
        #
        workflow.add_edge(START, "run_requirements")
        #
        # --- FIX 3: Updated outgoing edge ---
        #
        workflow.add_edge("run_requirements", "architecture")
        workflow.add_edge("architecture", "developer")
        workflow.add_edge("developer", "qa")
        workflow.add_edge("qa", "devops")
        workflow.add_edge("devops", "finalize")
        workflow.add_edge("finalize", END)

        return workflow

    async def _orchestrator_decision(self, state: WorkflowState) -> WorkflowState:
        """Orchestrator makes decision using ReAct"""

        # Determine context
        last_step = state["steps_completed"][-1] if state["steps_completed"] else "start"
        context = f"Just completed: {last_step}"

        self.orchestrator.log(f"DEBUG: State before orchestrator decision: {state.get('requirements_output')}", "debug")

        # Get orchestrator decision
        try:
            decision = await self.orchestrator.reason_and_act(state, context)

            # Defensive normalization: ensure we always have a dict
            if decision is None:
                self.orchestrator.log("ERROR: Orchestrator reason_and_act returned None unexpectedly.", "error")
                decision = {
                    "thought": "Orchestrator returned None",
                    "action": "proceed",
                    "action_details": {}
                }
            elif not isinstance(decision, dict):
                # Convert pydantic models or other objects to dict safely
                if hasattr(decision, "dict"):
                    try:
                        decision = decision.dict()
                    except Exception:
                        decision = {"thought": str(decision), "action": "proceed", "action_details": {}}
                else:
                    try:
                        decision = dict(decision)
                    except Exception:
                        decision = {
                            "thought": "Could not normalize orchestrator decision",
                            "action": "proceed",
                            "action_details": {}
                        }

        except Exception as e:
            self.orchestrator.log(f"ERROR: Orchestrator reason_and_act failed: {e}", "error")
            decision = {
                "thought": f"Orchestrator failed: {e}",
                "action": "proceed",
                "action_details": {}
            }

        self.orchestrator.log(f"DEBUG: State after orchestrator decision: {state.get('requirements_output')}", "debug")

        # Record decision safely
        action_for_state = decision.get("action") if isinstance(decision, dict) else "proceed"
        state["current_step"] = action_for_state

        # Track retry count to prevent infinite loops
        retry_count = state.get("retry_count", {})
        if action_for_state in retry_count:
            state["retry_count"][action_for_state] += 1
        else:
            state["retry_count"][action_for_state] = 1

        # Check for excessive retries with better validation
        max_retries = 5  # Increased from 3 to 5
        if retry_count.get(action_for_state, 0) > max_retries:
            # Check if the previous step actually produced output before forcing progression
            previous_step_output = None
            if action_for_state == "architecture" and state.get("requirements_output"):
                previous_step_output = state["requirements_output"]
            elif action_for_state == "developer" and state.get("architecture_output"):
                previous_step_output = state["architecture_output"]
            elif action_for_state == "qa" and state.get("developer_output"):
                previous_step_output = state["developer_output"]
            elif action_for_state == "devops" and state.get("qa_output"):
                previous_step_output = state["qa_output"]

            # Only force progression if previous step has some output
            if previous_step_output and previous_step_output.get("success", False):
                self.orchestrator.log(f"Too many retries for {action_for_state}, forcing progression", "warning")
                # Force completion of current step
                if action_for_state not in state.get("steps_completed", []):
                    state["steps_completed"].append(action_for_state)
                # Reset retry count for this step
                state["retry_count"][action_for_state] = 0
            else:
                self.orchestrator.log(f"Previous step incomplete, not forcing progression for {action_for_state}",
                                      "warning")
                # Add exponential backoff
                import time
                time.sleep(min(2 ** retry_count.get(action_for_state, 0), 30))  # Max 30 seconds

        # Skip human input checks - proceed automatically

        return state

    def _route_from_orchestrator(self, state: WorkflowState) -> Literal[
        "architecture", "developer", "qa", "devops", "human_input", "complete"]:
        """Route based on orchestrator decision and current progress"""

        # Skip human input - proceed automatically

        # Check what's completed
        completed = set(state.get("steps_completed", []))

        # Check for excessive retries and force completion if needed
        retry_count = state.get("retry_count", {})
        max_retries = 3

        # If any step has exceeded max retries, force progression
        for step in ["requirements", "architecture", "developer", "qa", "devops"]:
            if retry_count.get(step, 0) > max_retries and step not in completed:
                self.orchestrator.log(f"Step {step} exceeded max retries, forcing completion", "warning")
                completed.add(step)
                state["steps_completed"] = list(completed)

        # Sequential flow with quality gates
        if "requirements" in completed and "architecture" not in completed:
            return "architecture"
        elif "architecture" in completed and "developer" not in completed:
            return "developer"
        elif "developer" in completed and "qa" not in completed:
            return "qa"
        elif "qa" in completed and "devops" not in completed:
            return "devops"
        else:
            return "complete"

    async def _finalize(self, state: WorkflowState) -> WorkflowState:
        """Finalize project with comprehensive state management"""
        tz = ZoneInfo("Asia/Kolkata")
        project_id = state["project_name"]

        state["status"] = TaskStatus.COMPLETED
        state["current_step"] = "complete"
        state["completed_at"] = datetime.now(tz).isoformat()

        # Complete project in orchestrator's state management
        self.orchestrator.complete_project(project_id, state)

        # Save project memory for future learning
        metadata = {
            "requirements": state["requirements"],
            "complexity": (state.get("requirements_output") or {}).get("data", {}).get("complexity"),
            "quality_score": state.get("code_quality_score"),
            "files_generated": len(state.get("generated_files", [])),
            "architecture_pattern": (state.get("architecture_output") or {}).get("data", {}).get("architecture_pattern")
        }

        self.tools.save_project_memory(
            project_name=state["project_name"],
            metadata=metadata
        )

        return state

    async def run(self, state: WorkflowState) -> WorkflowState:
        """Execute workflow"""

        config = {"configurable": {"thread_id": state["task_id"]}}

        final_state = None
        async for s in self.app.astream(state, config):
            # Stream updates
            for node_name, node_state in s.items():
                print(f"[{node_name}] Processing...")
                final_state = node_state

        return final_state


class ChatModifier:
    """
    Chat interface for modifying existing projects
    Uses central orchestrator for intelligent modifications
    """

    def __init__(self, tools: Any):
        self.orchestrator = CentralOrchestrator(tools)
        self.tools = tools
        self.llm = self._load_llm()

    def _load_llm(self):
        provider = Config.MODEL_PROVIDER
        model_name = Config.MODEL_NAME

        if provider == "google":
            api_key = Config.GOOGLE_API_KEY
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.3, max_tokens=4000)
        elif provider == "openai":
            api_key = Config.OPENAI_API_KEY
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.3, max_tokens=4000)
        elif provider == "anthropic":
            api_key = Config.ANTHROPIC_API_KEY
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model_name, api_key=api_key, temperature=0.3, max_tokens=4000)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def modify_project(
            self,
            project_name: str,
            modification_request: str
    ) -> Dict[str, Any]:
        """Modify existing project based on user request with comprehensive state management"""

        try:
            # Load project state and conversation history
            project_state = self.orchestrator.project_state_manager.load_project_state(project_name)
            conversation_history = self.orchestrator.get_conversation_history(project_name)

            if not project_state:
                return {
                    "success": False,
                    "error": f"No project state found for '{project_name}'"
                }

            # Read project files for additional context
            files_result = self.tools.list_files(project_name)
            files = files_result.get("files", []) if files_result.get("success") else []

            # Read key files for context
            context = ""
            for file in files[:10]:  # Limit context
                if any(file.endswith(ext) for ext in ['.py', '.md', '.yml', '.yaml']):
                    content = self.tools.read_file(file)
                    if content.get("success"):
                        context += f"\n\n=== {file} ===\n{content['content'][:500]}"

            # Create comprehensive modification context
            modification_context = {
                "project_name": project_name,
                "project_type": project_state.project_type,
                "original_requirements": project_state.requirements,
                "modification_request": modification_request,
                "existing_files": project_state.generated_files,
                "architecture": project_state.architecture,
                "test_results": project_state.test_results,
                "conversation_history": conversation_history,
                "current_stage": project_state.current_stage,
                "stage_status": project_state.stage_status,
                "file_context": context,
                "project_files": files
            }

            # Classify modification intent
            intent = self.orchestrator.classify_user_intent(modification_request)

            # Add modification request to conversation
            self.orchestrator.add_user_message(project_name, modification_request, intent)

            # Use orchestrator to analyze modification with full context
            analysis_result = await self.orchestrator.reason_and_act(
                state={
                    "project_name": f"{project_name}_modification",
                    "requirements": f"MODIFY EXISTING PROJECT: {project_name}\n\nOriginal Requirements: {project_state.requirements}\n\nModification Request: {modification_request}",
                    "status": TaskStatus.PENDING,
                    "current_step": "requirements",
                    "task_id": f"modify_{project_name}_{int(time.time())}",
                    "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
                    "requires_human_input": False,
                    "modification_context": modification_context,
                    "modification_intent": intent
                }
            )

            return {
                "success": True,
                "analysis": analysis_result,
                "modification_context": modification_context,
                "intent": intent,
                "next_action": "User should review and confirm changes"
            }

        except Exception as e:
            logger.error(f"Error modifying project {project_name}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to modify project: {str(e)}"
            }