import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Send } from 'lucide-react';
import { projectService } from '../services/api';

const Chat = () => {
    const { projectId } = useParams();
    const [messages, setMessages] = useState<{ sender: string; text: string }[]>([]);
    const [input, setInput] = useState('');

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMsg = { sender: 'user', text: input };
        setMessages((prev) => [...prev, userMsg]);
        setInput('');

        try {
            if (projectId) {
                const data = await projectService.chatWithOrchestrator(projectId, userMsg.text);
                setMessages((prev) => [...prev, { sender: 'ai', text: data.response }]);
            }
        } catch (error) {
            console.error('Error sending message:', error);
        }
    };

    return (
        <div className="h-screen flex flex-col bg-background p-4">
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-surface rounded-2xl border border-white/10">
                {messages.map((msg, i) => (
                    <div
                        key={i}
                        className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[80%] p-3 rounded-xl ${msg.sender === 'user'
                                ? 'bg-primary text-black rounded-tr-none'
                                : 'bg-white/10 text-white rounded-tl-none'
                                }`}
                        >
                            {msg.text}
                        </div>
                    </div>
                ))}
            </div>

            <div className="flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                    className="flex-1 bg-surface border border-white/10 rounded-xl p-4 focus:border-primary outline-none"
                    placeholder="Ask the orchestrator..."
                />
                <button
                    onClick={sendMessage}
                    className="p-4 bg-primary text-black rounded-xl hover:bg-primary/80 transition-colors"
                >
                    <Send className="w-6 h-6" />
                </button>
            </div>
        </div>
    );
};

export default Chat;
