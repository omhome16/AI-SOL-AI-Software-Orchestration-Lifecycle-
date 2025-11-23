// WebSocket Message Types
export type LogMessage = {
    type: 'LOG';
    level: 'info' | 'success' | 'warning' | 'error';
    message: string;
    agent: string;
    timestamp: string;
};

export type FileGeneratedMessage = {
    type: 'FILE_GENERATED';
    doc_type: string;
    filename: string;
    path: string;
    content: string;  // Preview
    full_content: string;  // Full file content
    auto_focus: boolean;
    timestamp: string;
};

export type ChatMessageType = {
    type: 'CHAT_MESSAGE';
    role: 'user' | 'ai';
    content: string;
    timestamp: string;
};

export type ActionButton = {
    label: string;
    action: string;
    variant: 'primary' | 'secondary';
};

export type ChatResponseMessage = {
    type: 'CHAT_RESPONSE';
    message: string;
    action?: string;
    buttons?: ActionButton[];
    timestamp: string;
};

export type AwaitingReviewMessage = {
    type: 'AWAITING_REVIEW';
    stage: string;
    prompt: string;
    files: string[];
    timestamp: string;
};

export type StatusUpdateMessage = {
    type: 'STATUS_UPDATE';
    status: string;
    timestamp: string;
};

export type ConnectionStatusMessage = {
    type: 'CONNECTION_STATUS';
    connected: boolean;
    timestamp: string;
};

export type WorkflowEventMessage = {
    type: 'workflow_event';
    event: {
        event_type: string;
        timestamp: string;
        project_id: string;
        stage?: string;
        agent?: string;
        message: string;
        data?: Record<string, any>;
        severity?: 'debug' | 'info' | 'success' | 'warning' | 'error' | 'critical';
        progress_percentage?: number;
    };
};

export type WebSocketMessage =
    | LogMessage
    | FileGeneratedMessage
    | ChatMessageType
    | ChatResponseMessage
    | AwaitingReviewMessage
    | StatusUpdateMessage
    | ConnectionStatusMessage
    | WorkflowEventMessage;

export type WebSocketCallback = (message: WebSocketMessage) => void;

class WebSocketService {
    private ws: WebSocket | null = null;
    private callbacks: WebSocketCallback[] = [];
    private reconnectInterval: number = 3000;
    private maxReconnectAttempts: number = 10;
    private reconnectAttempts: number = 0;
    private projectId: string | null = null;

    connect(projectId: string) {
        this.projectId = projectId;
        this.reconnectAttempts = 0;
        this._connect();
    }

    private _connect() {
        if (!this.projectId) return;

        const wsBaseUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8005/ws';
        const wsUrl = `${wsBaseUrl}/${this.projectId}`;
        console.log(`Connecting to WebSocket: ${wsUrl}`);

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket Connected');
            this.reconnectAttempts = 0;
            this._notifyConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Handle workflow events specially
                if (data.type === 'workflow_event' && data.event) {
                    // Import and use event handler
                    import('./event_handler').then(({ eventHandler }) => {
                        eventHandler.handleEvent(data.event);
                    });
                }

                // Also notify regular WebSocket callbacks
                const message: WebSocketMessage = data;
                this.callbacks.forEach(callback => callback(message));
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
                // Fallback: if it's a plain string, treat as a log
                const fallbackMessage: LogMessage = {
                    type: 'LOG',
                    level: 'info',
                    message: event.data,
                    agent: 'SYSTEM',
                    timestamp: new Date().toISOString()
                };
                this.callbacks.forEach(callback => callback(fallbackMessage));
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket Disconnected');
            this.ws = null;
            this._notifyConnectionStatus(false);
            this._reconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket Error:', error);
            this.ws?.close();
        };
    }

    private _reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => this._connect(), this.reconnectInterval);
        } else {
            console.error('Max reconnect attempts reached. WebSocket connection failed.');
        }
    }

    private _notifyConnectionStatus(connected: boolean) {
        const message: ConnectionStatusMessage = {
            type: 'CONNECTION_STATUS',
            connected,
            timestamp: new Date().toISOString()
        };
        this.callbacks.forEach(callback => callback(message));
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.projectId = null;
    }

    subscribe(callback: WebSocketCallback) {
        this.callbacks.push(callback);
        return () => {
            this.callbacks = this.callbacks.filter(cb => cb !== callback);
        };
    }

    sendMessage(message: any) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket is not open. Cannot send message.');
        }
    }
}

export const webSocketService = new WebSocketService();
