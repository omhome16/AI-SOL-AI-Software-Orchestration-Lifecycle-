import React, { useState, useEffect, useRef } from 'react';
import {
    Send, Bot, User, Loader2,
    Rocket, CheckCircle, AlertTriangle, ClipboardCheck,
    Play, FileText, Pause, SkipForward, Layers, Trophy,
    Wand2, Save, Activity
} from 'lucide-react';

interface ChatMessage {
    role: 'user' | 'ai';
    content: string;
    timestamp: string;
    buttons?: ActionButton[];
}

interface ActionButton {
    label: string;
    action: string;
    variant: 'primary' | 'secondary';
}

interface ChatInterfaceProps {
    onSendMessage: (message: string) => void;
    messages: ChatMessage[];
    isLoading?: boolean;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
    onSendMessage,
    messages,
    isLoading = false
}) => {
    const [inputMessage, setInputMessage] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = () => {
        if (inputMessage.trim() && !isLoading) {
            onSendMessage(inputMessage.trim());
            setInputMessage('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleButtonClick = (action: string) => {
        onSendMessage(action.toLowerCase());
    };

    const formatTimestamp = (timestamp: string): string => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return '';
        }
    };

    // Helper to detect log type and return icon/style
    const getLogStyle = (content: string) => {
        if (!content) return null;
        if (content.startsWith('[START]')) return { icon: Rocket, color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', label: 'Workflow Started' };
        if (content.startsWith('[SUCCESS]')) return { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', label: 'Success' };
        if (content.startsWith('[ERROR]')) return { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Error' };
        if (content.startsWith('[REVIEW]')) return { icon: ClipboardCheck, color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Review Required' };
        if (content.startsWith('[PAUSED]')) return { icon: Pause, color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Paused' };
        if (content.startsWith('[APPROVED]')) return { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', label: 'Approved' };
        if (content.startsWith('[EXEC]')) return { icon: Play, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', label: 'Executing' };
        if (content.startsWith('[FILE]')) return { icon: FileText, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20', label: 'File Generation' };
        if (content.startsWith('[FORMAT]')) return { icon: Wand2, color: 'text-pink-400', bg: 'bg-pink-500/10', border: 'border-pink-500/20', label: 'Formatting' };
        if (content.startsWith('[CHECKPOINT]')) return { icon: Save, color: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/20', label: 'Checkpoint' };
        if (content.startsWith('[SKIP]')) return { icon: SkipForward, color: 'text-gray-400', bg: 'bg-gray-500/10', border: 'border-gray-500/20', label: 'Skipped' };
        if (content.startsWith('[STAGE]')) return { icon: Layers, color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', label: 'Stage' };
        if (content.startsWith('[COMPLETE]')) return { icon: Trophy, color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Completed' };
        if (content.startsWith('[CHECK]')) return { icon: Activity, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', label: 'Check' };

        return null; // Not a log message
    };

    const renderMessageContent = (msg: ChatMessage) => {
        const logStyle = getLogStyle(msg.content);

        if (logStyle) {
            const Icon = logStyle.icon;
            // Remove the prefix from the content
            const cleanContent = msg.content.replace(/^\[.*?\]\s*/, '');

            return (
                <div className={`flex items-start gap-3 p-3 rounded-xl border ${logStyle.bg} ${logStyle.border} backdrop-blur-sm w-full`}>
                    <div className={`p-2 rounded-lg bg-black/20 ${logStyle.color}`}>
                        <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className={`text-xs font-bold uppercase tracking-wider mb-1 ${logStyle.color}`}>
                            {logStyle.label}
                        </div>
                        <p className="text-sm text-gray-200 leading-relaxed">{cleanContent}</p>
                    </div>
                </div>
            );
        }

        // Standard chat message
        return (
            <div
                className={`rounded-2xl px-5 py-4 shadow-xl backdrop-blur-sm border ${msg.role === 'user'
                    ? 'bg-blue-600/20 border-blue-500/30 text-blue-50 rounded-tr-sm'
                    : 'bg-gray-800/60 border-white/5 text-gray-200 rounded-tl-sm'
                    }`}
            >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full bg-gray-900/50 relative">
            {/* Header - Minimal */}
            <div className="absolute top-0 left-0 right-0 z-10 p-4 bg-gradient-to-b from-gray-900/80 to-transparent backdrop-blur-sm flex items-center justify-between pointer-events-none">
                <div className="flex items-center gap-2 pointer-events-auto">
                    <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                    <span className="text-xs font-bold tracking-widest text-gray-400 uppercase">Orchestrator Active</span>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar pt-16">
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center opacity-50">
                        <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 flex items-center justify-center mb-6 animate-float">
                            <Bot className="w-10 h-10 text-cyan-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">AI Orchestrator Ready</h3>
                        <p className="text-sm text-gray-400 text-center max-w-xs">
                            I'm here to help you build. Give me a command or ask about the project status.
                        </p>
                    </div>
                ) : (
                    messages.map((msg, index) => {
                        const isLog = !!getLogStyle(msg.content);

                        return (
                            <div
                                key={index}
                                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} ${isLog ? 'w-full' : ''}`}
                            >
                                {msg.role === 'ai' && !isLog && (
                                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-600 to-blue-700 flex items-center justify-center shadow-lg shadow-cyan-900/50 mt-1">
                                        <Bot className="w-5 h-5 text-white" />
                                    </div>
                                )}

                                <div className={`flex flex-col ${isLog ? 'w-full' : 'max-w-[85%]'} ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>

                                    {renderMessageContent(msg)}

                                    {/* Action Buttons */}
                                    {msg.buttons && msg.buttons.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mt-3 animate-fade-in">
                                            {msg.buttons.map((button, btnIndex) => (
                                                <button
                                                    key={btnIndex}
                                                    onClick={() => handleButtonClick(button.action)}
                                                    className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wide uppercase transition-all transform hover:scale-105 active:scale-95 ${button.variant === 'primary'
                                                        ? 'bg-cyan-500 hover:bg-cyan-400 text-black shadow-lg shadow-cyan-500/20'
                                                        : 'bg-white/10 hover:bg-white/20 text-white border border-white/10'
                                                        }`}
                                                >
                                                    {button.label}
                                                </button>
                                            ))}
                                        </div>
                                    )}

                                    <span className="text-[10px] font-medium text-gray-600 mt-2 px-1">
                                        {formatTimestamp(msg.timestamp)}
                                    </span>
                                </div>

                                {msg.role === 'user' && (
                                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center mt-1">
                                        <User className="w-5 h-5 text-gray-300" />
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}

                {/* Loading Indicator */}
                {isLoading && (
                    <div className="flex gap-4 justify-start animate-pulse">
                        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center">
                            <Bot className="w-5 h-5 text-gray-500" />
                        </div>
                        <div className="bg-gray-800/50 rounded-2xl rounded-tl-sm px-5 py-4 flex items-center gap-3 border border-white/5">
                            <div className="flex gap-1">
                                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                            <span className="text-xs font-medium text-gray-400">Processing...</span>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-gray-900/80 backdrop-blur-md border-t border-white/5">
                <div className="relative flex items-center gap-2 bg-black/40 border border-white/10 rounded-xl p-1.5 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/20 transition-all">
                    <input
                        type="text"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type your instruction..."
                        disabled={isLoading}
                        className="flex-1 bg-transparent border-none text-sm text-white placeholder-gray-500 focus:ring-0 px-4 py-2"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!inputMessage.trim() || isLoading}
                        className="p-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-800 disabled:text-gray-600 text-white transition-all shadow-lg shadow-cyan-900/20"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                </div>
                <div className="flex justify-between items-center mt-2 px-1">
                    <p className="text-[10px] text-gray-600">
                        AI can generate code, run tests, and deploy.
                    </p>
                    <div className="text-[10px] text-gray-600 font-mono">
                        v1.0.0
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;
