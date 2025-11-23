from typing import Dict, Any, Optional, Any as AnyType, List
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import os
from pydantic import BaseModel, Field
from orchestrator.orchestrator_file_manager import OrchestratorFileManager
from core.enhanced_file_tools import EnhancedFileTools
from core.config import Config
from utils.conversation_manager import ConversationManager
from utils.project_state import ProjectStateManager, ProjectState, StageStatus
from utils.timeline_tracker import TimelineManager
from utils.context_manager import ContextManager
from langchain_core.messages import HumanMessage, SystemMessage

class ActionDetails(BaseModel):
    agent: Optional[str] = Field(description="requirements_analyst|system_architect|developer|qa_engineer|devops_engineer")
    tool: Optional[str] = Field(description="web_search|read_file|analyze_code")
    query: Optional[str] = Field(description="Search query or tool parameters")
    reason: Optional[str] = Field(description="Why this action is needed")

    class Config:
        extra = "allow"

class OrchestratorDecision(BaseModel):
    thought: str = Field(description="Your reasoning about current situation")
    action: str = Field(description="delegate_to_agent|use_tool|request_human_input|proceed|complete|chat_response")
    action_details: ActionDetails = Field(description="Details for the chosen action")
    observation_needed: Optional[str] = Field(description="What information do you need to see")
    next_step: Optional[str] = Field(description="What should happen after this action")
    chat_response: Optional[str] = Field(description="Response to the user if action is chat_response")

    class Config:
        extra = "allow"

class CentralOrchestrator:
    """
    Central LLM with ReAct reasoning
    Makes intelligent decisions about workflow
    """

    def get_current_project(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the current project."""
        project_id = state.get("project_name")
        if not project_id:
            return None
        return self._get_project_status(project_id)

    def get_current_step(self, state: Dict[str, Any]) -> Optional[str]:
        """Get the current step."""
        return state.get("current_step")

    def __init__(self, tools: AnyType):
        self.tools = tools
        self.file_tools = EnhancedFileTools()
        self.context_manager = ContextManager()
        self.file_manager = OrchestratorFileManager(
            self.file_tools,
            self.context_manager
        )
        self.tz = ZoneInfo("Asia/Kolkata")
        self.state_file = Path("./workspace/.orchestrator_state.json")
        self.agent_status_file = Path("./workspace/.agent_status.json")
        
        self.conversation_manager = ConversationManager()
        self.project_state_manager = ProjectStateManager()
        self.timeline_manager = TimelineManager()
        
        self.persistent_state = self._load_persistent_state()
        self.agent_status = self._load_agent_status()
        self.registered_agents = {}

        try:
            self.llm = self._load_llm(temperature=0.2, max_tokens=4000)
        except Exception as e:
            print(f"LLM not configured or failed to load: {e}")
            self.llm = None

        self.system_prompt = """You are the Central Orchestrator for AI-SOL, an AI software development platform.

Your role is to coordinate multiple specialized agents and ensure complete project generation.

Available Agents:
1. Requirements Analyst - Analyzes user requirements and creates specifications
2. System Architect - Designs system architecture and technical specifications
3. Developer - Generates complete, working code files
4. QA Engineer - Tests and validates quality
5. DevOps Engineer - Creates deployment configurations

Workflow Process:
Requirements → Architecture → Developer → QA → DevOps → Complete

You can also chat with the user to answer questions or take feedback.
"""

    def register_agents(self, agents: Dict[str, Any]):
        """Register agent instances for direct access."""
        self.registered_agents.update(agents)

    async def process_user_message(self, message: str, project_state: Dict[str, Any]) -> str:
        """Process a message from the user and return a response."""
        if not self.llm:
            return "Orchestrator LLM is not available."

        # Construct context
        current_step = project_state.get("current_step", "unknown")
        status = project_state.get("status", "unknown")
        
        prompt = f"""
Current Project Status:
- Step: {current_step}
- Status: {status}

User Message: "{message}"

You are the Orchestrator. The user is asking a question or giving feedback.
If the user wants to proceed, confirm that you will resume the workflow.
If the user asks about the project, answer based on the current state.
If the user wants to change something, explain how you will delegate that to the appropriate agent (conceptually).

Respond directly to the user.
"""
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])
            return response.content
        except Exception as e:
            return f"Error processing message: {e}"

    async def execute_build_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the developer build plan."""
        # This is a simplified version for the refactor
        if 'developer' in self.registered_agents:
            dev_agent = self.registered_agents['developer']
            # Inject log callback if available on orchestrator (not implemented here but good practice)
            return await dev_agent.execute(state)
        return {"success": False, "error": "Developer agent not registered"}

    # ... (Keep existing helper methods like _load_llm, _load_persistent_state, etc.)
    
from typing import Dict, Any, Optional, Any as AnyType, List
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import os
from pydantic import BaseModel, Field
from orchestrator.orchestrator_file_manager import OrchestratorFileManager
from core.enhanced_file_tools import EnhancedFileTools
from core.config import Config
from utils.conversation_manager import ConversationManager
from utils.project_state import ProjectStateManager, ProjectState, StageStatus
from utils.timeline_tracker import TimelineManager
from utils.context_manager import ContextManager
from langchain_core.messages import HumanMessage, SystemMessage

class ActionDetails(BaseModel):
    agent: Optional[str] = Field(description="requirements_analyst|system_architect|developer|qa_engineer|devops_engineer")
    tool: Optional[str] = Field(description="web_search|read_file|analyze_code")
    query: Optional[str] = Field(description="Search query or tool parameters")
    reason: Optional[str] = Field(description="Why this action is needed")

    class Config:
        extra = "allow"

class OrchestratorDecision(BaseModel):
    thought: str = Field(description="Your reasoning about current situation")
    action: str = Field(description="delegate_to_agent|use_tool|request_human_input|proceed|complete|chat_response")
    action_details: ActionDetails = Field(description="Details for the chosen action")
    observation_needed: Optional[str] = Field(description="What information do you need to see")
    next_step: Optional[str] = Field(description="What should happen after this action")
    chat_response: Optional[str] = Field(description="Response to the user if action is chat_response")

    class Config:
        extra = "allow"

class CentralOrchestrator:
    """
    Central LLM with ReAct reasoning
    Makes intelligent decisions about workflow
    """

    def get_current_project(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the current project."""
        project_id = state.get("project_name")
        if not project_id:
            return None
        return self._get_project_status(project_id)

    def get_current_step(self, state: Dict[str, Any]) -> Optional[str]:
        """Get the current step."""
        return state.get("current_step")

    def __init__(self, tools: AnyType):
        self.tools = tools
        self.file_tools = EnhancedFileTools()
        self.context_manager = ContextManager()
        self.file_manager = OrchestratorFileManager(
            self.file_tools,
            self.context_manager
        )
        self.tz = ZoneInfo("Asia/Kolkata")
        self.state_file = Path("./workspace/.orchestrator_state.json")
        self.agent_status_file = Path("./workspace/.agent_status.json")
        
        self.conversation_manager = ConversationManager()
        self.project_state_manager = ProjectStateManager()
        self.timeline_manager = TimelineManager()
        
        self.persistent_state = self._load_persistent_state()
        self.agent_status = self._load_agent_status()
        self.registered_agents = {}

        try:
            self.llm = self._load_llm(temperature=0.2, max_tokens=4000)
        except Exception as e:
            print(f"LLM not configured or failed to load: {e}")
            self.llm = None

        self.system_prompt = """You are the Central Orchestrator for AI-SOL, an AI software development platform.

Your role is to coordinate multiple specialized agents and ensure complete project generation.

Available Agents:
1. Requirements Analyst - Analyzes user requirements and creates specifications
2. System Architect - Designs system architecture and technical specifications
3. Developer - Generates complete, working code files
4. QA Engineer - Tests and validates quality
5. DevOps Engineer - Creates deployment configurations

Workflow Process:
Requirements → Architecture → Developer → QA → DevOps → Complete

You can also chat with the user to answer questions or take feedback.
"""

    def register_agents(self, agents: Dict[str, Any]):
        """Register agent instances for direct access."""
        self.registered_agents.update(agents)

    async def process_user_message(self, message: str, project_state: Dict[str, Any]) -> str:
        """Process a message from the user and return a response."""
        if not self.llm:
            return "Orchestrator LLM is not available."

        # Construct context
        current_step = project_state.get("current_step", "unknown")
        status = project_state.get("status", "unknown")
        
        prompt = f"""
Current Project Status:
- Step: {current_step}
- Status: {status}

User Message: "{message}"

You are the Orchestrator. The user is asking a question or giving feedback.
If the user wants to proceed, confirm that you will resume the workflow.
If the user asks about the project, answer based on the current state.
If the user wants to change something, explain how you will delegate that to the appropriate agent (conceptually).

Respond directly to the user.
"""
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ])
            return response.content
        except Exception as e:
            return f"Error processing message: {e}"

    async def execute_build_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the developer build plan."""
        # This is a simplified version for the refactor
        if 'developer' in self.registered_agents:
            dev_agent = self.registered_agents['developer']
            # Inject log callback if available on orchestrator (not implemented here but good practice)
            return await dev_agent.execute(state)
        return {"success": False, "error": "Developer agent not registered"}

    # ... (Keep existing helper methods like _load_llm, _load_persistent_state, etc.)
    
    def _load_llm(self, temperature: float, max_tokens: int):
        """Load LLM based on Config."""
        # Duplicate logic from BaseAgent or import it. For now, simple re-implementation
        provider = Config.MODEL_PROVIDER
        api_key = Config.GOOGLE_API_KEY
        
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            import os
            os.environ["GOOGLE_API_KEY"] = api_key
            
            model_name = Config.MODEL_NAME
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"
                
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )
        # Add other providers as needed
        return None

    def _load_persistent_state(self): return {}
    def _load_agent_status(self): return {}
    def _get_project_status(self, pid): return {}