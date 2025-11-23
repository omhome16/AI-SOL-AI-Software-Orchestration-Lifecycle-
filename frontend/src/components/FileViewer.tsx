import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import axios from 'axios';

interface FileViewerProps {
    file: {
        filename: string;
        path: string;
        full_content: string;
        doc_type: string;
    };
    projectId?: string;
    onFileUpdated?: () => void;
}

const FileViewer: React.FC<FileViewerProps> = ({ file, projectId, onFileUpdated }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState('');

    const isMarkdown = file.filename.endsWith('.md');
    const isCode = file.filename.match(/\.(js|ts|tsx|jsx|py|java|cpp|c|css|html|json|xml|yaml|yml)$/);

    // Clean content for markdown (fix double escaping)
    const cleanContent = (content: string) => {
        if (!content) return '';
        return content.replace(/\\n/g, '\n').replace(/\\"/g, '"');
    };

    // Detect file tree structure
    const isFileTree = file.full_content.includes('├──') || file.full_content.includes('└──') || (file.filename.includes('structure') && !isCode);

    // Extract language from filename
    const getLanguage = (filename: string): string => {
        const ext = filename.split('.').pop()?.toLowerCase();
        const langMap: { [key: string]: string } = {
            'js': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'jsx': 'javascript',
            'py': 'python',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'css': 'css',
            'html': 'html',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml'
        };
        return langMap[ext || ''] || 'text';
    };

    const handleEdit = () => {
        setEditContent(cleanContent(file.full_content));
        setIsEditing(true);
        setSaveMessage('');
    };

    const handleCancel = () => {
        setIsEditing(false);
        setEditContent('');
        setSaveMessage('');
    };

    const handleSave = async () => {
        if (!projectId) {
            setSaveMessage('⚠️ Project ID not available');
            return;
        }

        setIsSaving(true);
        setSaveMessage('');

        try {
            await axios.put(
                `/api/v1/projects/${projectId}/files/content`,
                { content: editContent },
                { params: { path: file.path } }
            );

            setSaveMessage('✅ Saved successfully!');
            setIsEditing(false);

            // Notify parent to refresh
            if (onFileUpdated) {
                onFileUpdated();
            }

            setTimeout(() => setSaveMessage(''), 3000);
        } catch (error: any) {
            setSaveMessage(`❌ Save failed: ${error.response?.data?.detail || error.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    // Toolbar component
    const Toolbar = () => (
        <div className="flex items-center justify-between p-3 bg-[#2d2d2d] border-b border-gray-700">
            <div className="flex items-center gap-3">
                <span className="text-sm text-gray-400 font-mono">{file.filename}</span>
                {saveMessage && (
                    <span className={`text-xs ${saveMessage.includes('✅') ? 'text-green-400' : 'text-red-400'}`}>
                        {saveMessage}
                    </span>
                )}
            </div>
            <div className="flex gap-2">
                {!isEditing ? (
                    <button
                        onClick={handleEdit}
                        className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                        title="Edit this file"
                    >
                        ✏️ Edit
                    </button>
                ) : (
                    <>
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded transition-colors"
                        >
                            {isSaving ? '⏳ Saving...' : '💾 Save'}
                        </button>
                        <button
                            onClick={handleCancel}
                            disabled={isSaving}
                            className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 text-white rounded transition-colors"
                        >
                            ❌ Cancel
                        </button>
                    </>
                )}
            </div>
        </div>
    );

    // Edit mode
    if (isEditing) {
        return (
            <div className="flex flex-col h-full">
                <Toolbar />
                <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="flex-1 p-4 bg-[#1e1e1e] text-gray-300 font-mono text-sm resize-none focus:outline-none border-none"
                    style={{ minHeight: '500px' }}
                    placeholder="Edit file content..."
                />
            </div>
        );
    }

    if (isFileTree) {
        return (
            <div className="flex flex-col h-full">
                <Toolbar />
                <div className="file-tree-viewer p-6 bg-[#1e1e1e] overflow-x-auto">
                    <pre className="font-mono text-sm text-green-400 leading-relaxed">
                        {cleanContent(file.full_content)}
                    </pre>
                </div>
            </div>
        );
    }

    if (isMarkdown) {
        return (
            <div className="flex flex-col h-full">
                <Toolbar />
                <div className="markdown-viewer prose prose-invert max-w-none p-6 overflow-y-auto">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            code({ node, inline, className, children, ...props }) {
                                const match = /language-(\w+)/.exec(className || '');
                                return !inline && match ? (
                                    <SyntaxHighlighter
                                        style={vscDarkPlus}
                                        language={match[1]}
                                        PreTag="div"
                                        {...props}
                                    >
                                        {String(children).replace(/\n$/, '')}
                                    </SyntaxHighlighter>
                                ) : (
                                    <code className={className} {...props}>
                                        {children}
                                    </code>
                                );
                            },
                            table({ children }) {
                                return (
                                    <div className="overflow-x-auto my-4">
                                        <table className="min-w-full border-collapse border border-gray-700">
                                            {children}
                                        </table>
                                    </div>
                                );
                            },
                            th({ children }) {
                                return (
                                    <th className="border border-gray-700 px-4 py-2 bg-gray-800 font-semibold text-left">
                                        {children}
                                    </th>
                                );
                            },
                            td({ children }) {
                                return (
                                    <td className="border border-gray-700 px-4 py-2 align-top">
                                        {children}
                                    </td>
                                );
                            },
                            ul({ children }) {
                                return <ul className="list-disc pl-6 my-4 space-y-1">{children}</ul>;
                            },
                            ol({ children }) {
                                return <ol className="list-decimal pl-6 my-4 space-y-1">{children}</ol>;
                            },
                            h1({ children }) {
                                return <h1 className="text-3xl font-bold mt-8 mb-4 border-b border-gray-700 pb-2">{children}</h1>;
                            },
                            h2({ children }) {
                                return <h2 className="text-2xl font-bold mt-6 mb-3">{children}</h2>;
                            },
                            h3({ children }) {
                                return <h3 className="text-xl font-bold mt-4 mb-2">{children}</h3>;
                            },
                            p({ children }) {
                                return <p className="my-3 leading-relaxed">{children}</p>;
                            }
                        }}
                    >
                        {cleanContent(file.full_content)}
                    </ReactMarkdown>
                </div>
            </div>
        );
    }

    if (isCode) {
        return (
            <div className="flex flex-col h-full">
                <Toolbar />
                <div className="code-viewer overflow-y-auto">
                    <SyntaxHighlighter
                        language={getLanguage(file.filename)}
                        style={vscDarkPlus}
                        showLineNumbers
                        wrapLines
                        customStyle={{
                            margin: 0,
                            padding: '1.5rem',
                            fontSize: '0.875rem',
                            borderRadius: 0,
                        } as { [key: string]: React.CSSProperties }}
                    >
                        {cleanContent(file.full_content)}
                    </SyntaxHighlighter>
                </div>
            </div>
        );
    }

    // Plain text fallback
    return (
        <div className="flex flex-col h-full">
            <Toolbar />
            <div className="text-viewer p-6 overflow-y-auto">
                <pre className="whitespace-pre-wrap font-mono text-sm text-gray-300">
                    {cleanContent(file.full_content)}
                </pre>
            </div>
        </div>
    );
};

export default FileViewer;
