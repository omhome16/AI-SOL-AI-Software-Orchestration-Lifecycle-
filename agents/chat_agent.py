"""
ChatAgent - Handles all orchestrator-to-user communication
Sends progress updates, announcements, and handles user commands
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ChatAgent(BaseAgent):
    """
    Dedicated agent for orchestrator communication.
    Handles greetings, announcements, approvals, and modifications.
    """
    
    def __init__(self, project_id: str, websocket_manager=None):
        super().__init__(name="chat", project_id=project_id)
        self.websocket_manager = websocket_manager
        self.sent_messages = set()  # Track sent messages to prevent duplicates
    
    def _message_hash(self, content: str) -> str:
        """Create hash of message content to detect duplicates"""
        return f"{content[:100]}_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    async def send_message(self, content: str, role: str = "ai", metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Send a message to the user via WebSocket (prevents duplicates)"""
        
        msg_hash = self._message_hash(content)
        
        # Prevent duplicate messages within 1 minute
        if msg_hash in self.sent_messages:
            logger.info(f"[CHAT] Skipping duplicate message: {content[:50]}...")
            return {"skipped": True, "reason": "duplicate"}
        
        self.sent_messages.add(msg_hash)
        
        # Clean up old hashes (keep only last 50)
        if len(self.sent_messages) > 50:
            self.sent_messages = set(list(self.sent_messages)[-50:])
        
        message = {
            "type": "CHAT_MESSAGE",
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        if self.websocket_manager:
            await self.websocket_manager.broadcast(self.project_id, message)
        
        logger.info(f"[CHAT] Sent message: {content[:100]}...")
        return {"sent": True, "message": message}
    
    async def send_greeting(self) -> Dict[str, Any]:
        """Send welcome greeting to user"""
        greeting = (
            "Welcome to AI-SOL! 🚀 I'm your AI Architect. "
            "I'm analyzing your requirements and will guide you through the development process. "
            "The Requirements Agent is currently working on your specification."
        )
        return await self.send_message(greeting, role="ai", metadata={"type": "greeting"})
    
    async def announce_agent_start(self, agent_name: str, description: str = "") -> Dict[str, Any]:
        """Announce that an agent is starting work"""
        desc_text = f" - {description}" if description else ""
        content = f"🔧 Starting {agent_name} Agent{desc_text}..."
        return await self.send_message(content, role="ai", metadata={"type": "agent_start", "agent": agent_name})
    
    async def announce_agent_complete(self, agent_name: str, summary: str = "") -> Dict[str, Any]:
        """Announce that an agent has completed its work"""
        summary_text = f"\n\n{summary}" if summary else ""
        content = f"✅ {agent_name} Agent complete!{summary_text}\n\nPlease review the generated files."
        return await self.send_message(content, role="ai", metadata={"type": "agent_complete", "agent": agent_name})
    
    async def announce_transition(self, from_agent: str, to_agent: str) -> Dict[str, Any]:
        """Announce transition between agents"""
        content = f"🔄 {from_agent} approved! Now starting {to_agent} Agent..."
        return await self.send_message(
            content,
            role="ai",
            metadata={"type": "transition", "from": from_agent, "to": to_agent}
        )
    
    async def handle_approval(self, stage: str) -> Dict[str, Any]:
        """Handle user approval command"""
        content = f"✅ Approved! Proceeding to the next stage..."
        return await self.send_message(
            content,
            role="ai",
            metadata={"type": "approval_confirmed", "stage": stage}
        )
    
    async def handle_modification_request(self, modifications: str) -> Dict[str, Any]:
        """Handle user modification request"""
        content = f"🔄 I'll regenerate with your requested changes: {modifications}\n\nThis may take a moment..."
        return await self.send_message(
            content,
            role="ai",
            metadata={"type": "modification_request", "modifications": modifications}
        )
    
    async def send_error(self, error_message: str, agent: Optional[str] = None) -> Dict[str, Any]:
        """Send error message to user"""
        agent_text = f" in {agent} Agent" if agent else ""
        content = f"❌ Error{agent_text}: {error_message}\n\nPlease check the logs or try again."
        return await self.send_message(
            content,
            role="ai",
            metadata={"type": "error", "agent": agent, "error": error_message}
        )
    
    async def send_progress_update(self, stage: str, progress: int, status: str) -> Dict[str, Any]:
        """Send progress update"""
        content = f"⏳ {stage}: {progress}% - {status}"
        return await self.send_message(
            content,
            role="ai",
            metadata={"type": "progress", "stage": stage, "progress": progress, "status": status}
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute method for compatibility with BaseAgent"""
        action = kwargs.get("action", "greeting")
        
        if action == "greeting":
            return await self.send_greeting()
        elif action == "announce_start":
            return await self.announce_agent_start(kwargs.get("agent_name", "Unknown"))
        elif action == "announce_complete":
            return await self.announce_agent_complete(kwargs.get("agent_name", "Unknown"))
        elif action == "approve":
            return await self.handle_approval(kwargs.get("stage", "current"))
        elif action == "modify":
            return await self.handle_modification_request(kwargs.get("modifications", ""))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
