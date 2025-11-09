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

class ActionDetails(BaseModel):
    agent: Optional[str] = Field(description="requirements_analyst|system_architect|developer|qa_engineer|devops_engineer")
    tool: Optional[str] = Field(description="web_search|read_file|analyze_code")
    query: Optional[str] = Field(description="Search query or tool parameters")
    reason: Optional[str] = Field(description="Why this action is needed")

    class Config:
        # Accept unknown extra fields returned by the LLM to avoid strict validation errors
        extra = "allow"


class OrchestratorDecision(BaseModel):
    thought: str = Field(description="Your reasoning about current situation")
    action: str = Field(description="delegate_to_agent|use_tool|request_human_input|proceed|complete")
    action_details: ActionDetails = Field(description="Details for the chosen action")
    observation_needed: Optional[str] = Field(description="What information do you need to see")
    next_step: Optional[str] = Field(description="What should happen after this action")

    class Config:
        # Accept unknown extra fields returned by the LLM
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
        # ContextManager may not be set on tools; create local one
        self.context_manager = ContextManager()
        self.file_manager = OrchestratorFileManager(
            self.file_tools,
            self.context_manager
        )
        self.tz = ZoneInfo("Asia/Kolkata")
        self.state_file = Path("./workspace/.orchestrator_state.json")
        self.agent_status_file = Path("./workspace/.agent_status.json")
        
        # Initialize new managers
        self.conversation_manager = ConversationManager()
        self.project_state_manager = ProjectStateManager()
        self.timeline_manager = TimelineManager()
        
        # Load persistent state
        self.persistent_state = self._load_persistent_state()
        self.agent_status = self._load_agent_status()

        try:
            self.llm = self._load_llm(temperature=0.2, max_tokens=4000)
        except Exception as e:
            self.log(f"LLM not configured or failed to load: {e}", "warning")
            self.llm = None

        # The orchestrator should prefer automated LLM-driven decisions but allow
        # human interrupts/checkpoints when configured. It will request human
        # input only when a checkpoint is active or when the LLM decision asks
        # for human clarification.
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

Guidelines:
- Prefer LLM-driven decisions for orchestration (use ReAct to think/decide/act).
- Use human checkpoints when enabled by configuration (interrupts_enabled=True).
- When a human is asked, present a concise, human-friendly summary and allow actions: continue, modify, retry, abort.
- Record decisions in conversation history and prefer actions that maximize project completeness and correctness.
- Use automated retries (bounded) before escalating to human input.

Success Criteria:
- Requirements: functional and non-functional requirements present
- Architecture: clear system design and file-level blueprint
- Developer: working code files are produced
- QA: code passes basic syntax and unit checks
- DevOps: deployment configuration present

Decision Making:
- Use the LLM to reason about trade-offs and choose actions. When multiple plausible actions exist, prefer the one that preserves correctness and developer time.
- When uncertain, request human input via a checkpoint (if enabled).

Always respond with valid JSON when asked to produce structured output by the system.
"""

        # Whether to pause after each agent/file generation and ask the human to review
        # Can be toggled via Config or by tests.
        self.interrupts_enabled = getattr(Config, 'ENABLE_INTERRUPTS', True)

        # Agent registry: optional mapping of agent name -> agent instance. Can be set via register_agents().
        self.agents: Dict[str, Any] = {}

    def register_agents(self, agents: Dict[str, Any]):
        """Register agent instances so the orchestrator can call them by role name.

        Example: orchestrator.register_agents({'developer': dev_agent, 'qa': qa_agent})
        """
        self.agents.update(agents or {})
        # Also, if tools is a dict, merge for backward-compatibility
        if isinstance(self.tools, dict):
            self.tools.update(agents)
        else:
            # attach as attributes for convenience
            for k, v in agents.items():
                setattr(self.tools, k, v)

    def get_agent(self, name: str):
        """Resolve an agent instance by name from multiple possible registries."""
        # 1. explicit registry
        if name in self.agents:
            return self.agents[name]
        # 2. tools object (dict-like)
        if isinstance(self.tools, dict) and name in self.tools:
            return self.tools[name]
        # 3. attribute on tools
        if hasattr(self.tools, name):
            return getattr(self.tools, name)
        # Not found
        return None

    def _load_llm(self, temperature: float, max_tokens: int):
        """Dynamically loads the LLM based on configuration."""
        provider = Config.MODEL_PROVIDER
        model_name = Config.MODEL_NAME

        if provider == "google":
            api_key = Config.GOOGLE_API_KEY
        elif provider == "openai":
            api_key = Config.OPENAI_API_KEY
        elif provider == "anthropic":
            api_key = Config.ANTHROPIC_API_KEY
        elif provider == "xai":
            api_key = Config.XAI_API_KEY
        elif provider == "mistral":
            api_key = Config.MISTRAL_API_KEY
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        if not api_key:
            raise ValueError(f"API key for {provider} is not set in environment variables.")

        if provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=model_name,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except ImportError:
                raise ImportError("Please install langchain-anthropic to use Anthropic models.")
        elif provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except ImportError:
                raise ImportError("Please install langchain-openai to use OpenAI models.")
        elif provider == "xai":
            try:
                from langchain_xai import ChatXAI
                return ChatXAI(
                    model=model_name,
                    xai_api_key=api_key, # Grok uses xai_api_key
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except ImportError:
                raise ImportError("Please install langchain-xai to use xAI (Grok) models.")
        elif provider == "google":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from google.generativeai import types  # noqa: F401
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except ImportError:
                raise ImportError("Please install langchain-google-genai to use Google Gemini models.")
        elif provider == "mistral":
            try:
                from langchain_mistralai import ChatMistralAI
                return ChatMistralAI(
                    model=model_name,
                    mistral_api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except ImportError:
                raise ImportError("Please install langchain-mistralai to use Mistral AI models.")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def log(self, message: str, level: str = "info"):
        """Simple logging"""
        timestamp = datetime.now(self.tz).strftime("%H:%M:%S")
        colors = {
            "info": "\033[36m",  # Cyan
            "success": "\033[32m",  # Green
            "warning": "\033[33m",  # Yellow
            "error": "\033[31m",  # Red
            "debug": "\033[35m",  # Magenta for debug
            "reset": "\033[0m"
        }

        color = colors.get(level, colors["info"])
        print(f"{color}[{timestamp}] [ORCHESTRATOR] {message}{colors['reset']}")

    def _truncate_prompt(self, prompt: str, max_tokens: int) -> str:
        """Truncates a prompt to a maximum number of tokens."""
        # A more sophisticated implementation could use summarization
        tokens = self.tools.count_tokens(prompt)
        if tokens <= max_tokens:
            return prompt

        # Simple truncation
        ratio = max_tokens / tokens
        new_length = int(len(prompt) * ratio)
        truncated_prompt = prompt[:new_length]

        # Ensure we don't cut in the middle of a word
        last_space = truncated_prompt.rfind(' ')
        if last_space != -1:
            truncated_prompt = truncated_prompt[:last_space]

        self.log(f"Prompt truncated from {tokens} to {self.tools.count_tokens(truncated_prompt)} tokens.", "warning")
        return truncated_prompt

    async def reason_and_act(
            self,
            state: Dict[str, Any],
            context: str
    ) -> Dict[str, Any]:
        """
        Execute ReAct reasoning loop with conversation memory integration
        Returns decision about what to do next as a plain dict (normalized)
        """
        try:
            project_id = state.get("project_name", "default_project")
            session_id = state.get("task_id", project_id)
            
            # Load conversation history for context
            conversation_history = self.conversation_manager.get_message_history(session_id, limit=5)
            
            # Check if we have a human response to process
            human_response = state.get("human_response")
            if human_response:
                self.log(f"Processing human response: {human_response}", "info")
                
                # Record human response in conversation
                self.conversation_manager.add_message(
                    session_id,
                    "user", 
                    f"Human response: {human_response}",
                    {"project_state": state.get("current_step", "unknown")}
                )
                
                # Handle different human responses
                if human_response == "skip":
                    decision = {
                        "thought": "Human requested to skip current step",
                        "action": "proceed",
                        "action_details": {"reason": "Human requested skip"},
                        "observation_needed": "Continue to next step",
                        "next_step": "Proceed to next phase"
                    }
                elif human_response == "retry":
                    decision = {
                        "thought": "Human requested to retry current step",
                        "action": "delegate_to_agent",
                        "action_details": {"agent": state.get("current_step", "developer")},
                        "observation_needed": "Retry the current step",
                        "next_step": "Retry current step"
                    }
                elif human_response == "abort":
                    decision = {
                        "thought": "Human requested to abort project",
                        "action": "complete",
                        "action_details": {"reason": "Human requested abort"},
                        "observation_needed": "Project aborted",
                        "next_step": "End project"
                    }
                else:  # "proceed" or "proceed_automatically"
                    decision = {
                        "thought": "Human requested to proceed or auto-proceeding",
                        "action": "proceed",
                        "action_details": {"reason": "Human requested proceed"},
                        "observation_needed": "Continue workflow",
                        "next_step": "Continue to next step"
                    }
            else:
                # Build current situation summary with conversation context
                situation = self._summarize_situation(state)
                
                # Include conversation history in context
                conversation_context = ""
                if conversation_history:
                    conversation_context = "\n**Recent Conversation:**\n"
                    for entry in conversation_history[-3:]:  # Last 3 messages
                        conversation_context += f"- {entry.sender}: {entry.message[:100]}...\n"

                prompt = f"""Analyze the current situation and decide the next action.

**Current Situation:**
{situation}

**Context:**
{context}

{conversation_context}

**Recent Actions:**
{json.dumps(state.get('orchestrator_thoughts', [])[-3:], indent=2)}

Use ReAct framework: Think about what's needed, decide action, specify what observation you need.

Respond with JSON."""

                # Truncate prompt if it exceeds the token limit
                truncated_prompt = self._truncate_prompt(prompt, 60000)

                # Create a prompt template using lazy import to avoid importing langchain at module load
                try:
                    from langchain_core.prompts import ChatPromptTemplate
                except Exception:
                    # Minimal fallback template
                    class _FallbackTemplate:
                        @staticmethod
                        def from_messages(messages):
                            class Templ:
                                def format(self, **kwargs):
                                    return kwargs.get('input', '')

                                def __str__(self):
                                    return self.system_prompt if hasattr(self, 'system_prompt') else ''

                            return Templ()

                    ChatPromptTemplate = _FallbackTemplate

                template = ChatPromptTemplate.from_messages([
                    ("system", self.system_prompt),
                    ("human", "{input}")
                ])

                try:
                    if not self.llm:
                        raise RuntimeError("LLM not configured; skipping LLM invocation in orchestrator")

                    llm_with_structure = self.llm.with_structured_output(OrchestratorDecision)
                    decision_model = await llm_with_structure.ainvoke(template.format(input=truncated_prompt))
                    # Normalize to plain dict to avoid passing model objects to other parts of the system
                    if hasattr(decision_model, "dict"):
                        decision = decision_model.dict()
                    else:
                        try:
                            decision = dict(decision_model)
                        except Exception:
                            decision = {"thought": str(decision_model), "action": "proceed", "action_details": {}}

                    self.log(f"DEBUG: Raw LLM response in orchestrator (normalized): {decision}", "debug")
                except Exception as e:
                    self.log(f"ERROR: LLM ainvoke failed or JSON parsing failed: {e}", "error")
                    decision = {
                        "thought": f"LLM invocation or JSON parsing failed or unavailable: {e}",
                        "action": "proceed",
                        "action_details": {}
                    }

            # Record orchestrator decision in conversation
            thought_text = decision.get("thought") if isinstance(decision, dict) else str(decision)
            action_text = decision.get("action") if isinstance(decision, dict) else "proceed"
            
            self.conversation_manager.add_message(
                session_id,
                "ai",
                f"Orchestrator decision: {thought_text}",
                {
                    "action": action_text,
                    "project_state": state.get("current_step", "unknown"),
                    "steps_completed": state.get("steps_completed", [])
                }
            )

            # Record thought (use safe, canonical format)
            try:
                tz = ZoneInfo("Asia/Kolkata")
                # Append normalized entry
                state["orchestrator_thoughts"].append({
                    "thought": thought_text,
                    "action": action_text,
                    "timestamp": datetime.now(tz).isoformat()
                })
            except Exception as e:
                # If recording fails, log and continue - do not let it bubble up
                self.log(f"WARNING: failed to record orchestrator thought: {e}", "warning")

            # Always return a plain dict
            return decision
        except json.JSONDecodeError as e:
            self.log(f"JSON parse error in orchestrator: {e}", "error")
            return {
                "thought": f"JSON parsing failed: {e}",
                "action": "proceed",
                "action_details": {}
            }
        except Exception as e:
            self.log(f"An unexpected error occurred in orchestrator.reason_and_act: {e}", "error")
            return {
                "thought": f"Unexpected error: {e}",
                "action": "proceed",
                "action_details": {}
            }

    def _summarize_situation(self, state: Dict[str, Any]) -> str:
        """Create summary of current state"""

        # Ensure agent outputs are always dictionaries for safe access
        req_output = state.get('requirements_output') or {}
        arch_output = state.get('architecture_output') or {}
        dev_output = state.get('developer_output') or {}
        qa_output = state.get('qa_output') or {}
        devops_output = state.get('devops_output') or {}

        # Ensure steps_completed is safe iterable
        steps_completed = state.get('steps_completed') or []

        summary = f"""
**Project:** {state.get('project_name', 'unknown')}
**Current Step:** {state.get('current_step', 'unknown')}
**Steps Completed:** {', '.join(steps_completed)}
**Status:** {state.get('status', 'unknown')}

**Agent Outputs:**
- Requirements: {'✓' if isinstance(req_output, dict) and req_output.get('success', False) else '✗'}
- Architecture: {'✓' if isinstance(arch_output, dict) and arch_output.get('success', False) else '✗'}
- Developer: {'✓' if isinstance(dev_output, dict) and dev_output.get('success', False) else '✗'}
- QA: {'✓' if isinstance(qa_output, dict) and qa_output.get('success', False) else '✗'}
- DevOps: {'✓' if isinstance(devops_output, dict) and devops_output.get('success', False) else '✗'}

**Quality Metrics:**
- Code Quality: {state.get('code_quality_score', 0):.1f}/100
- Test Coverage: {state.get('test_coverage', 0):.1f}%
- Security Issues: {len(state.get('security_issues', []))}

**Files Generated:** {len(state.get('generated_files', []))}
**Errors:** {len(state.get('errors', []))}
"""
        return summary

    async def should_request_human_input(
            self,
            state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decide if human input is needed"""

        # Only check for critical errors that would prevent completion
        if len(state.get('errors', [])) > 5:  # Increased threshold
            return {
                "needed": True,
                "reason": f"{len(state['errors'])} critical errors encountered",
                "prompt": f"Multiple critical errors occurred:\n" +
                          "\n".join(f"- {e.get('agent', '')}: {e.get('error', '')}" for e in state['errors'][-3:]) +
                          "\n\nHow should I proceed?"
            }

        return {"needed": False}

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool"""
        if not hasattr(self.tools, tool_name):
            return {"success": False, "error": f"Tool {tool_name} not found"}

        tool_method = getattr(self.tools, tool_name)
        return tool_method(**kwargs)
    
    def _load_persistent_state(self) -> Dict[str, Any]:
        """Load persistent state from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"Failed to load persistent state: {e}", "warning")
        return {"projects": {}, "completed_projects": [], "last_updated": None}
    
    def _save_persistent_state(self):
        """Save persistent state to disk"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.persistent_state["last_updated"] = datetime.now(self.tz).isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.persistent_state, f, indent=2)
        except Exception as e:
            self.log(f"Failed to save persistent state: {e}", "error")
    
    def _load_agent_status(self) -> Dict[str, Any]:
        """Load agent status from disk"""
        try:
            if self.agent_status_file.exists():
                with open(self.agent_status_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"Failed to load agent status: {e}", "warning")
        return {"active_agents": {}, "completed_agents": {}}
    
    def _save_agent_status(self):
        """Save agent status to disk"""
        try:
            self.agent_status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.agent_status_file, 'w') as f:
                json.dump(self.agent_status, f, indent=2)
        except Exception as e:
            self.log(f"Failed to save agent status: {e}", "error")
    
    def _is_agent_running(self, project_id: str, agent_name: str) -> bool:
        """Check if an agent is currently running for a project"""
        key = f"{project_id}_{agent_name}"
        if key in self.agent_status["active_agents"]:
            # Check if it's been running too long (5 minutes timeout)
            start_time = datetime.fromisoformat(self.agent_status["active_agents"][key]["started_at"])
            if (datetime.now(self.tz) - start_time).seconds > 300:  # 5 minutes
                # Mark as completed due to timeout
                self.agent_status["completed_agents"][key] = {
                    "status": "timeout",
                    "completed_at": datetime.now(self.tz).isoformat()
                }
                del self.agent_status["active_agents"][key]
                self._save_agent_status()
                return False
            return True
        return False
    
    def _mark_agent_started(self, project_id: str, agent_name: str):
        """Mark an agent as started"""
        key = f"{project_id}_{agent_name}"
        self.agent_status["active_agents"][key] = {
            "agent_name": agent_name,
            "project_id": project_id,
            "started_at": datetime.now(self.tz).isoformat()
        }
        self._save_agent_status()
    
    def _mark_agent_completed(self, project_id: str, agent_name: str, success: bool = True):
        """Mark an agent as completed"""
        key = f"{project_id}_{agent_name}"
        if key in self.agent_status["active_agents"]:
            del self.agent_status["active_agents"][key]
        
        self.agent_status["completed_agents"][key] = {
            "agent_name": agent_name,
            "project_id": project_id,
            "status": "completed" if success else "failed",
            "completed_at": datetime.now(self.tz).isoformat()
        }
        self._save_agent_status()
    
    def _mark_project_complete(self, project_id: str, project_data: Dict[str, Any]):
        """Mark a project as completed in persistent state"""
        self.persistent_state["completed_projects"].append({
            "project_id": project_id,
            "project_data": project_data,
            "completed_at": datetime.now(self.tz).isoformat()
        })
        self._save_persistent_state()
    
    def _get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project status from persistent state"""
        for project in self.persistent_state["completed_projects"]:
            if project["project_id"] == project_id:
                return project
        return None
    
    def _collect_errors(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """Collect all errors from the workflow state"""
        errors = []
        
        # Check each agent's output for errors
        agent_outputs = [
            ("requirements", state.get("requirements_output", {})),
            ("architecture", state.get("architecture_output", {})),
            ("developer", state.get("developer_output", {})),
            ("qa", state.get("qa_output", {})),
            ("devops", state.get("devops_output", {}))
        ]
        
        for agent_name, output in agent_outputs:
            if isinstance(output, dict):
                if not output.get("success", True):
                    error_msg = output.get("error", "Unknown error")
                    errors.append({
                        "agent": agent_name,
                        "error": error_msg,
                        "type": "agent_failure"
                    })
                
                # Check for specific error fields
                if "errors" in output:
                    for error in output["errors"]:
                        if isinstance(error, dict):
                            errors.append({
                                "agent": agent_name,
                                "error": error.get("error", str(error)),
                                "type": "agent_error"
                            })
                        else:
                            errors.append({
                                "agent": agent_name,
                                "error": str(error),
                                "type": "agent_error"
                            })
        
        # Check for general errors in state
        if "errors" in state:
            for error in state["errors"]:
                if isinstance(error, dict):
                    errors.append({
                        "agent": error.get("agent", "unknown"),
                        "error": error.get("error", str(error)),
                        "type": "workflow_error"
                    })
                else:
                    errors.append({
                        "agent": "unknown",
                        "error": str(error),
                        "type": "workflow_error"
                    })
        
        return errors
    
    def _format_error_message(self, errors: List[Dict[str, str]]) -> str:
        """Format error messages for user display"""
        if not errors:
            return "No specific errors reported."
        
        error_messages = []
        for error in errors:
            agent = error.get("agent", "Unknown")
            error_text = error.get("error", "Unknown error")
            error_type = error.get("type", "error")
            
            if error_type == "agent_failure":
                error_messages.append(f"❌ {agent.title()} Agent Failed: {error_text}")
            elif error_type == "agent_error":
                error_messages.append(f"⚠️ {agent.title()} Agent Error: {error_text}")
            else:
                error_messages.append(f"🔧 {agent.title()} Issue: {error_text}")
        
        return "\n".join(error_messages)
    
    def _generate_user_friendly_response(self, state: Dict[str, Any], errors: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a user-friendly response with detailed error information"""
        success = len(errors) == 0 and all(
            state.get(f"{agent}_output", {}).get("success", True) 
            for agent in ["requirements", "architecture", "developer", "qa", "devops"]
        )
        
        response = {
            "success": success,
            "message": "Project completed successfully!" if success else "Project completed with some issues.",
            "project_name": state.get("project_name", "Unknown"),
            "steps_completed": state.get("steps_completed", []),
            "generated_files": state.get("generated_files", []),
            "quality_metrics": {
                "code_quality_score": state.get("code_quality_score", 0),
                "test_coverage": state.get("test_coverage", 0),
                "security_issues": len(state.get("security_issues", []))
            }
        }
        
        if errors:
            response["errors"] = errors
            response["error_summary"] = self._format_error_message(errors)
            response["suggestions"] = self._generate_error_suggestions(errors)
        
        return response
    
    def _generate_error_suggestions(self, errors: List[Dict[str, str]]) -> List[str]:
        """Generate helpful suggestions based on errors"""
        suggestions = []
        
        for error in errors:
            agent = error.get("agent", "")
            error_text = error.get("error", "").lower()
            
            if "requirements" in agent:
                suggestions.append("Try providing more detailed requirements or enabling research mode")
            elif "architecture" in agent:
                suggestions.append("Check if requirements are complete and clear")
            elif "developer" in agent:
                suggestions.append("Ensure architecture is properly defined before code generation")
            elif "qa" in agent:
                suggestions.append("Verify that code files were generated successfully")
            elif "devops" in agent:
                suggestions.append("Check that QA process completed successfully")
            
            if "llm" in error_text or "api" in error_text:
                suggestions.append("Check your API key configuration and internet connection")
            elif "file" in error_text:
                suggestions.append("Check file permissions and workspace directory")
            elif "git" in error_text:
                suggestions.append("Git operations are optional - project can continue without them")
        
        # Remove duplicates and return unique suggestions
        return list(set(suggestions))
    
    # New methods for ProjectState and TimelineManager integration
    
    def initialize_project_state(self, project_id: str, project_name: str, requirements: str) -> ProjectState:
        """Initialize project state for a new project"""
        try:
            project_state = self.project_state_manager.create_initial_state(
                project_id=project_id,
                project_name=project_name,
                requirements=requirements
            )
            
            # Create timeline for the project
            self.timeline_manager.create_timeline(project_id)
            
            # Create conversation for the project
            self.conversation_manager.create_conversation(
                session_id=project_id,
                project_id=project_id,
                initial_message=f"Project '{project_name}' started with requirements: {requirements[:100]}..."
            )
            
            self.log(f"Initialized project state for {project_id}", "info")
            return project_state
            
        except Exception as e:
            self.log(f"Failed to initialize project state: {e}", "error")
            return None
    
    def update_project_stage(self, project_id: str, stage: str, status: StageStatus, 
                           agent_output: Dict[str, Any] = None, errors: List[str] = None):
        """Update project stage status"""
        try:
            self.project_state_manager.update_stage_status(
                project_id=project_id,
                stage_name=stage,
                status=status,
                agent_output=agent_output,
                errors=errors
            )
            
            # Update timeline
            progress_percentage = self._get_stage_progress_percentage(stage, status)
            self.timeline_manager.update_stage_progress(
                project_id=project_id,
                stage_name=stage,
                progress_percentage=progress_percentage,
                milestone=f"{stage} {status.value}"
            )
            
            self.log(f"Updated project {project_id} stage {stage} to {status.value}", "info")
            # If interrupts enabled, create a human-review checkpoint after stage completion
            try:
                if getattr(self, 'interrupts_enabled', False) and status.name.lower() == 'completed':
                    try:
                        self.checkpoint_agent_output(project_id, stage, agent_output or {})
                        self.log(f"Created checkpoint for stage {stage} of project {project_id}", "info")
                    except Exception as e:
                        self.log(f"Failed to create checkpoint for stage {stage}: {e}", "warning")
            except Exception:
                pass
            
        except Exception as e:
            self.log(f"Failed to update project stage: {e}", "error")
    
    def _get_stage_progress_percentage(self, stage: str, status: StageStatus) -> float:
        """Get progress percentage for a stage based on status"""
        stage_progress_map = {
            "requirements": {"pending": 0, "in_progress": 20, "completed": 20, "failed": 10},
            "architecture": {"pending": 20, "in_progress": 40, "completed": 40, "failed": 30},
            "developer": {"pending": 40, "in_progress": 70, "completed": 70, "failed": 60},
            "qa": {"pending": 70, "in_progress": 90, "completed": 90, "failed": 80},
            "devops": {"pending": 90, "in_progress": 95, "completed": 100, "failed": 90}
        }
        
        return stage_progress_map.get(stage, {}).get(status.value, 0)
    
    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive project status"""
        try:
            project_state = self.project_state_manager.load_project_state(project_id)
            timeline = self.timeline_manager.load_timeline(project_id)
            conversation = self.conversation_manager.load_conversation(project_id)
            
            if not project_state:
                return {"error": "Project not found"}
            
            return {
                "project_id": project_id,
                "project_name": project_state.project_name,
                "current_stage": project_state.current_stage,
                "stage_status": project_state.stage_status,
                "overall_progress": timeline.overall_progress if timeline else 0,
                "estimated_completion": timeline.estimated_completion if timeline else None,
                "steps_completed": project_state.get_completed_stages(),
                "errors": project_state.errors,
                "last_updated": project_state.updated_at,
                "conversation_active": conversation is not None
            }
            
        except Exception as e:
            self.log(f"Failed to get project status: {e}", "error")
            return {"error": str(e)}
    
    def get_conversation_history(self, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a project"""
        try:
            messages = self.conversation_manager.get_message_history(project_id, limit=limit)
            return [
                {
                    "sender": msg.sender,
                    "message": msg.message,
                    "timestamp": msg.timestamp,
                    "intent": msg.intent
                }
                for msg in messages
            ]
        except Exception as e:
            self.log(f"Failed to get conversation history: {e}", "error")
            return []
    
    def add_user_message(self, project_id: str, message: str, intent: str = None):
        """Add a user message to the conversation"""
        try:
            self.conversation_manager.add_message(
                session_id=project_id,
                sender="user",
                message=message,
                intent=intent
            )
            self.log(f"Added user message to project {project_id}", "info")
        except Exception as e:
            self.log(f"Failed to add user message: {e}", "error")
    
    def classify_user_intent(self, message: str) -> str:
        """Classify user intent from message"""
        try:
            return self.conversation_manager.classify_intent(message)
        except Exception as e:
            self.log(f"Failed to classify intent: {e}", "error")
            return "unknown"
    
    def get_project_timeline(self, project_id: str) -> Dict[str, Any]:
        """Get project timeline information"""
        try:
            timeline = self.timeline_manager.load_timeline(project_id)
            if not timeline:
                return {"error": "Timeline not found"}
            
            return {
                "project_id": project_id,
                "overall_progress": timeline.overall_progress,
                "estimated_completion": timeline.estimated_completion,
                "stages": [
                    {
                        "name": stage.name,
                        "status": stage.status,
                        "progress": stage.progress,
                        "started_at": stage.started_at,
                        "estimated_duration": stage.estimated_duration,
                        "actual_duration": stage.actual_duration,
                        "milestones": stage.milestones
                    }
                    for stage in timeline.stages
                ],
                "created_at": timeline.created_at,
                "updated_at": timeline.updated_at
            }
        except Exception as e:
            self.log(f"Failed to get project timeline: {e}", "error")
            return {"error": str(e)}

    async def execute_build_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the ProjectBlueprint produced by ArchitectAgent.

        Loads the blueprint from the stored context, iterates its build_plan, and for each
        FileTask calls the DeveloperAgent (available via self.tools) to generate the file
        using previously generated files as context. Each generated file is written to disk
        and stored in a generated_code_cache.
        """
        try:
            project_id = state.get('project_name') or state.get('project_id')
            if not project_id:
                raise ValueError('No project_name in state')

            ctx_mgr = ContextManager()
            ctx = ctx_mgr.load_context(project_id)
            if not ctx or not getattr(ctx, 'blueprint', None):
                raise RuntimeError('No ProjectBlueprint found in project context')

            blueprint = ctx.blueprint
            # blueprint.build_plan is a list of FileTask-like dicts or models
            build_plan = blueprint.build_plan if hasattr(blueprint, 'build_plan') else blueprint.get('build_plan', [])

            # Support resuming: respect any already generated files in state
            generated_code_cache: Dict[str, str] = {}
            generated_files: List[str] = list(state.get('generated_files', []))
            already_generated = set(generated_files)

            # Resolve developer and qa agents from registry
            dev_agent = self.get_agent('developer')

            for task_entry in build_plan:
                # Normalize to dict
                task = task_entry if isinstance(task_entry, dict) else task_entry.dict()
                path = task.get('path')

                # Skip files already generated (resume support)
                if path in already_generated:
                    self.log(f"[BUILD] Skipping already-generated file: {path}", "debug")
                    continue
                self.log(f"[BUILD] Generating: {path}", "info")

                # Convert to FileTask-like object if developer expects it
                try:
                    from pydantic import BaseModel
                    FileTask = None
                    try:
                        from utils.context_manager import FileTask as FT
                        FileTask = FT
                    except Exception:
                        FileTask = None

                    task_model = task
                    if FileTask:
                        task_model = FileTask.parse_obj(task)
                except Exception:
                    task_model = task

                # Call developer to generate code
                generated_code = None
                if dev_agent and hasattr(dev_agent, 'generate_file'):
                    # Support both awaitable and sync
                    try:
                        generated_code = await dev_agent.generate_file(task_model, ctx, generated_code_cache)
                    except TypeError:
                        # sync method
                        generated_code = dev_agent.generate_file(task_model, ctx, generated_code_cache)
                elif hasattr(self.tools, 'generate_code'):
                    generated_code = self.tools.generate_code(task=task_model, context=ctx, code_cache=generated_code_cache)
                else:
                    raise RuntimeError('Developer agent or code generator not available in tools')

                if not isinstance(generated_code, str):
                    # Try to extract content field
                    generated_code = getattr(generated_code, 'content', str(generated_code))

                # Save to cache
                generated_code_cache[path] = generated_code

                # Write file to disk (project root from context if present)
                project_root = getattr(ctx, 'project_root', '.')
                file_path = Path(project_root) / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(generated_code, encoding='utf-8')
                generated_files.append(path)

                # After each file generation, create an interactive checkpoint if enabled
                if self.interrupts_enabled:
                    checkpoint = self._create_checkpoint(project_id, f"file:{path}", {
                        "file": path,
                        "path_on_disk": str(file_path),
                        "preview": generated_code[:4000],
                        "qa": None
                    })
                    # Persist partially filled context and state so the UI can inspect files
                    state['generated_files'] = generated_files
                    ctx_mgr.save_context(project_id, ctx)
                    self.log(f"[BUILD] Pausing for human review at {path}. Checkpoint: {checkpoint['id']}", "info")
                    return {"interrupted": True, "checkpoint": checkpoint}

                # Optional QA verification (if available)
                qa_agent = self.get_agent('qa')

                if qa_agent and hasattr(qa_agent, 'verify_code'):
                    try:
                        qa_result = await qa_agent.verify_code(task_model, generated_code, ctx)
                        if not qa_result.get('valid', True):
                            error = qa_result.get('error', 'Unknown')
                            self.log(f"[BUILD] QA failed for {path}: {error}.", "warning")

                            # Let the orchestrator LLM decide whether to retry or proceed
                            decision_state = {
                                "project_name": project_id,
                                "current_step": "execute_build_plan",
                                "last_error": {"file": path, "error": error},
                                "generated_files": generated_files,
                                "steps_completed": state.get('steps_completed', [])
                            }
                            decision = await self.reason_and_act(decision_state, f"QA failed for {path}: {error}")
                            action = decision.get('action', 'proceed') if isinstance(decision, dict) else 'proceed'

                            if action in ("delegate_to_agent", "retry", "proceed_with_retry"):
                                # try one retry
                                self.log(f"[BUILD] Orchestrator decided to retry generation for {path}", "info")
                                if dev_agent and hasattr(dev_agent, 'generate_file'):
                                    generated_code = await dev_agent.generate_file(task_model, ctx, generated_code_cache)
                                    generated_code_cache[path] = generated_code
                                    file_path.write_text(generated_code, encoding='utf-8')
                                    # re-run QA
                                    qa_result = await qa_agent.verify_code(task_model, generated_code, ctx)
                                    if not qa_result.get('valid', True):
                                        self.log(f"[BUILD] QA failed after retry for {path}: {qa_result.get('error')}", "error")
                            else:
                                self.log(f"[BUILD] Orchestrator decided to proceed despite QA failure for {path}", "warning")
                    except Exception as e:
                        self.log(f"[BUILD] QA verification error for {path}: {e}", "warning")

            # After build loop, update state and context
            state['generated_files'] = generated_files
            ctx_mgr.save_context(project_id, ctx)

            # Run compile checks for Python files and attempt automated fixes
            try:
                project_root = getattr(ctx, 'project_root', '.')
                compile_report = self._compile_and_fix(project_root, generated_files)
                self.log(f"Compile report: {compile_report}", "info")
            except Exception as e:
                self.log(f"Compile/fix step failed: {e}", "warning")

            self.log(f"Build plan executed: {len(generated_files)} files generated", "success")
            return {"success": True, "generated_files": generated_files}

        except Exception as e:
            self.log(f"execute_build_plan failed: {e}", "error")
            return {"success": False, "error": str(e)}
    
    def complete_project(self, project_id: str, final_state: Dict[str, Any]):
        """Mark project as completed"""
        try:
            # Update final project state
            self.project_state_manager.update_stage_status(
                project_id=project_id,
                stage_name="devops",
                status=StageStatus.COMPLETED,
                agent_output=final_state
            )
            
            # Complete timeline
            self.timeline_manager.update_stage_progress(
                project_id=project_id,
                stage_name="devops",
                progress_percentage=100,
                milestone="Project completed"
            )
            
            # Add completion message to conversation
            self.conversation_manager.add_message(
                session_id=project_id,
                sender="ai",
                message="Project completed successfully!",
                intent="completion"
            )
            
            self.log(f"Project {project_id} marked as completed", "success")
            
        except Exception as e:
            self.log(f"Failed to complete project: {e}", "error")

    async def read_project_file(self, project_name: str, file_path: str):
        """Read a file from the project"""
        return self.file_manager.read_project_file(project_name, file_path)
    
    async def edit_project_file(self, project_name: str, file_path: str, **kwargs):
        """Edit a file in the project"""
        return self.file_manager.edit_project_file(project_name, file_path, **kwargs)
    
    async def delete_project_file(self, project_name: str, file_path: str):
        """Delete a file from the project"""
        return self.file_manager.delete_project_file(project_name, file_path)
    
    async def fix_file(self, project_name: str, file_path: str, issue: str):
        """Fix an issue in a file"""
        return await self.file_manager.fix_file_with_llm(
            project_name,
            file_path,
            issue,
            self.call_llm
        )
    
    async def refactor_file(self, project_name: str, file_path: str, instruction: str):
        """Refactor a file"""
        return await self.file_manager.refactor_file(
            project_name,
            file_path,
            instruction,
            self.call_llm
        )
    
    async def analyze_file(self, project_name: str, file_path: str):
        """Analyze a file for bugs"""
        return await self.file_manager.find_bugs_in_file(
            project_name,
            file_path,
            self.call_llm
        )
    
    async def _post_generation_management(
        self, 
        project_name: str, 
        dev_result: Dict[str, Any]
    ):
        """Orchestrator manages generated files"""
        
        self.log("Orchestrator: Inspecting generated project", "info")
        
        # Inspect project
        inspection = self.file_manager.inspect_project(project_name)
        self.log(f"Found {inspection['total_files']} files", "info")
        
        # Validate structure
        validation = self.file_manager.validate_project_structure(project_name)
        
        if not validation['is_complete']:
            self.log(f"Missing files: {validation['missing_files']}", "warning")
            
            # Create missing files
            for missing_file in validation['missing_files']:
                self.log(f"Creating missing file: {missing_file}", "info")
                await self.file_manager.create_missing_file(
                    project_name,
                    missing_file,
                    "Auto-generated missing file",
                    self.call_llm
                )
        
        # Search for TODOs/placeholders
        todo_search = self.file_manager.search_for_pattern(
            project_name,
            "TODO",
            file_pattern="*"
        )
        
        if todo_search['files_matched'] > 0:
            self.log(f"Found {todo_search['files_matched']} files with TODOs", "warning")
            
            # Fix TODOs
            for result in todo_search['results']:
                file_path = result['file'].replace(f"./workspace/{project_name}/", "")
                self.log(f"Fixing TODOs in {file_path}", "info")
                
                await self.file_manager.fix_file_with_llm(
                    project_name,
                    file_path,
                    "Remove all TODO comments and implement the functionality",
                    self.call_llm
                )
        
        self.log("Post-generation management complete", "success")

    def _create_checkpoint(self, project_id: str, step: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a JSON checkpoint that the UI/human can inspect and act upon.

        Returns checkpoint metadata (id, path, summary).
        """
        checkpoints_dir = Path("./workspace/.orchestrator_checkpoints")
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(self.tz).strftime("%Y%m%dT%H%M%S")
        cid = f"{project_id}_{step.replace('/', '_').replace(':', '_')}_{ts}"
        cp_path = checkpoints_dir / f"{cid}.json"
        record = {
            "id": cid,
            "project_id": project_id,
            "step": step,
            "timestamp": datetime.now(self.tz).isoformat(),
            "payload": payload
        }
        try:
            with open(cp_path, 'w', encoding='utf-8') as f:
                json.dump(record, f, indent=2)
        except Exception as e:
            self.log(f"Failed to write checkpoint {cid}: {e}", "warning")

        return {"id": cid, "path": str(cp_path), "summary": payload.get('file')}

    def _compile_and_fix(self, project_root: str, generated_files: List[str]) -> Dict[str, Any]:
        """Compile python files and attempt automated fixes using the file manager and LLM.

        Returns a report with successes and failures.
        """
        import py_compile

        report = {"compiled": [], "errors": []}
        project_root_path = Path(project_root)

        # Focus on generated_files (prefer relative paths)
        py_files = [f for f in generated_files if f.endswith('.py')]
        # If none specified, scan project for .py files
        if not py_files:
            py_files = [str(p.relative_to(project_root_path)) for p in project_root_path.rglob('*.py')]

        for rel in py_files:
            abs_path = project_root_path / rel
            try:
                py_compile.compile(str(abs_path), doraise=True)
                report['compiled'].append(rel)
            except py_compile.PyCompileError as e:
                err = str(e)
                self.log(f"Compilation error in {rel}: {err}", "warning")
                report['errors'].append({"file": rel, "error": err})

                # Attempt automated fix via file_manager (use LLM to patch)
                try:
                    fix_result = self.file_manager.fix_file_with_llm(
                        project_name=str(project_root_path.name),
                        file_path=rel,
                        issue=err,
                        call_llm=getattr(self, 'call_llm', None)
                    )

                    # If fix_result is coroutine, run it synchronously is not possible here;
                    # try to handle typical sync return
                    if hasattr(fix_result, '__await__'):
                        # Can't await here from sync context; log and skip
                        self.log(f"fix_file_with_llm returned coroutine for {rel}, skipping auto-await in sync context", "debug")
                    else:
                        if fix_result.get('success'):
                            # retry compile once
                            try:
                                py_compile.compile(str(abs_path), doraise=True)
                                report['compiled'].append(rel)
                                # remove from errors
                                report['errors'] = [e for e in report['errors'] if e['file'] != rel]
                            except Exception as ee:
                                self.log(f"Recompile after fix failed for {rel}: {ee}", "warning")
                except Exception as e2:
                    self.log(f"Automated fix failed for {rel}: {e2}", "warning")

        return report

    def checkpoint_agent_output(self, project_id: str, agent_name: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """Create a checkpoint after an agent finishes so a human can review.

        This is a convenience wrapper that writes a checkpoint file and returns metadata.
        """
        summary = {
            "agent": agent_name,
            "output_summary": output if len(str(output)) < 2000 else str(output)[:2000]
        }
        return self._create_checkpoint(project_id, f"agent:{agent_name}", summary)

    def resume_checkpoint(self, checkpoint_id: str, action: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Resume execution from a checkpoint.

        action: continue | modify_file | retry_agent | abort
        payload: depends on action
        """
        checkpoints_dir = Path("./workspace/.orchestrator_checkpoints")
        cp_path = checkpoints_dir / f"{checkpoint_id}.json"
        if not cp_path.exists():
            return {"success": False, "error": "checkpoint not found"}

        try:
            with open(cp_path, 'r', encoding='utf-8') as f:
                record = json.load(f)
        except Exception as e:
            return {"success": False, "error": f"failed to load checkpoint: {e}"}

        step = record.get('step', '')
        project_id = record.get('project_id')

        # Actions
        if action == 'continue':
            # simply remove checkpoint and indicate caller to resume orchestration
            try:
                cp_path.unlink()
            except Exception:
                pass
            return {"success": True, "resumed": True, "message": "Checkpoint cleared; resume orchestration."}

        if action == 'modify_file':
            # payload must contain 'file' and 'new_content'
            file_rel = payload.get('file') if payload else None
            new_content = payload.get('new_content') if payload else None
            if not file_rel or new_content is None:
                return {"success": False, "error": "modify_file requires 'file' and 'new_content' in payload"}
            # Write directly to disk (assume project workspace)
            project_root = f"./workspace/{project_id}"
            abs_path = Path(project_root) / file_rel
            try:
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                abs_path.write_text(new_content, encoding='utf-8')
                return {"success": True, "modified": True, "file": str(abs_path)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if action == 'retry_agent':
            # Signal orchestrator to retry: attach a human_response to persistent state
            # Caller should re-invoke execute_build_plan or the specific agent run with updated state
            # We simply record the intent into a small file for the orchestrator to pick up
            intent_file = Path(f"./workspace/.orchestrator_intents/{project_id}_intent.json")
            intent_file.parent.mkdir(parents=True, exist_ok=True)
            intent = {
                "checkpoint_id": checkpoint_id,
                "action": "retry",
                "payload": payload or {},
                "created_at": datetime.now(self.tz).isoformat()
            }
            try:
                with open(intent_file, 'w', encoding='utf-8') as f:
                    json.dump(intent, f, indent=2)
                return {"success": True, "intent_file": str(intent_file)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if action == 'abort':
            # mark project as aborted in persistent state
            try:
                self.persistent_state.setdefault('projects', {})
                self.persistent_state['projects'][project_id] = {'status': 'aborted', 'aborted_at': datetime.now(self.tz).isoformat()}
                self._save_persistent_state()
                return {"success": True, "aborted": True}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"unknown action: {action}"}