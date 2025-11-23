/**
 * Frontend Event Handler - Receives and processes workflow events from backend
 */

export interface WorkflowEvent {
    event_type: string;
    timestamp: string;
    project_id: string;
    stage?: string;
    agent?: string;
    message: string;
    data?: Record<string, any>;
    severity?: 'debug' | 'info' | 'success' | 'warning' | 'error' | 'critical';
    progress_percentage?: number;
}

export type EventCallback = (event: WorkflowEvent) => void;

class EventHandler {
    private listeners: Map<string, EventCallback[]> = new Map();
    private eventHistory: WorkflowEvent[] = [];

    /**
     * Register a callback for specific event type
     */
    on(eventType: string, callback: EventCallback): void {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, []);
        }
        this.listeners.get(eventType)!.push(callback);
    }

    /**
     * Register a callback for all events
     */
    onAny(callback: EventCallback): void {
        this.on('*', callback);
    }

    /**
     * Remove a specific callback
     */
    off(eventType: string, callback: EventCallback): void {
        const callbacks = this.listeners.get(eventType);
        if (callbacks) {
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Handle incoming event from WebSocket
     */
    handleEvent(event: WorkflowEvent): void {
        // Add to history
        this.eventHistory.push(event);

        // Log event
        this._logEvent(event);

        // Notify specific listeners
        const specificListeners = this.listeners.get(event.event_type) || [];
        specificListeners.forEach(callback => {
            try {
                callback(event);
            } catch (error) {
                console.error(`Event handler error for ${event.event_type}:`, error);
            }
        });

        // Notify wildcard listeners
        const wildcardListeners = this.listeners.get('*') || [];
        wildcardListeners.forEach(callback => {
            try {
                callback(event);
            } catch (error) {
                console.error('Wildcard event handler error:', error);
            }
        });
    }

    /**
     * Get event history, optionally filtered by type
     */
    getHistory(eventType?: string, limit?: number): WorkflowEvent[] {
        let filtered = eventType
            ? this.eventHistory.filter(e => e.event_type === eventType)
            : this.eventHistory;

        return limit ? filtered.slice(-limit) : filtered;
    }

    /**
     * Clear event history
     */
    clearHistory(): void {
        this.eventHistory = [];
    }

    /**
     * Get current stage based on latest events
     */
    getCurrentStage(): string | null {
        const stageEvents = this.eventHistory
            .filter(e => e.stage)
            .reverse();

        return stageEvents.length > 0 ? stageEvents[0].stage! : null;
    }

    /**
     * Log event to console with appropriate styling
     */
    private _logEvent(event: WorkflowEvent): void {
        const emoji = this._getEmojiForEventType(event.event_type);
        const style = this._getStyleForSeverity(event.severity || 'info');

        console.log(
            `%c${emoji} [${event.event_type}] ${event.message}`,
            style,
            event
        );
    }

    private _getEmojiForEventType(eventType: string): string {
        const emojiMap: Record<string, string> = {
            'workflow_started': '🚀',
            'workflow_completed': '✅',
            'workflow_paused': '⏸️',
            'workflow_resumed': '▶️',
            'stage_started': '📍',
            'stage_completed': '✓',
            'stage_failed': '❌',
            'agent_thinking': '🤔',
            'agent_response': '💬',
            'file_generated': '📄',
            'error_occurred': '⚠️',
            'retry_attempt': '🔄',
            'human_input_required': '👤'
        };

        return emojiMap[eventType] || '📡';
    }

    private _getStyleForSeverity(severity: string): string {
        const styleMap: Record<string, string> = {
            'debug': 'color: #999',
            'info': 'color: #2196F3; font-weight: bold',
            'success': 'color: #4CAF50; font-weight: bold',
            'warning': 'color: #FF9800; font-weight: bold',
            'error': 'color: #F44336; font-weight: bold',
            'critical': 'color: #F44336; font-weight: bold; font-size: 14px'
        };

        return styleMap[severity] || styleMap['info'];
    }
}

// Global event handler instance
export const eventHandler = new EventHandler();

// Setup default event handlers
eventHandler.on('workflow_started', (event) => {
    console.info('🎯 Workflow Started:', event.message);
});

eventHandler.on('workflow_completed', (event) => {
    console.info('🎉 Workflow Completed:', event.message);
});

eventHandler.on('error_occurred', (event) => {
    console.error('⚠️ Error:', event.message, event.data);
});

eventHandler.on('human_input_required', (event) => {
    console.warn('👤 Human Input Required:', event.message);
    // Could trigger a UI notification here
});

export default eventHandler;
