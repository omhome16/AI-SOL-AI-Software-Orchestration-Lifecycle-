from typing import Dict, Any, List

class CommunicationManager:
    def __init__(self):
        self.messages = []

    def add_message(self, sender: str, message: str, metadata: Dict[str, Any] = None):
        self.messages.append({
            "sender": sender,
            "message": message,
            "metadata": metadata or {}
        })

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages

    def clear_messages(self):
        self.messages = []