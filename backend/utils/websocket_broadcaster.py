"""
WebSocket Event Broadcaster - Listens to event bus and broadcasts to connected clients
"""

import logging
from typing import Dict, Any
from backend.core.event_bus import WorkflowEvent, get_event_bus

logger = logging.getLogger(__name__)


class WebSocketEventBroadcaster:
    """
    Listens to the event bus and broadcasts events to WebSocket clients
    """
    
    def __init__(self, connection_manager):
        """
        Initialize broadcaster with connection manager
        
        Args:
            connection_manager: WebSocket connection manager instance
        """
        self.connection_manager = connection_manager
        self.event_bus = get_event_bus()
        
        # Register this broadcaster as a listener
        self.event_bus.add_listener(self.broadcast_event)
        logger.info("WebSocketEventBroadcaster initialized and registered")
    
    async def broadcast_event(self, event: WorkflowEvent):
        """
        Broadcast an event to all connected WebSocket clients for the project
        
        Args:
            event: WorkflowEvent to broadcast
        """
        try:
            # Convert event to dict for JSON serialization
            event_dict = event.dict()
            
            # Add event type to match frontend expectations
            message = {
                "type": "workflow_event",
                "event": event_dict
            }
            
            # Broadcast to all clients connected to this project
            await self.connection_manager.broadcast_json(message, event.project_id)
            
            logger.debug(f"Broadcasted event {event.event_type} for project {event.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast event via WebSocket: {e}")
    
    def unregister(self):
        """Unregister this broadcaster from the event bus"""
        self.event_bus.remove_listener(self.broadcast_event)
        logger.info("WebSocketEventBroadcaster unregistered")


def setup_websocket_broadcaster(connection_manager) -> WebSocketEventBroadcaster:
    """
    Setup and return a WebSocket event broadcaster
    
    Args:
        connection_manager: WebSocket connection manager instance
    
    Returns:
        WebSocketEventBroadcaster instance
    """
    broadcaster = WebSocketEventBroadcaster(connection_manager)
    logger.info("WebSocket event broadcasting enabled")
    return broadcaster
