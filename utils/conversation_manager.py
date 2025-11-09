from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

class Message(BaseModel):
    sender: str
    message: str
    timestamp: str
    intent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Conversation(BaseModel):
    session_id: str
    project_id: str
    messages: List[Message] = Field(default_factory=list)
    created_at: str
    updated_at: str

class ConversationManager:
    def __init__(self, base_dir: str = "./workspace/.conversations"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tz = ZoneInfo("Asia/Kolkata")

    def _get_conversation_path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"

    def create_conversation(self, session_id: str, project_id: str, initial_message: str) -> Conversation:
        now = datetime.now(self.tz).isoformat()
        conversation = Conversation(
            session_id=session_id,
            project_id=project_id,
            messages=[Message(sender="system", message=initial_message, timestamp=now)],
            created_at=now,
            updated_at=now
        )
        self.save_conversation(conversation)
        return conversation

    def save_conversation(self, conversation: Conversation):
        conversation.updated_at = datetime.now(self.tz).isoformat()
        with open(self._get_conversation_path(conversation.session_id), "w") as f:
            json.dump(conversation.dict(), f, indent=2)

    def load_conversation(self, session_id: str) -> Optional[Conversation]:
        conversation_path = self._get_conversation_path(session_id)
        if conversation_path.exists():
            with open(conversation_path, "r") as f:
                data = json.load(f)
                return Conversation(**data)
        return None

    def add_message(self, session_id: str, sender: str, message: str, metadata: Dict[str, Any] = None, intent: Optional[str] = None):
        conversation = self.load_conversation(session_id)
        if conversation:
            conversation.messages.append(Message(
                sender=sender,
                message=message,
                timestamp=datetime.now(self.tz).isoformat(),
                intent=intent,
                metadata=metadata or {}
            ))
            self.save_conversation(conversation)
        else:
            # If conversation doesn't exist, create a new one (e.g., for ad-hoc chats)
            self.create_conversation(session_id, "ad-hoc", f"New conversation started with message from {sender}: {message}")

    def get_message_history(self, session_id: str, limit: int = 10) -> List[Message]:
        conversation = self.load_conversation(session_id)
        if conversation:
            return conversation.messages[-limit:]
        return []

    def classify_intent(self, message: str) -> str:
        # Placeholder for LLM-based intent classification
        # In a real system, this would involve an LLM call
        if "create project" in message.lower() or "new project" in message.lower():
            return "create_project"
        elif "modify" in message.lower() or "change" in message.lower():
            return "modify_project"
        elif "status" in message.lower() or "progress" in message.lower():
            return "get_status"
        elif "list" in message.lower() or "show projects" in message.lower():
            return "list_projects"
        elif "push to github" in message.lower() or "github" in message.lower():
            return "github_push"
        else:
            return "unknown"