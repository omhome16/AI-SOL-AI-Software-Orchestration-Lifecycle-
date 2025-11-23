import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Activity, FileText, X, Maximize2 } from 'lucide-react';
import { projectService } from '../services/api';
import { webSocketService, type FileGeneratedMessage, type WebSocketMessage } from '../services/websocket';
import FileViewer from '../components/FileViewer';
import ChatInterface from '../components/ChatInterface';
import ConnectionStatus from '../components/ConnectionStatus';
import ProgressTimeline from '../components/ProgressTimeline';

interface ProjectStatus {
    status: string;
    current_step: string;
    steps_completed: string[];
    generated_files: any[];
}

interface ChatMessage {
    role: 'user' | 'ai';
    content: string;
    timestamp: string;
}

const Dashboard = () => {
    const { projectId } = useParams();

    // Load initial status from localStorage if available to prevent blank screen
    const [status, setStatus] = useState<ProjectStatus | null>(() => {
        if (projectId) {
            const saved = localStorage.getItem(`status_${projectId}`);
            return saved ? JSON.parse(saved) : null;
        }
        return null;
    });

    const [files, setFiles] = useState<FileGeneratedMessage[]>([]);
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => {
        // Load chat history from localStorage on mount
        if (projectId) {
            const saved = localStorage.getItem(`chat_${projectId}`);
            return saved ? JSON.parse(saved) : [];
        }
        return [];
    });
    const [selectedFile, setSelectedFile] = useState<FileGeneratedMessage | null>(null);
    const [isChatLoading, setIsChatLoading] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [awaitingReview, setAwaitingReview] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    // Panel widths (percentage)
    const [leftWidth, setLeftWidth] = useState(20);
    const [rightWidth, setRightWidth] = useState(30);
    const [isDraggingLeft, setIsDraggingLeft] = useState(false);
    const [isDraggingRight, setIsDraggingRight] = useState(false);

    // Persist chat messages
    useEffect(() => {
        if (projectId && chatMessages.length > 0) {
            localStorage.setItem(`chat_${projectId}`, JSON.stringify(chatMessages));
        }
    }, [chatMessages, projectId]);

    // Persist status
    useEffect(() => {
        if (projectId && status) {
            localStorage.setItem(`status_${projectId}`, JSON.stringify(status));
        }
    }, [status, projectId]);

    // Resizing Handlers
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (isDraggingLeft) {
                const newWidth = (e.clientX / window.innerWidth) * 100;
                if (newWidth > 10 && newWidth < 40) setLeftWidth(newWidth);
            }
            if (isDraggingRight) {
                const newWidth = ((window.innerWidth - e.clientX) / window.innerWidth) * 100;
                if (newWidth > 15 && newWidth < 50) setRightWidth(newWidth);
            }
        };

        const handleMouseUp = () => {
            setIsDraggingLeft(false);
            setIsDraggingRight(false);
            document.body.style.cursor = 'default';
        };

        if (isDraggingLeft || isDraggingRight) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
        }

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDraggingLeft, isDraggingRight]);

    const fetchStatus = async () => {
        if (!projectId) return;
        try {
            const data = await projectService.getProjectStatus(projectId);
            setStatus(data);
            setRetryCount(0); // Reset retry count on success

            // Restore files from backend state if available (fixes empty files on reload)
            if (data.generated_files && data.generated_files.length > 0) {
                setFiles(prev => {
                    // Merge unique files
                    const newFiles = [...prev];
                    data.generated_files.forEach((serverFile: any) => {
                        if (!newFiles.find(f => f.path === serverFile.path)) {
                            newFiles.push(serverFile);
                        }
                    });
                    return newFiles;
                });
            }
        } catch (error) {
            console.error('Failed to fetch status:', error);
            // Exponential backoff for retries
            const timeout = Math.min(1000 * Math.pow(2, retryCount), 10000);
            setTimeout(() => setRetryCount(c => c + 1), timeout);
        }
    };

    const handleSendMessage = async (message: string) => {
        if (!projectId) return;

        setIsChatLoading(true);

        try {
            // Optimistically add user message
            const newMessage: ChatMessage = {
                role: 'user',
                content: message,
                timestamp: new Date().toISOString()
            };

            setChatMessages(prev => {
                // Prevent duplicates
                if (prev.some(m => m.content === message && m.role === 'user' &&
                    new Date(m.timestamp).getTime() > Date.now() - 5000)) {
                    return prev;
                }
                return [...prev, newMessage];
            });

            await projectService.chatWithOrchestrator(projectId, message);

        } catch (error) {
            console.error('Failed to send message:', error);
            setChatMessages(prev => [...prev, {
                role: 'ai',
                content: 'Sorry, I encountered an error processing your message. Please check your connection.',
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setIsChatLoading(false);
        }
    };

    const handleApprove = async () => {
        console.log("✅ Approve button clicked");
        setAwaitingReview(false);
        await handleSendMessage('approve');
    };

    // Handle Escape key for fullscreen
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isFullscreen) {
                setIsFullscreen(false);
            }
        };
        window.addEventListener('keydown', handleEscape);
        return () => window.removeEventListener('keydown', handleEscape);
    }, [isFullscreen]);

    useEffect(() => {
        if (!projectId) return;

        fetchStatus();
        const statusInterval = setInterval(fetchStatus, 3000);

        webSocketService.connect(projectId);

        // Add initial greeting if chat is empty
        if (chatMessages.length === 0) {
            setChatMessages([{
                role: 'ai',
                content: "Welcome to AI-SOL! I'm your AI Architect. I'm analyzing your requirements and will guide you through the development process. The Requirements Agent is currently working on your specification.",
                timestamp: new Date().toISOString()
            }]);
        }

        const unsubscribe = webSocketService.subscribe((message: WebSocketMessage) => {
            console.log("WebSocket message received:", message.type);

            if (message.type === 'FILE_GENERATED') {
                console.log("📄 File generated:", message.filename);
                setFiles(prev => {
                    const existingIndex = prev.findIndex(f => f.filename === message.filename);
                    if (existingIndex >= 0) {
                        const updated = [...prev];
                        updated[existingIndex] = message;
                        return updated;
                    }
                    return [...prev, message];
                });

                if (message.auto_focus) {
                    setSelectedFile(message);
                }
            } else if (message.type === 'CONNECTION_STATUS') {
                setIsConnected(message.connected);
            } else if (message.type === 'CHAT_MESSAGE') {
                // Only add if not already present (deduplication)
                setChatMessages(prev => {
                    const isDuplicate = prev.some(m =>
                        m.role === message.role &&
                        m.content === message.content &&
                        Math.abs(new Date(m.timestamp).getTime() - new Date(message.timestamp).getTime()) < 2000
                    );

                    if (isDuplicate) return prev;

                    return [...prev, {
                        role: message.role,
                        content: message.content,
                        timestamp: message.timestamp
                    }];
                });
            } else if (message.type === 'CHAT_RESPONSE') {
                setIsChatLoading(false);
                setChatMessages(prev => {
                    const isDuplicate = prev.some(m =>
                        m.role === 'ai' &&
                        m.content === message.message &&
                        Math.abs(new Date(m.timestamp).getTime() - new Date(message.timestamp).getTime()) < 2000
                    );

                    if (isDuplicate) return prev;

                    return [...prev, {
                        role: 'ai',
                        content: message.message,
                        timestamp: message.timestamp
                    }];
                });
            } else if (message.type === 'AWAITING_REVIEW') {
                console.log("⏸️  AWAITING_REVIEW event received");
                setAwaitingReview(true);

                // Auto-select first file if not already selected
                if (files.length > 0 && !selectedFile) {
                    setSelectedFile(files[files.length - 1]);
                }
            }
        });

        return () => {
            clearInterval(statusInterval);
            unsubscribe();
            webSocketService.disconnect();
        };
    }, [projectId]);

    // Auto-select newly generated file
    useEffect(() => {
        if (files.length > 0 && !selectedFile) {
            setSelectedFile(files[files.length - 1]);
        }
    }, [files]);

    return (
        <div className="min-h-screen bg-black text-white font-sans selection:bg-cyan-500/30">
            {/* Background Ambient Glow */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden">
                <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/20 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-cyan-900/20 rounded-full blur-[120px]" />
            </div>

            {/* Header */}
            <header className="sticky top-0 z-50 border-b border-white/5 bg-black/50 backdrop-blur-xl">
                <div className="container mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                            <Activity className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-lg font-bold tracking-tight text-white">
                                AI Architect <span className="text-gray-500 font-normal">Workspace</span>
                            </h1>
                            <div className="flex items-center gap-2 text-xs text-gray-400">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                                ID: <span className="font-mono text-gray-300">{projectId?.slice(0, 8)}...</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <ConnectionStatus isConnected={isConnected} />
                        <div className={`px-3 py-1.5 rounded-full text-xs font-bold tracking-wider uppercase flex items-center gap-2 border ${status?.status === 'running' ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400' :
                            status?.status === 'completed' ? 'bg-green-500/10 border-green-500/20 text-green-400' :
                                status?.status === 'failed' ? 'bg-red-500/10 border-red-500/20 text-red-400' :
                                    'bg-gray-800 border-gray-700 text-gray-400'
                            }`}>
                            {status?.status === 'running' && <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />}
                            {status?.status || 'INITIALIZING'}
                        </div>
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-6 py-8 relative z-10 h-[calc(100vh-64px)]">
                <div className="flex h-full select-none">
                    {/* Left Sidebar */}
                    <div style={{ width: `${leftWidth}%` }} className="flex flex-col gap-6 h-full overflow-hidden min-w-[200px] relative">
                        {/* Workflow Progress */}
                        <div className="h-1/2 bg-gray-900/40 backdrop-blur-md rounded-2xl border border-white/5 overflow-hidden flex flex-col shadow-xl">
                            <div className="p-4 border-b border-white/5 bg-white/5 flex items-center gap-2">
                                <Activity className="w-4 h-4 text-cyan-400" />
                                <h2 className="text-sm font-semibold text-gray-200">Workflow Progress</h2>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                                <ProgressTimeline projectId={projectId || ''} />
                            </div>
                        </div>

                        {/* Generated Files */}
                        <div className="h-1/2 bg-gray-900/40 backdrop-blur-md rounded-2xl border border-white/5 overflow-hidden flex flex-col shadow-xl">
                            <div className="p-4 border-b border-white/5 bg-white/5 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <FileText className="w-4 h-4 text-purple-400" />
                                    <h2 className="text-sm font-semibold text-gray-200">Generated Files</h2>
                                </div>
                                <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">{files.length}</span>
                            </div>
                            <div className="flex-1 overflow-y-auto p-2 custom-scrollbar">
                                {files.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-gray-500 text-xs text-center p-4">
                                        <FileText className="w-8 h-8 mb-2 opacity-20" />
                                        <p>No files generated yet</p>
                                    </div>
                                ) : (
                                    <div className="space-y-1">
                                        {files.map((file) => (
                                            <button
                                                key={file.path}
                                                onClick={() => setSelectedFile(file)}
                                                className={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all flex items-center gap-2 group ${selectedFile?.path === file.path
                                                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                                                    : 'text-gray-400 hover:bg-white/5 hover:text-gray-200 border border-transparent'
                                                    }`}
                                            >
                                                <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                                                <span className="truncate font-medium">{file.filename}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Resizer Handle Left */}
                    <div
                        className="w-4 cursor-col-resize flex items-center justify-center hover:bg-white/5 transition-colors z-20"
                        onMouseDown={() => setIsDraggingLeft(true)}
                    >
                        <div className="w-1 h-8 bg-gray-700 rounded-full" />
                    </div>

                    {/* Center - Chat */}
                    <div style={{ width: `${100 - leftWidth - rightWidth}%` }} className="bg-gray-900/60 backdrop-blur-md rounded-2xl border border-white/5 overflow-hidden shadow-2xl flex flex-col min-w-[300px]">
                        <div className="p-4 border-b border-white/5 bg-black/20 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                                <h2 className="text-sm font-bold text-gray-200">AI Orchestrator</h2>
                            </div>
                        </div>
                        <ChatInterface
                            onSendMessage={handleSendMessage}
                            messages={chatMessages}
                            isLoading={isChatLoading}
                        />
                    </div>

                    {/* Resizer Handle Right */}
                    {!isFullscreen && (
                        <div
                            className="w-4 cursor-col-resize flex items-center justify-center hover:bg-white/5 transition-colors z-20"
                            onMouseDown={() => setIsDraggingRight(true)}
                        >
                            <div className="w-1 h-8 bg-gray-700 rounded-full" />
                        </div>
                    )}

                    {/* Right Panel - File Viewer (compact) */}
                    {!isFullscreen && (
                        <div style={{ width: `${rightWidth}%` }} className="bg-gray-900/60 backdrop-blur-xl rounded-2xl border border-white/5 overflow-hidden shadow-xl flex flex-col min-w-[250px]">
                            {selectedFile ? (
                                <>
                                    <div className="p-4 border-b border-white/5 bg-black/30 backdrop-blur-md flex items-center justify-between">
                                        <div className="flex items-center gap-2 flex-1 min-w-0">
                                            <FileText className="w-4 h-4 text-purple-400 flex-shrink-0" />
                                            <span className="text-sm font-semibold text-gray-200 truncate">{selectedFile.filename}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => setIsFullscreen(true)}
                                                className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                                                title="Fullscreen"
                                            >
                                                <Maximize2 className="w-4 h-4 text-gray-400" />
                                            </button>
                                            <button
                                                onClick={() => setSelectedFile(null)}
                                                className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                                            >
                                                <X className="w-4 h-4 text-gray-400" />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Scrollable viewer */}
                                    <div className="flex-1 overflow-y-auto bg-gradient-to-br from-gray-900/80 via-gray-800/70 to-black/80 backdrop-blur-lg custom-scrollbar">
                                        <FileViewer file={selectedFile} />
                                    </div>

                                    {/* Approve button */}
                                    {awaitingReview && (
                                        <div className="p-4 border-t border-white/5 bg-black/50 backdrop-blur-md">
                                            <button
                                                onClick={handleApprove}
                                                className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 rounded-xl font-bold text-white shadow-lg shadow-cyan-500/30 transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                                            >
                                                <Activity className="w-4 h-4" />
                                                Approve & Continue
                                            </button>
                                            <p className="text-xs text-gray-500 text-center mt-2">
                                                Or type your changes in chat
                                            </p>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="flex-1 flex flex-col items-center justify-center text-gray-500 p-6">
                                    <Maximize2 className="w-12 h-12 mb-4 opacity-20" />
                                    <h3 className="text-sm font-semibold text-gray-400 mb-2">No File Selected</h3>
                                    <p className="text-xs text-gray-600 text-center">
                                        Click a file to view its contents
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>

            {/* FULLSCREEN MODAL with GLASSMORPHISM */}
            {isFullscreen && selectedFile && (
                <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-center justify-center p-8 animate-in fade-in duration-200">
                    {/* Glass Container */}
                    <div className="w-full h-full max-w-7xl bg-gradient-to-br from-gray-900/95 via-gray-800/90 to-black/95 backdrop-blur-2xl rounded-3xl border border-white/10 shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-300">
                        {/* Modal Header */}
                        <div className="p-6 border-b border-white/10 bg-black/40 backdrop-blur-md flex items-center justify-between flex-shrink-0">
                            <div className="flex items-center gap-3">
                                <FileText className="w-5 h-5 text-purple-400" />
                                <h2 className="text-xl font-bold text-white">{selectedFile.filename}</h2>
                            </div>
                            <button
                                onClick={() => setIsFullscreen(false)}
                                className="p-2 hover:bg-white/10 rounded-xl transition-colors group"
                                title="Close (Esc)"
                            >
                                <X className="w-6 h-6 text-gray-400 group-hover:text-white transition-colors" />
                            </button>
                        </div>

                        {/* Scrollable Content */}
                        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                            <FileViewer file={selectedFile} />
                        </div>

                        {/* Approve Button in Modal */}
                        {awaitingReview && (
                            <div className="p-6 border-t border-white/10 bg-black/40 backdrop-blur-md flex-shrink-0">
                                <button
                                    onClick={handleApprove}
                                    className="w-full py-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 rounded-2xl font-bold text-lg text-white shadow-2xl shadow-cyan-500/40 transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-3"
                                >
                                    <Activity className="w-5 h-5" />
                                    Approve & Continue
                                </button>
                                <p className="text-sm text-gray-400 text-center mt-3">
                                    Or type your changes in chat to modify
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
