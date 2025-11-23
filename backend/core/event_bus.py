"""
Event Bus - Central event emission system for real-time workflow updates
Broadcasts events via WebSocket to frontend for transparent progress tracking
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types for workflow tracking"""
    # Stage events
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    
    # Agent events
    AGENT_THINKING = "agent_thinking"
    AGENT_RESPONSE = "agent_response"
    AGENT_ERROR = "agent_error"
    
    # File events
    FILE_GENERATED = "file_generated"
    FILE_UPDATED = "file_updated"
    FILE_VALIDATED = "file_validated"
    
    # User interaction events
    HUMAN_INPUT_REQUIRED = "human_input_required"
    USER_MESSAGE = "user_message"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    
    # System events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_COMPLETED = "workflow_completed"
    
    # Error events
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    RETRY_ATTEMPT = "retry_attempt"


class EventSeverity(str, Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class WorkflowEvent(BaseModel):
    """Standard event structure for all workflow events"""
    event_type: EventType
    timestamp: str
    project_id: str
    stage: Optional[str] = None  # requirements, architecture, implementation, etc.
    agent: Optional[str] = None  # requirements_analyst, architect, developer, etc.
    message: str  # User-friendly description
    data: Dict[str, Any] = {}  # Event-specific payload
    severity: EventSeverity = EventSeverity.INFO
    progress_percentage: Optional[int] = None  # 0-100
    
    class Config:
        use_enum_values = True


class EventBus:
    """
    Central event bus for emitting and broadcasting workflow events.
    Supports multiple listeners (WebSocket, logging, persistence, etc.)
    """
    
    def __init__(self):
        self.listeners: List[Callable] = []
        self.event_history: Dict[str, List[WorkflowEvent]] = {}  # project_id -> events
        logger.info("EventBus initialized")
    
    def add_listener(self, listener: Callable):
        """Add a listener function that will be called for every event"""
        self.listeners.append(listener)
        logger.info(f"Added event listener: {listener.__name__}")
    
    def remove_listener(self, listener: Callable):
        """Remove a listener"""
        if listener in self.listeners:
            self.listeners.remove(listener)
            logger.info(f"Removed event listener: {listener.__name__}")
    
    async def emit(self, event: WorkflowEvent):
        """
        Emit an event to all listeners and store in history
        """
        try:
            # Add to history
            if event.project_id not in self.event_history:
                self.event_history[event.project_id] = []
            self.event_history[event.project_id].append(event)
            
            # Log event
            log_level = self._get_log_level(event.severity)
            logger.log(
                log_level,
                f"[{event.project_id}] {event.event_type}: {event.message}"
            )
            
            # Broadcast to all listeners
            for listener in self.listeners:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        await listener(event)
                    else:
                        listener(event)
                except Exception as e:
                    logger.error(f"Listener {listener.__name__} failed: {e}")
        
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
    
    def emit_sync(self, event: WorkflowEvent):
        """Synchronous version of emit for non-async contexts"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create task if loop is already running
                asyncio.create_task(self.emit(event))
            else:
                # Run until complete if no loop is running
                loop.run_until_complete(self.emit(event))
        except Exception as e:
            logger.error(f"Failed to emit event synchronously: {e}")
    
    def get_history(self, project_id: str, limit: Optional[int] = None) -> List[WorkflowEvent]:
        """Get event history for a project"""
        events = self.event_history.get(project_id, [])
        if limit:
            return events[-limit:]
        return events
    
    def clear_history(self, project_id: str):
        """Clear event history for a project"""
        if project_id in self.event_history:
            del self.event_history[project_id]
            logger.info(f"Cleared event history for project {project_id}")
    
    @staticmethod
    def _get_log_level(severity: EventSeverity) -> int:
        """Map severity to logging level"""
        mapping = {
            EventSeverity.DEBUG: logging.DEBUG,
            EventSeverity.INFO: logging.INFO,
            EventSeverity.SUCCESS: logging.INFO,
            EventSeverity.WARNING: logging.WARNING,
            EventSeverity.ERROR: logging.ERROR,
            EventSeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.INFO)


# Global event bus instance
_event_bus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance (Singleton)"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Convenience functions for quick event emission
async def emit_stage_started(project_id: str, stage: str, agent: str, message: str = None):
    """Quick helper to emit stage started event"""
    event = WorkflowEvent(
        event_type=EventType.STAGE_STARTED,
        timestamp=datetime.now().isoformat(),
        project_id=project_id,
        stage=stage,
        agent=agent,
        message=message or f"Starting {stage} stage with {agent}",
        severity=EventSeverity.INFO
    )
    await get_event_bus().emit(event)


async def emit_stage_completed(project_id: str, stage: str, agent: str, message: str = None, data: Dict = None):
    """Quick helper to emit stage completed event"""
    event = WorkflowEvent(
        event_type=EventType.STAGE_COMPLETED,
        timestamp=datetime.now().isoformat(),
        project_id=project_id,
        stage=stage,
        agent=agent,
        message=message or f"Completed {stage} stage",
        data=data or {},
        severity=EventSeverity.SUCCESS
    )
    await get_event_bus().emit(event)


async def emit_error(project_id: str, stage: str, error: str, agent: str = None):
    """Quick helper to emit error event"""
    event = WorkflowEvent(
        event_type=EventType.ERROR_OCCURRED,
        timestamp=datetime.now().isoformat(),
        project_id=project_id,
        stage=stage,
        agent=agent,
        message=f"Error in {stage}: {error}",
        data={"error": error},
        severity=EventSeverity.ERROR
    )
    await get_event_bus().emit(event)


# Import asyncio at the end to avoid circular imports
import asyncio
