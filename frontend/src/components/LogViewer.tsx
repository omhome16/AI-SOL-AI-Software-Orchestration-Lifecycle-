import React, { useEffect, useRef } from 'react';

interface LogMessage {
    type: 'LOG';
    level: 'info' | 'success' | 'warning' | 'error';
    message: string;
    agent: string;
    timestamp: string;
}

interface LogViewerProps {
    logs: LogMessage[];
}

const LogViewer: React.FC<LogViewerProps> = ({ logs }) => {
    const logEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const getLevelColor = (level: string): string => {
        switch (level) {
            case 'error':
                return 'text-red-400';
            case 'warning':
                return 'text-yellow-400';
            case 'success':
                return 'text-green-400';
            default:
                return 'text-gray-300';
        }
    };

    const getLevelIcon = (level: string): string => {
        switch (level) {
            case 'error':
                return '❌';
            case 'warning':
                return '⚠️';
            case 'success':
                return '✅';
            default:
                return 'ℹ️';
        }
    };

    const formatTimestamp = (timestamp: string): string => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return timestamp;
        }
    };

    return (
        <div className="log-viewer h-full overflow-y-auto bg-gray-950 p-4 font-mono text-sm">
            {logs.length === 0 ? (
                <div className="text-gray-500 text-center py-8">
                    No logs yet. Waiting for workflow to start...
                </div>
            ) : (
                <div className="space-y-1">
                    {logs.map((log, index) => (
                        <div
                            key={index}
                            className={`flex items-start gap-2 ${getLevelColor(log.level)} hover:bg-gray-900 px-2 py-1 rounded`}
                        >
                            <span className="flex-shrink-0 text-xs">{getLevelIcon(log.level)}</span>
                            <span className="flex-shrink-0 text-gray-500 text-xs">
                                {formatTimestamp(log.timestamp)}
                            </span>
                            <span className="flex-shrink-0 text-cyan-400 text-xs font-semibold">
                                [{log.agent}]
                            </span>
                            <span className="flex-1 break-words">
                                {log.message}
                            </span>
                        </div>
                    ))}
                    <div ref={logEndRef} />
                </div>
            )}
        </div>
    );
};

export default LogViewer;
