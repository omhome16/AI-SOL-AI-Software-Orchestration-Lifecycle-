"""
Interactive Chat Orchestrator for AI-SOL with RAG
Enables natural language control of the workflow via intelligent chat interface.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.core.config import Config
import json

logger = logging.getLogger(__name__)


class UserIntent(BaseModel):
    """Represents the classified intent from user's message"""
    action: str  # "approve", "modify", "regenerate", "explain", "question"
    target: Optional[str] = None  # Which file/concept
    modifications: Optional[Dict[str, Any]] = None  # Requested changes
    question: Optional[str] = None
    confidence: float = 0.0  # 0.0 to 1.0


class InteractiveChatOrchestrator:
    """
    Intelligent orchestrator that understands natural language and controls workflow.
    Uses LLM with RAG to classify user intents and execute appropriate actions.
    """
    
    def __init__(self, state_manager, workflow_engine=None, context_store=None, conversation_store=None):
        """
        Initialize the chat orchestrator.
        
        Args:
            state_manager: ProjectStateManager for loading/saving project data
            workflow_engine: Optional WorkflowEngine instance for resuming workflows
            context_store: Optional ProjectContextStore for RAG
            conversation_store: Optional ConversationStore for persistence
        """
        self.state_manager = state_manager
        self.workflow_engine = workflow_engine
        self.context_store = context_store
        self.conversation_store = conversation_store
        self.conversation_history: Dict[str, List[Dict]] = {}  # project_id -> messages
        
        # Initialize LLM for intent classification - use faster Flash model
        try:
            llm_config = Config.get_orchestrator_llm_config()
            self.llm = ChatGoogleGenerativeAI(**llm_config)
            logger.info(f"InteractiveChatOrchestrator LLM initialized: {llm_config['model']}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
    
    async def process_message(self, project_id: str, user_message: str) -> Dict[str, Any]:
        """
        Process user message and determine appropriate action.
        
        Args:
            project_id: ID of the project
            user_message: User's chat message
            
        Returns:
            Response dict with message, action, and optional buttons
        """
        logger.info(f"Processing message for {project_id}: {user_message}")
        
        # Get project context
        project = self.state_manager.load_project(project_id)
        if not project:
            return {
                "message": "Project not found. Please try again.",
                "action": "error",
                "buttons": []
            }
        
        current_stage = project.get("current_step", "unknown")
        workflow_status = project.get("status", "unknown")
        generated_files = project.get("generated_files", [])
        
        # Build context for LLM
        context = self._build_context(project_id, current_stage, generated_files, workflow_status)
        
        # Classify user intent using LLM
        intent = await self._classify_intent(user_message, context)
        
        logger.info(f"Classified intent: {intent.action} (confidence: {intent.confidence})")
        
        # Execute action based on intent
        if intent.action == "approve":
            return await self._handle_approval(project_id, current_stage)
        elif intent.action == "modify":
            return await self._handle_modification(project_id, intent.modifications or {}, user_message)
        elif intent.action == "regenerate":
            return await self._handle_regeneration(project_id, user_message)
        elif intent.action == "explain":
            return await self._handle_explanation_with_rag(project_id, intent.target or user_message, context)
        else:  # question
            return await self._handle_question_with_rag(project_id, user_message, context)
    
    def _build_context(self, project_id: str, current_stage: str, generated_files: List[str], 
                       workflow_status: str) -> str:
        """Build context string for LLM"""
        # Handle generated_files being list of dicts or strings
        file_list = []
        if generated_files:
            for f in generated_files:
                if isinstance(f, dict):
                    file_list.append(f.get("filename", "unknown"))
                else:
                    file_list.append(str(f))
        
        context = f"""
Project ID: {project_id}
Current Stage: {current_stage}
Workflow Status: {workflow_status}
Generated Files: {', '.join(file_list) if file_list else 'None yet'}
"""
        return context.strip()
    
    async def _classify_intent(self, message: str, context: str) -> UserIntent:
        """
        Use LLM to classify user's intent from their message.
        
        Args:
            message: User's message
            context: Project context
            
        Returns:
            UserIntent object
        """
        if not self.llm:
            # Fallback: simple keyword matching
            return self._fallback_intent_classification(message)
        
        prompt = f"""
You are analyzing a user's message in the context of an AI project generation workflow.

Current Context:
{context}

User Message: "{message}"

Classify the user's intent. Choose ONE action:
- "approve": User wants to proceed (e.g., "looks good", "approve", "continue", "proceed", "LGTM", "yes", "ok")
- "modify": User wants to change something specific (e.g., "change X to Y", "add Z", "remove A")
- "regenerate": User wants complete regeneration with new context
- "explain": User wants explanation of a concept/file/decision (e.g., "why X?", "explain Y")
- "question": General question about the project/process

For "modify" actions, extract what they want to modify.
For "explain" actions, extract what they want explained.

Return ONLY valid JSON matching this schema:
{{
  "action": "approve|modify|regenerate|explain|question",
  "target": "what to explain or modify (optional)",
  "modifications": {{"description": "what to change"}},
  "confidence": 0.0-1.0
}}

JSON:"""

        try:
            response = await self.llm.ainvoke(prompt)
            response_text = response.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            intent_data = json.loads(response_text)
            return UserIntent(**intent_data)
            
        except Exception as e:
            logger.error(f"LLM intent classification failed: {e}")
            return self._fallback_intent_classification(message)
    
    def _fallback_intent_classification(self, message: str) -> UserIntent:
        """Fallback intent classification using keyword matching"""
        message_lower = message.lower()
        
        # Approval keywords
        if any(word in message_lower for word in ['approve', 'proceed', 'continue', 'looks good', 'lgtm', 'yes', 'ok', 'fine']):
            return UserIntent(action="approve", confidence=0.7)
        
        # Modification keywords
        if any(word in message_lower for word in ['add', 'change', 'modify', 'update', 'remove', 'delete']):
            return UserIntent(
                action="modify",
                modifications={"description": message},
                confidence=0.6
            )
        
        # Explanation keywords
        if any(word in message_lower for word in ['why', 'explain', 'how', 'what is']):
            return UserIntent(action="explain", target=message, confidence=0.6)
        
        # Default to question
        return UserIntent(action="question", question=message, confidence=0.5)
    
    async def _handle_approval(self, project_id: str, current_stage: str) -> Dict[str, Any]:
        """Handle approval - resume workflow to next stage"""
        logger.info(f"Handling approval for {project_id}, stage: {current_stage}")
        
        # Update project status
        project = self.state_manager.load_project(project_id)
        if project:
            project["awaiting_review"] = False
            self.state_manager.save_project(project_id, project)
        
        # If workflow engine is available, resume it
        if self.workflow_engine:
            await self.workflow_engine.resume()
        
        return {
            "message": f"✅ Approved! Proceeding to the next stage...",
            "action": "approve",  # Changed from "resume_workflow" to "approve"
            "buttons": []
        }
    
    async def _handle_modification(self, project_id: str, modifications: Dict, user_message: str) -> Dict[str, Any]:
        """Handle modification request - re-run current stage with changes"""
        logger.info(f"Handling modification for {project_id}: {modifications}")
        
        project = self.state_manager.load_project(project_id)
        current_stage = project.get("current_step", "requirements")
        
        # Store modification context for the agent to use
        if "modification_context" not in project:
            project["modification_context"] = {}
        
        project["modification_context"][current_stage] = {
            "original_message": user_message,
            "modifications": modifications,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update user context with modifications if they're specific
        if modifications and "user_context" in project:
            # Merge modifications into user_context
            for key, value in modifications.items():
                if key in project["user_context"]:
                    project["user_context"][key] = value
        
        self.state_manager.save_project(project_id, project)
        
        # If we have a workflow engine, trigger re-execution
        if self.workflow_engine and current_stage == "requirements":
            try:
                from agents.requirements import RequirementsAgent
                
                logger.info(f"Re-running Requirements Agent with modifications for {project_id}")
                
                # Create agent and re-execute
                requirements_agent = RequirementsAgent(tools=self.workflow_engine.tools)
                requirements_agent.set_log_callback(self.workflow_engine.broadcast)
                
                # Execute with updated state (includes modification_context)
                output = await requirements_agent.execute(project)
                
                # Update project with new output
                project.update(output)
                
                # Save updated requirements
                from backend.utils.file_manager import get_file_manager
                file_manager = get_file_manager()
                
                if "requirements_output" in output:
                    req_output = output["requirements_output"]
                    # Generate markdown from output
                    from backend.core.markdown_formatter import get_markdown_formatter
                    formatter = get_markdown_formatter()
                    content = await formatter.format("requirements", output, project.get("type", "website"))
                    
                    # Save to file
                    file_path = file_manager.save_file(
                        project_id,
                        project.get("project_name", project_id),
                        "requirements.md",
                        content
                    )
                    logger.info(f"Updated requirements saved to {file_path}")
                
                self.state_manager.save_project(project_id, project)
                
                return {
                    "message": f"✅ Requirements have been regenerated with your changes! Check the updated requirements.md file.",
                    "action": "modification_complete",
                    "buttons": [
                        {"label": "Review & Approve", "action": "approve", "variant": "primary"},
                        {"label": "Request More Changes", "action": "modify", "variant": "secondary"}
                    ]
                }
            except Exception as e:
                logger.error(f"Failed to re-run Requirements Agent: {e}", exc_info=True)
                return {
                    "message": f"❌ Failed to regenerate requirements: {str(e)}. Please try again or contact support.",
                    "action": "error",
                    "buttons": []
                }
        
        return {
            "message": f"🔄 I'll regenerate the {current_stage} with your requested changes: {user_message}. This may take a moment...",
            "action": "regenerating",
            "buttons": []
        }
    
    async def _handle_regeneration(self, project_id: str, user_message: str) -> Dict[str, Any]:
        """Handle complete regeneration request"""
        return {
            "message": "🔄 Complete regeneration will restart the entire workflow. Are you sure?",
            "action": "confirm_regeneration",
            "buttons": [
                {"label": "Yes, Regenerate", "action": "confirm_regenerate", "variant": "primary"},
                {"label": "Cancel", "action": "cancel", "variant": "secondary"}
            ]
        }
    
    async def _handle_explanation_with_rag(self, project_id: str, question: str, context: str) -> Dict[str, Any]:
        """Handle explanation request using RAG"""
        logger.info(f"Handling explanation for {project_id}: {question}")
        
        # Try to retrieve relevant context
        relevant_docs = []
        if self.context_store:
            try:
                results = self.context_store.query(project_id, question, n_results=2)
                relevant_docs = results.get("documents", [])
                logger.info(f"Retrieved {len(relevant_docs)} relevant documents")
            except Exception as e:
                logger.error(f"Failed to query context store: {e}")
        
        # Build explanation with context
        rag_context = "\n\n".join([f"Document: {doc[:500]}..." for doc in relevant_docs]) if relevant_docs else "No additional context available."
        
        try:
            explanation_prompt = f"""
Based on the project context, explain the following:

Question: {question}

Retrieved Context:
{rag_context}

Project Info:
{context}

Provide a clear, concise explanation:"""
            
            if self.llm:
                response = await self.llm.ainvoke(explanation_prompt)
                explanation = response.content
            else:
                explanation = f"I'd explain {question}, but LLM is not available."
                
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            explanation = f"I understand you're asking about {question}, but I encountered an error generating the explanation."
        
        return {
            "message": f"💡 {explanation}",
            "action": "explanation",
            "buttons": []
        }
    
    async def _handle_question_with_rag(self, project_id: str, question: str, context: str) -> Dict[str, Any]:
        """Handle general question using RAG"""
        logger.info(f"Handling question for {project_id}: {question}")
        
        # Similar to explanation, but more conversational
        relevant_docs = []
        if self.context_store:
            try:
                results = self.context_store.query(project_id, question, n_results=2)
                relevant_docs = results.get("documents", [])
            except Exception as e:
                logger.error(f"Failed to query context store: {e}")
        
        rag_context = "\n\n".join([f"Context: {doc[:500]}..." for doc in relevant_docs]) if relevant_docs else "No specific project context available yet."
        
        try:
            answer_prompt = f"""
You are helping with an AI-driven project generation workflow.

User Question: {question}

Project Context:
{context}

Relevant Documents:
{rag_context}

Answer the user's question:"""
            
            if self.llm:
                response = await self.llm.ainvoke(answer_prompt)
                answer = response.content
            else:
                answer = "I'd answer your question, but the LLM is not available. Please check the configuration."
                
        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            answer = "I encountered an error while processing your question. Please try again."
        
        return {
            "message": answer,
            "action": "question_answered",
            "buttons": []
        }
    
    def add_to_history(self, project_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add message to conversation history with optional metadata"""
        if project_id not in self.conversation_history:
            self.conversation_history[project_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add metadata if provided
        if metadata:
            message["metadata"] = metadata
        
        self.conversation_history[project_id].append(message)
        
        # Save to persistent store if available
        if self.conversation_store:
            try:
                self.conversation_store.save_message(project_id, role, content)
            except Exception as e:
                logger.error(f"Failed to save message to conversation store: {e}")
    
    def get_history(self, project_id: str) -> List[Dict]:
        """Get conversation history for a project"""
        # Try to load from persistent store first
        if self.conversation_store:
            try:
                return self.conversation_store.load_conversation(project_id)
            except Exception as e:
                logger.error(f"Failed to load conversation from store: {e}")
        
        return self.conversation_history.get(project_id, [])

    def get_greeting_message(self, project_id: str) -> Dict[str, Any]:
        """Get the initial greeting message for a project"""
        return {
            "message": "Welcome to AI-SOL! I'm your AI Architect. I'm analyzing your requirements and will guide you through the development process. The Requirements Agent is currently working on your specification.",
            "action": "greeting",
            "buttons": []
        }
