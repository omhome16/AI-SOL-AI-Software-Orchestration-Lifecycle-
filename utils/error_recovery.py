from typing import Dict, Any, List
from datetime import datetime

class ErrorRecoveryManager:
    def __init__(self):
        self.error_log = []

    def log_error(self, agent_name: str, error_message: str, context: Dict[str, Any] = None):
        self.error_log.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "error_message": error_message,
            "context": context or {}
        })

    def get_recent_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.error_log[-limit:]

    def suggest_recovery_strategy(self, error: Dict[str, Any]) -> str:
        # Placeholder for LLM-based recovery strategy
        if "API key" in error["error_message"]:
            return "Check API key configuration in .env file."
        elif "network" in error["error_message"]:
            return "Verify internet connection and proxy settings."
        elif "file not found" in error["error_message"]:
            return "Ensure all necessary files are present in the workspace."
        else:
            return "Review agent logs for more details and consider retrying the step."
