"""
ConversationStore - Persist chat conversations to disk
Enables conversation history across sessions.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationStore:
    """
    Manages conversation persistence for projects.
    Stores chat history as JSON files.
    """
    
    def __init__(self, base_directory: str = "./workspace"):
        """
        Initialize conversation store.
        
        Args:
            base_directory: Base directory for storing conversations
        """
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
    
    def _get_conversation_path(self, project_id: str) -> Path:
        """Get the path to a project's conversation file"""
        project_dir = self.base_directory / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir / "conversation.json"
    
    def save_message(self, project_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Save a single message to the conversation.
        
        Args:
            project_id: Project identifier
            role: 'user' or 'ai'
            content: Message content
            metadata: Optional metadata (buttons, action, etc.)
            
        Returns:
            True if successful
        """
        try:
            # Load existing conversation
            conversation = self.load_conversation(project_id)
            
            # Add new message
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
            conversation.append(message)
            
            # Save back to file
            path = self._get_conversation_path(project_id)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved message for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save message for {project_id}: {e}")
            return False
    
    def load_conversation(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Load conversation history for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of message dicts
        """
        try:
            path = self._get_conversation_path(project_id)
            
            if not path.exists():
                return []
            
            with open(path, 'r', encoding='utf-8') as f:
                conversation = json.load(f)
            
            logger.info(f"Loaded {len(conversation)} messages for project {project_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to load conversation for {project_id}: {e}")
            return []
    
    def clear_conversation(self, project_id: str) -> bool:
        """
        Clear conversation history for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if successful
        """
        try:
            path = self._get_conversation_path(project_id)
            
            if path.exists():
                path.unlink()
                logger.info(f"Cleared conversation for project {project_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear conversation for {project_id}: {e}")
            return False
    
    def get_stats(self, project_id: str) -> Dict[str, Any]:
        """
        Get statistics about a conversation.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with message counts and timestamps
        """
        try:
            conversation = self.load_conversation(project_id)
            
            user_messages = sum(1 for msg in conversation if msg.get('role') == 'user')
            ai_messages = sum(1 for msg in conversation if msg.get('role') == 'ai')
            
            timestamps = [msg.get('timestamp') for msg in conversation if 'timestamp' in msg]
            
            return {
                "total_messages": len(conversation),
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "first_message": timestamps[0] if timestamps else None,
                "last_message": timestamps[-1] if timestamps else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {project_id}: {e}")
            return {
                "total_messages": 0,
                "user_messages": 0,
                "ai_messages": 0,
                "error": str(e)
            }
