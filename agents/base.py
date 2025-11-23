from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from zoneinfo import ZoneInfo
import asyncio
import time
from pydantic import BaseModel

from core.config import Config
from utils.context_manager import ContextManager, AgentContext
from utils.project_state import ProjectStateManager
from utils.timeline_tracker import TimelineManager
from utils.conversation_manager import ConversationManager

# Timezone
_TZ = ZoneInfo("Asia/Kolkata")


# -------------------------
# Helper utilities
# -------------------------
def _normalize_payload(obj: Any) -> Any:
    """
    Normalize objects to plain Python types suitable for state and output.
    - Pydantic models -> .dict()
    - lists/dicts/primitives -> returned as-is
    - other objects -> attempt json.dumps then load, fallback to str()
    """
    if obj is None:
        return None

    # If already a primitive or container of primitives, return as-is
    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, list):
        return [_normalize_payload(x) for x in obj]

    if isinstance(obj, dict):
        return {k: _normalize_payload(v) for k, v in obj.items()}

    # Pydantic models
    if hasattr(obj, "model_dump"):
        try:
            d = obj.model_dump()
            # normalize nested entries
            return _normalize_payload(d)
        except Exception:
            # Fallback to dict() or other
            pass

    if hasattr(obj, "dict"):
        try:
            d = obj.dict()
            # normalize nested entries
            return _normalize_payload(d)
        except Exception:
            try:
                # try json serialization fallback
                return json.loads(json.dumps(obj, default=str))
            except Exception:
                return str(obj)

    # Last-resort: try to json serialize then parse back
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return str(obj)


# -------------------------
# BaseAgent
# -------------------------
class BaseAgent:
    """Base class for all agents with LLM integration and context awareness"""

    def get_agent_name(self) -> str:
        """Get the agent's name."""
        return self.name

    def get_agent_tools(self) -> Any:
        """Get the agent's tools."""
        return self.tools

    def __init__(
            self,
            name: str,
            tools: Any,
            temperature: float = Config.TEMPERATURE,
            max_tokens: int = Config.MAX_TOKENS,
            llm: Any = None
    ):
        self.name = name
        self.tools = tools
        self.tz = _TZ

        # Allow injecting a mock or preconfigured LLM for testing. If not provided,
        # attempt to load based on Config but do so defensively so imports don't
        # break tests on machines without the full LLM stack installed.
        if llm is not None:
            self.llm = llm
        else:
            try:
                self.llm = self._load_llm(temperature, max_tokens)
                print(f"✅ LLM initialized successfully for {name}")
            except Exception as e:
                # Log with full traceback for debugging
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ LLM initialization failed for {name}: {e}")
                print(f"Full error:\n{error_details}")
                self.llm = None

        # System prompt - override in subclass
        self.system_prompt = "You are a helpful AI assistant."

        # Initialize context management components
        self.context_manager = ContextManager()
        self.project_state_manager = ProjectStateManager()
        self.timeline_tracker = None  # Will be initialized per project
        self.conversation_manager = ConversationManager()
        self.timeline_manager = None  # Will be initialized on first update
        self.log_callback = None # Callback for real-time logging

    def set_log_callback(self, callback):
        """Set a callback function for real-time logging."""
        self.log_callback = callback

    def log(self, message: str, level: str = "info"):
        """Log a message to console and optionally via callback with structured JSON."""
        timestamp = datetime.now(self.tz).strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{self.name.upper()}] {message}"
        
        # Console logging
        if level == "error":
            print(f"\033[91m{formatted_msg}\033[0m")
        elif level == "warning":
            print(f"\033[93m{formatted_msg}\033[0m")
        elif level == "success":
            print(f"\033[92m{formatted_msg}\033[0m")
        else:
            print(formatted_msg)
            
        # Real-time callback with structured JSON - check if attribute exists first
        if hasattr(self, 'log_callback') and self.log_callback:
            # Create structured log message for frontend
            log_data = {
                "type": "LOG",
                "level": level,
                "message": message,
                "agent": self.name.upper(),
                "timestamp": datetime.now(self.tz).isoformat()
            }
            
            # We need to run this async callback in the event loop if it's async
            # But log is sync. So we check if there's a running loop.
            try:
                loop = asyncio.get_running_loop()
                if asyncio.iscoroutinefunction(self.log_callback):
                    loop.create_task(self.log_callback(log_data))
                else:
                    self.log_callback(log_data)
            except RuntimeError:
                # No running loop, just skip or run sync
                pass

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
                    xai_api_key=api_key,  # Grok uses xai_api_key
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except ImportError:
                raise ImportError("Please install langchain-xai to use xAI (Grok) models.")
        elif provider == "google":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from google.generativeai import types  # noqa: F401
                import os
                
                # Newer versions of langchain-google-genai require GOOGLE_API_KEY env var
                # even if we pass google_api_key parameter. Set it explicitly.
                os.environ["GOOGLE_API_KEY"] = api_key
                
                # Ensure model name has "models/" prefix for newer API versions
                if not model_name.startswith("models/"):
                    model_name = f"models/{model_name}"
                
                return ChatGoogleGenerativeAI(
                    model=model_name,
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

    def create_prompt(self, system_message: str):
        """Create prompt template. Uses lazy import to avoid heavy imports at module load."""
        try:
            from langchain_core.prompts import ChatPromptTemplate
        except Exception:
            # Fallback minimal template when langchain isn't available
            class _FallbackTemplate:
                @staticmethod
                def from_messages(messages):
                    class Templ:
                        def format(self, **kwargs):
                            return kwargs.get('input', '')

                        def __str__(self):
                            return system_message

                    return Templ()

            ChatPromptTemplate = _FallbackTemplate

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}")
        ])

    def _truncate_prompt(self, prompt: str, max_tokens: int) -> str:
        """Truncates a prompt to a maximum number of tokens."""
        tokens = 0
        try:
            tokens = self.tools.count_tokens(prompt)
        except Exception:
            # fallback: estimate tokens by words
            tokens = len(prompt.split())

        if tokens <= max_tokens:
            return prompt

        ratio = max_tokens / tokens
        new_length = int(len(prompt) * ratio)
        truncated_prompt = prompt[:new_length]

        last_space = truncated_prompt.rfind(' ')
        if last_space != -1:
            truncated_prompt = truncated_prompt[:last_space]

        self.log(
            f"Prompt truncated from {tokens} to approx {self.tools.count_tokens(truncated_prompt) if hasattr(self.tools, 'count_tokens') else 'N/A'} tokens.",
            "warning")
        return truncated_prompt

    async def call_llm(self, prompt: str, output_schema: Optional[BaseModel] = None) -> Any:
        """Make LLM call with current system prompt, optionally with structured output"""
        if self.llm is None:
            raise RuntimeError(f"LLM not initialized for agent {self.name}. Check configuration and dependencies.")

        truncated_prompt = self._truncate_prompt(prompt, 60000)
        template = self.create_prompt(self.system_prompt)

        # Add gRPC error handling with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if output_schema:
                    # structured output (pydantic model) - return the model object (caller may normalize)
                    llm_with_structure = self.llm.with_structured_output(output_schema)
                    response = await llm_with_structure.ainvoke(template.format(input=truncated_prompt))
                    self.log(f"Raw LLM response in call_llm (structured): {response}", "debug")
                    return response
                else:
                    # unstructured text
                    response = await self.llm.ainvoke(template.format(input=truncated_prompt))
                    # some wrappers return an object with .content, others return string
                    content = getattr(response, "content", response)
                    self.log(f"Raw LLM response in call_llm (unstructured): {content}", "debug")
                    return content
            except BlockingIOError as e:
                if "10035" in str(e):  # Windows-specific gRPC error
                    self.log(f"gRPC BlockingIOError (attempt {attempt + 1}): {e}", "warning")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1 * (attempt + 1))  # Small delay
                        continue
                    else:
                        self.log("gRPC error persisted after retries, continuing", "warning")
                        if output_schema:
                            # Return a default structured response
                            return self._create_fallback_structured_response(output_schema)
                        else:
                            return "LLM temporarily unavailable due to network issues"
                else:
                    raise
            except Exception as e:
                self.log(f"LLM invocation failed (attempt {attempt + 1}): {e}", "error")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    raise

    async def call_llm_json(self, prompt: str, output_schema: BaseModel) -> BaseModel:
        """
        Make LLM call expecting structured JSON response.
        Returns the structured object (Pydantic model or similar). Caller can normalize it.
        """
        response = await self.call_llm(prompt, output_schema=output_schema)
        self.log(f"Raw LLM response (structured): {response}", "debug")
        return response

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool by name with defensive handling and retries"""
        if not hasattr(self.tools, tool_name):
            return {"success": False, "error": f"Tool {tool_name} not found"}

        tool_method = getattr(self.tools, tool_name)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                result = tool_method(**kwargs)
                # Normalize tool result if it's not a dict
                if not isinstance(result, dict):
                    try:
                        result = _normalize_payload(result)
                        if not isinstance(result, dict):
                            result = {"success": False, "result": result}
                    except Exception:
                        result = {"success": False, "error": "Tool returned non-dict result"}
                self.log(f"Tool {tool_name} called: {result.get('success', False)}", "debug")
                return result
            except Exception as e:
                self.log(f"Tool {tool_name} failed (attempt {attempt + 1}): {e}", "warning")
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    self.log(f"Tool {tool_name} failed after {max_retries} attempts: {e}", "error")
                    return {"success": False, "error": str(e)}

    def create_output(
            self,
            success: bool,
            data: Dict[str, Any],
            documents: List[Dict[str, str]] = None,
            artifacts: List[str] = None,
            errors: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized agent output and normalize data/documents to plain types.
        This prevents pydantic models or other complex objects from leaking into shared state.
        """
        data_norm = _normalize_payload(data) if data is not None else {}
        documents_norm = []
        for d in (documents or []):
            if isinstance(d, dict):
                documents_norm.append(_normalize_payload(d))
            else:
                documents_norm.append(_normalize_payload(d))

        artifacts_norm = artifacts or []
        errors_norm = errors or []

        return {
            "agent_name": self.name,
            "success": success,
            "data": data_norm,
            "documents": documents_norm,
            "artifacts": artifacts_norm,
            "errors": errors_norm,
            "timestamp": datetime.now(self.tz).isoformat()
        }


    def load_context(self, project_id: str) -> Optional[AgentContext]:
        """Load comprehensive context for the project"""
        try:
            context = self.context_manager.load_context(project_id)
            if context:
                self.log(f"Loaded context for project {project_id}", "info")
                return context
            else:
                self.log(f"No context found for project {project_id}", "warning")
                return None
        except Exception as e:
            self.log(f"Error loading context for {project_id}: {e}", "error")
            return None

    def get_agent_specific_context(self, project_id: str) -> Dict[str, Any]:
        """Get context specific to this agent type"""
        try:
            if self.name == "requirements_analyst":
                return self.context_manager.get_requirements_context(project_id)
            elif self.name == "system_architect":
                return self.context_manager.get_architecture_context(project_id)
            elif self.name == "developer":
                return self.context_manager.get_development_context(project_id)
            elif self.name == "qa_engineer":
                return self.context_manager.get_qa_context(project_id)
            elif self.name == "devops_engineer":
                return self.context_manager.get_devops_context(project_id)
            else:
                return {}
        except Exception as e:
            self.log(f"Error getting agent-specific context: {e}", "error")
            return {}

    def update_project_state(self, project_id: str, stage_name: str,
                             agent_output: Dict[str, Any], errors: List[str] = None) -> bool:
        """Update project state with agent output"""
        try:
            from utils.project_state import StageStatus

            # Determine stage status
            if agent_output.get("success", False):
                status = StageStatus.COMPLETED
            else:
                status = StageStatus.FAILED

            # Update stage status
            success = self.project_state_manager.update_stage_status(
                project_id, stage_name, status, agent_output, errors
            )

            if success:
                self.log(f"Updated project state for {stage_name}", "info")
            else:
                self.log(f"Failed to update project state for {stage_name}", "warning")

            return success
        except Exception as e:
            self.log(f"Error updating project state: {e}", "error")
            return False

    def update_timeline(self, project_id: str, stage_name: str,
                        progress_percentage: float = None, milestone: str = None) -> bool:
        """Update timeline progress"""
        try:
            # --- FIX: Instantiate or get the manager ---
            # The manager needs to be stored on self or instantiated here.
            if not hasattr(self, 'timeline_manager') or self.timeline_manager is None:
                from utils.timeline_tracker import TimelineManager
                self.timeline_manager = TimelineManager()

            # Load the timeline tracker object if it's not loaded
            if not self.timeline_tracker:
                self.timeline_tracker = self.timeline_manager.load_timeline(project_id)

                if not self.timeline_tracker:
                    self.timeline_tracker = self.timeline_manager.create_timeline(project_id)

            if progress_percentage is not None:
                # --- FIX: Call the method on the MANAGER, not the timeline object ---
                # Pass the project_id to the manager's method.
                return self.timeline_manager.update_stage_progress(
                    project_id, stage_name, progress_percentage, milestone
                )

            return True
        except Exception as e:
            self.log(f"Error updating timeline: {e}", "error")
            return False

    def build_context_aware_prompt(self, project_id: str, base_prompt: str,
                                   additional_context: Dict[str, Any] = None) -> str:
        """Build a comprehensive prompt with full context"""
        try:
            # Load project context
            context = self.load_context(project_id)
            agent_context = self.get_agent_specific_context(project_id)

            # Build context section
            context_section = ""

            if context:
                context_section += f"\n\n**PROJECT CONTEXT:**\n"
                context_section += f"Project Type: {context.project_type.value}\n"
                context_section += f"Complexity: {context.complexity_level}\n"
                context_section += f"Technology Stack: {context.technology_stack.to_dict()}\n"

                if context.functional_requirements:
                    context_section += f"\n**FUNCTIONAL REQUIREMENTS:**\n"
                    for req in context.functional_requirements[:5]:  # Limit to 5
                        context_section += f"- {req.description}\n"

                if context.component_specifications:
                    context_section += f"\n**COMPONENT SPECIFICATIONS:**\n"
                    for comp in context.component_specifications[:3]:  # Limit to 3
                        context_section += f"- {comp.name}: {comp.description}\n"

            # Add agent-specific context
            if agent_context:
                context_section += f"\n**AGENT-SPECIFIC CONTEXT:**\n"
                for key, value in agent_context.items():
                    if isinstance(value, (str, int, float, bool)):
                        context_section += f"{key}: {value}\n"
                    elif isinstance(value, list) and len(value) > 0:
                        context_section += f"{key}: {', '.join(map(str, value[:3]))}\n"

            # Add additional context if provided
            if additional_context:
                context_section += f"\n**ADDITIONAL CONTEXT:**\n"
                for key, value in additional_context.items():
                    context_section += f"{key}: {value}\n"

            # Combine base prompt with context
            full_prompt = base_prompt + context_section

            return full_prompt

        except Exception as e:
            self.log(f"Error building context-aware prompt: {e}", "error")
            return base_prompt  # Fallback to base prompt

    def validate_llm_response(self, response: Any, expected_type: str = "string") -> Any:
        """Validate LLM response and provide fallback if needed"""
        try:
            if response is None:
                self.log("LLM returned None response", "warning")
                return self._get_fallback_response(expected_type)

            if expected_type == "string":
                if isinstance(response, str):
                    return response.strip()
                else:
                    # Try to extract string content
                    content = getattr(response, "content", str(response))
                    return str(content).strip()

            elif expected_type == "dict":
                if isinstance(response, dict):
                    return response
                elif hasattr(response, "dict"):
                    return response.dict()
                else:
                    try:
                        return json.loads(str(response))
                    except:
                        return {"error": "Could not parse response as dict"}

            elif expected_type == "list":
                if isinstance(response, list):
                    return response
                else:
                    try:
                        parsed = json.loads(str(response))
                        if isinstance(parsed, list):
                            return parsed
                        else:
                            return [parsed]
                    except:
                        return ["Could not parse response as list"]

            return response

        except Exception as e:
            self.log(f"Error validating LLM response: {e}", "error")
            return self._get_fallback_response(expected_type)

    def _get_fallback_response(self, expected_type: str) -> Any:
        """Get fallback response based on expected type"""
        if expected_type == "string":
            return f"Fallback response from {self.name} due to LLM error"
        elif expected_type == "dict":
            return {"error": f"Fallback response from {self.name}", "success": False}
        elif expected_type == "list":
            return [f"Fallback response from {self.name}"]
        else:
            return None

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method - must be implemented by each agent
        Returns updated state
        """
        raise NotImplementedError(f"{self.name} must implement execute()")

    def save_document(
            self,
            project_name: str,
            doc_type: str,
            filename: str,
            content: str
    ) -> Optional[Dict[str, Any]]:
        """Save document, broadcast to frontend, and return doc entry"""
        path = f"{project_name}/{filename}"
        result = self.call_tool("write_file", path=path, content=content)

        if result.get("success"):
            doc_entry = {
                "type": doc_type,
                "filename": filename,
                "path": path,
                "created_at": datetime.now(self.tz).isoformat()
            }
            
            # Broadcast file generation to frontend via WebSocket
            if hasattr(self, 'log_callback') and self.log_callback:
                file_message = {
                    "type": "FILE_GENERATED",
                    "doc_type": doc_type,
                    "filename": filename,
                    "path": path,
                    "content": content[:500] if len(content) > 500 else content,  # Send preview
                    "full_content": content,  # Send full content for viewing
                    "auto_focus": True,  # Auto-switch tab to this file
                    "timestamp": datetime.now(self.tz).isoformat()
                }
                
                try:
                    loop = asyncio.get_running_loop()
                    if asyncio.iscoroutinefunction(self.log_callback):
                        loop.create_task(self.log_callback(file_message))
                    else:
                        self.log_callback(file_message)
                except RuntimeError:
                    pass

            # Embed document in vector store for RAG
            try:
                from backend.core.context_store import ProjectContextStore
                context_store = ProjectContextStore()
                
                # Extract project ID from path (e.g., "proj-123/docs/..." -> "proj-123")
                project_id = project_name.split('/')[0]
                
                context_store.add_document(
                    project_id=project_id,
                    doc_id=f"{doc_type}_{filename}",
                    content=content,
                    metadata={
                        "filename": filename,
                        "doc_type": doc_type,
                        "agent": self.name,
                        "timestamp": datetime.now(self.tz).isoformat()
                    }
                )
                self.log(f"Document {filename} embedded for RAG context", "success")
            except Exception as e:
                self.log(f"Failed to embed document: {e}", "warning")
            
            return doc_entry
        return None

    def _create_fallback_structured_response(self, output_schema: BaseModel) -> BaseModel:
        """Create a fallback structured response when gRPC fails"""
        try:
            # Try to create a minimal valid response
            if hasattr(output_schema, '__fields__'):
                # Pydantic v1
                fields = output_schema.__fields__
            elif hasattr(output_schema, 'model_fields'):
                # Pydantic v2
                fields = output_schema.model_fields
            else:
                # Fallback to empty dict
                return output_schema()

            # Create minimal data with default values
            data = {}
            for field_name, field_info in fields.items():
                if hasattr(field_info, 'default'):
                    data[field_name] = field_info.default
                elif hasattr(field_info, 'default_factory'):
                    data[field_name] = field_info.default_factory()
                else:
                    # Use type-based defaults
                    field_type = getattr(field_info, 'type_', str)
                    if field_type == str:
                        data[field_name] = "Fallback response due to network issues"
                    elif field_type == list:
                        data[field_name] = []
                    elif field_type == dict:
                        data[field_name] = {}
                    elif field_type == int:
                        data[field_name] = 0
                    elif field_type == float:
                        data[field_name] = 0.0
                    elif field_type == bool:
                        data[field_name] = False
                    else:
                        data[field_name] = None

            return output_schema(**data)
        except Exception as e:
            self.log(f"Failed to create fallback response: {e}", "error")
            # Return empty instance
            return output_schema()
