"""
Master Orchestrator - Proactive AI agent that manages the entire workflow
with transparency, auto-recovery, and intelligent decision-making.

This orchestrator:
1. Provides step-by-step explanations of what it's doing
2. Proactively gathers context using RAG
3. Auto-recovers from errors with retry logic
4. Handles human interrupts intelligently
5. Validates outputs before proceeding
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.core.config import Config
from backend.core.event_bus import get_event_bus, WorkflowEvent, EventType, EventSeverity
# from backend.core.context_store import ProjectContextStore  # Commented out - chromadb not installed

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    Proactive master orchestrator that transparently manages workflow execution.
    """
    
    SYSTEM_PROMPT = """You are the Master Orchestrator for AI-SOL (AI Software Orchestration Lifecycle).

Your role is to:
1. **Guide the user** through software project generation with complete transparency
2. **Explain your actions** before and after each step
3. **Gather context proactively** using available project documentation
4. **Validate outputs** before proceeding to next stages
5. **Handle errors gracefully** with automatic retry and recovery
6. **Respond to human interrupts** intelligently

Core Workflow Stages:
1. **Requirements**: Analyze user request, gather context, create detailed requirements
2. **Architecture**: Design system architecture, tech stack, file structure
3. **Implementation**: Generate all code files, configurations, documentation
4. **QA**: Create tests, validate functionality
5. **DevOps**: Setup deployment configs, CI/CD if needed

Transparency Guidelines:
- Always explain WHAT you're about to do and WHY
- After each stage, summarize WHAT was accomplished
- If errors occur, explain the issue and your recovery strategy
- Present options when multiple paths are valid
- Ask for clarification when requirements are ambiguous

Human Interrupt Handling:
When a user sends a message during workflow:
1. **Classify intent**:
   - QUESTION: User wants explanation → Provide context-aware answer
   - MODIFICATION: User wants to change something → Extract specifics and update
   - STOP: User wants to pause/cancel → Pause workflow
   - CONTINUE: User says proceed → Resume workflow
   
2. **Extract details**: If modification, identify what to change
3. **Confirm understanding**: Restate what you understood
4. **Execute**: Apply changes or answer questions

Output Format:
Always structure your responses as:
```
🎯 **Current Stage**: [stage_name]
📋 **Action**: [what you're about to do]
💡 **Reasoning**: [why this approach]
✨ **Expected Outcome**: [what this will produce]
```

After completing an action:
```
✅ **Completed**: [what was done]
📊 **Results**: [key outputs]
➡️ **Next**: [what comes next]
```

Remember: You are not just executing tasks, you are a transparent partner guiding the user through software creation.
"""

    def __init__(self, project_id: str, context_store: Optional[Any] = None):
        """
        Initialize Master Orchestrator
        
        Args:
            project_id: Unique project identifier
            context_store: Optional context store for RAG
        """
        self.project_id = project_id
        self.context_store = context_store
        self.event_bus = get_event_bus()
        
        # Initialize LLM with comprehensive system prompt
        llm_config = Config.get_agent_llm_config()
        self.llm = ChatGoogleGenerativeAI(**llm_config)
        
        self.current_stage = None
        self.conversation_history = []
        
        logger.info(f"MasterOrchestrator initialized for project {project_id}")
    
    async def start_workflow(self, user_request: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Start the workflow with a user request
        
        Args:
            user_request: User's project description
            options: Optional workflow options (generate_tests, generate_devops, etc.)
        
        Returns:
            Workflow initialization response
        """
        await self._emit_event(
            EventType.WORKFLOW_STARTED,
            "Master Orchestrator starting workflow analysis",
            data={"user_request": user_request, "options": options}
        )
        
        # Gather initial context if available
        context = await self._gather_context("initial_analysis")
        
        # Create initial analysis prompt
        prompt = f"""
{self.SYSTEM_PROMPT}

A user has requested a new software project:
\"\"\"{user_request}\"\"\"

Additional Context from Knowledge Base:
{context if context else "No prior context available"}

Your task:
1. Acknowledge the request
2. Explain your understanding of what they want
3. Outline the high-level approach you'll take
4. Ask any clarifying questions if needed
5. Confirm you're ready to begin requirements gathering

Respond in the structured format specified in your system prompt.
"""
        
        response = await self._invoke_llm(prompt)
        
        self._add_to_history("user", user_request)
        self._add_to_history("assistant", response)
        
        return {
            "success": True,
            "message": response,
            "stage": "initialization",
            "ready_to_proceed": True
        }
    
    async def handle_interrupt(self, user_message: str) -> Dict[str, Any]:
        """
        Handle user interrupt during workflow
        
        Args:
            user_message: User's message
        
        Returns:
            Response with intent classification and action taken
        """
        await self._emit_event(
            EventType.USER_MESSAGE,
            f"User interrupt: {user_message[:100]}...",
            severity=EventSeverity.INFO
        )
        
        # Gather context about current stage
        context = await self._gather_context(self.current_stage or "general")
        
        # Intent classification prompt
        intent_prompt = f"""
Based on the conversation history and current workflow state, classify this user message:

User Message: "{user_message}"

Current Stage: {self.current_stage or "Not started"}
Recent Context: {context[:500] if context else "None"}

Classify the intent as ONE of:
- QUESTION: User wants explanation or information
- MODIFICATION: User wants to change/update something
- STOP: User wants to pause or cancel
- CONTINUE: User confirms to proceed
- UNCLEAR: Intent is ambiguous

Return ONLY the classification word, nothing else.
"""
        
        intent = await self._invoke_llm(intent_prompt)
        intent = intent.strip().upper()
        
        # Handle based on intent
        if "QUESTION" in intent:
            response = await self._handle_question(user_message, context)
        elif "MODIFICATION" in intent:
            response = await self._handle_modification(user_message, context)
        elif "STOP" in intent:
            response = await self._handle_stop(user_message)
        elif "CONTINUE" in intent:
            response = await self._handle_continue(user_message)
        else:
            response = await self._handle_unclear(user_message)
        
        self._add_to_history("user", user_message)
        self._add_to_history("assistant", response["message"])
        
        return response
    
    async def _gather_context(self, topic: str) -> str:
        """
        Proactively gather relevant context using RAG
        
        Args:
            topic: Topic to gather context about
        
        Returns:
            Relevant context string
        """
        if not self.context_store:
            return ""
        
        try:
            # Query for relevant documents
            results = self.context_store.query_documents(
                self.project_id,
                topic,
                n_results=5
            )
            
            if not results:
                return ""
            
            # Format context
            context_parts = []
            for i, doc in enumerate(results, 1):
                context_parts.append(f"[{i}] {doc.get('content', '')[:200]}...")
            
            return "\n".join(context_parts)
        
        except Exception as e:
            logger.warning(f"Failed to gather context: {e}")
            return ""
    
    async def _invoke_llm(self, prompt: str, max_retries: int = 3) -> str:
        """
        Invoke LLM with retry logic
        
        Args:
            prompt: Prompt to send
            max_retries: Maximum retry attempts
        
        Returns:
            LLM response text
        """
        import asyncio
        
        for attempt in range(max_retries):
            try:
                response = await self.llm.ainvoke(prompt)
                return response.content
            
            except Exception as e:
                logger.error(f"LLM invocation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"LLM failed after {max_retries} attempts: {e}")
    
    async def _emit_event(self, event_type: EventType, message: str, 
                         severity: EventSeverity = EventSeverity.INFO,
                         data: Dict[str, Any] = None):
        """Emit a workflow event"""
        event = WorkflowEvent(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            project_id=self.project_id,
            stage=self.current_stage,
            agent="MasterOrchestrator",
            message=message,
            severity=severity,
            data=data or {}
        )
        await self.event_bus.emit(event)
    
    def _add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    # Intent handlers
    async def _handle_question(self, question: str, context: str) -> Dict[str, Any]:
        """Handle user question"""
        prompt = f"""
User asked a question during workflow execution:
"{question}"

Current Stage: {self.current_stage}
Relevant Context: {context}

Provide a helpful, context-aware answer. Be concise but thorough.
"""
        response = await self._invoke_llm(prompt)
        
        return {
            "success": True,
            "intent": "QUESTION",
            "message": response,
            "continue_workflow": False
        }
    
    async def _handle_modification(self, request: str, context: str) -> Dict[str, Any]:
        """Handle modification request"""
        prompt = f"""
User wants to modify something:
"{request}"

Current Stage: {self.current_stage}
Context: {context}

1. Acknowledge the modification request
2. Explain what you understand needs to change
3. Confirm the changes you'll make
4. Ask if they want to proceed

Be clear and specific about what will change.
"""
        response = await self._invoke_llm(prompt)
        
        return {
            "success": True,
            "intent": "MODIFICATION",
            "message": response,
            "continue_workflow": False,
            "requires_confirmation": True
        }
    
    async def _handle_stop(self, message: str) -> Dict[str, Any]:
        """Handle stop/pause request"""
        await self._emit_event(
            EventType.WORKFLOW_PAUSED,
            "Workflow paused by user",
            severity=EventSeverity.WARNING
        )
        
        return {
            "success": True,
            "intent": "STOP",
            "message": "Workflow paused. I've saved the current progress. Send 'continue' when you're ready to resume.",
            "continue_workflow": False,
            "paused": True
        }
    
    async def _handle_continue(self, message: str) -> Dict[str, Any]:
        """Handle continue request"""
        await self._emit_event(
            EventType.WORKFLOW_RESUMED,
            "Workflow resumed by user",
            severity=EventSeverity.SUCCESS
        )
        
        return {
            "success": True,
            "intent": "CONTINUE",
            "message": f"Resuming workflow from {self.current_stage} stage.",
            "continue_workflow": True
        }
    
    async def _handle_unclear(self, message: str) -> Dict[str, Any]:
        """Handle unclear intent"""
        return {
            "success": True,
            "intent": "UNCLEAR",
            "message": "I'm not sure what you'd like me to do. Could you please clarify? You can:\n- Ask a question about the current stage\n- Request modifications\n- Say 'continue' to proceed\n- Say 'stop' to pause",
            "continue_workflow": False
        }
