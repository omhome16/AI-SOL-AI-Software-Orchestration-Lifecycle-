import React, { useEffect, useState } from 'react';
import { eventHandler, type WorkflowEvent } from '../services/event_handler';
import './ProgressTimeline.css';

interface StageInfo {
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    agent?: string;
    startTime?: string;
    endTime?: string;
    message?: string;
    events: WorkflowEvent[];
    expanded: boolean;
}

const STAGES = [
    'requirements',
    'architecture',
    'developer',
    'qa',
    'devops'
];

const STAGE_LABELS: Record<string, string> = {
    'requirements': 'Requirements Analysis',
    'architecture': 'Architecture Design',
    'developer': 'Implementation',
    'qa': 'Quality Assurance',
    'devops': 'DevOps & Deployment'
};

export const ProgressTimeline: React.FC<{ projectId: string }> = ({ projectId }) => {
    const [stages, setStages] = useState<Record<string, StageInfo>>(() => {
        const initial: Record<string, StageInfo> = {};
        STAGES.forEach(stage => {
            initial[stage] = {
                name: stage,
                status: 'pending',
                events: [],
                expanded: false
            };
        });
        return initial;
    });

    useEffect(() => {
        // Handle workflow events
        const handleEvent = (event: WorkflowEvent) => {
            if (event.project_id !== projectId) return;

            // Update stage status
            if (event.stage) {
                setStages(prev => {
                    const updated = { ...prev };
                    const stageInfo = updated[event.stage!];

                    if (!stageInfo) return prev;

                    // Add event to stage events
                    stageInfo.events.push(event);

                    // Update stage status based on event type
                    if (event.event_type === 'stage_started') {
                        stageInfo.status = 'running';
                        stageInfo.startTime = event.timestamp;
                        stageInfo.agent = event.agent;
                        stageInfo.message = event.message;
                    } else if (event.event_type === 'stage_completed') {
                        stageInfo.status = 'completed';
                        stageInfo.endTime = event.timestamp;
                        stageInfo.message = event.message;
                    } else if (event.event_type === 'stage_failed') {
                        stageInfo.status = 'failed';
                        stageInfo.endTime = event.timestamp;
                        stageInfo.message = event.message;
                    } else if (event.event_type === 'agent_thinking') {
                        stageInfo.message = event.message;
                    }

                    return updated;
                });
            }
        };

        eventHandler.onAny(handleEvent);

        return () => {
            eventHandler.off('*', handleEvent);
        };
    }, [projectId]);

    const toggleStageExpansion = (stageName: string) => {
        setStages(prev => ({
            ...prev,
            [stageName]: {
                ...prev[stageName],
                expanded: !prev[stageName].expanded
            }
        }));
    };

    const getSeverityColor = (severity?: string) => {
        switch (severity) {
            case 'success': return '#4CAF50';
            case 'warning': return '#FF9800';
            case 'error': return '#F44336';
            case 'critical': return '#D32F2F';
            default: return '#2196F3';
        }
    };

    return (
        <div className="relative pl-4">
            {/* Vertical Line */}
            <div className="absolute left-[27px] top-4 bottom-4 w-0.5 bg-gradient-to-b from-cyan-500/50 via-purple-500/50 to-transparent -z-10" />

            <div className="space-y-8">
                {STAGES.map((stageName) => {
                    const stage = stages[stageName];
                    if (!stage) return null;

                    const isActive = stage.status === 'running';
                    const isCompleted = stage.status === 'completed';
                    const isFailed = stage.status === 'failed';
                    const isPending = stage.status === 'pending';

                    return (
                        <div key={stageName} className={`relative group ${isPending ? 'opacity-50' : 'opacity-100'} transition-opacity duration-500`}>
                            <div
                                className="flex items-start gap-4 cursor-pointer"
                                onClick={() => toggleStageExpansion(stageName)}
                            >
                                {/* Icon / Status Indicator */}
                                <div className={`relative z-10 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center border-2 transition-all duration-500 ${isActive
                                    ? 'bg-black border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.6)] scale-110'
                                    : isCompleted
                                        ? 'bg-green-500 border-green-500 shadow-[0_0_10px_rgba(34,197,94,0.4)]'
                                        : isFailed
                                            ? 'bg-red-500 border-red-500'
                                            : 'bg-black border-gray-700'
                                    }`}>
                                    {isActive && (
                                        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-ping" />
                                    )}
                                    {isCompleted && (
                                        <span className="text-black text-[10px] font-bold">✓</span>
                                    )}
                                    {isFailed && (
                                        <span className="text-white text-[10px] font-bold">!</span>
                                    )}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0 pt-0.5">
                                    <div className="flex items-center justify-between mb-1">
                                        <h4 className={`text-sm font-bold tracking-wide ${isActive ? 'text-cyan-400' : isCompleted ? 'text-green-400' : 'text-gray-300'}`}>
                                            {STAGE_LABELS[stageName]}
                                        </h4>
                                        {stage.events.length > 0 && (
                                            <span className="text-[10px] text-gray-500 font-mono bg-white/5 px-1.5 py-0.5 rounded">
                                                {stage.events.length}
                                            </span>
                                        )}
                                    </div>

                                    {stage.agent && (
                                        <div className="text-xs text-purple-400 font-medium mb-1 flex items-center gap-1">
                                            <span className="w-1 h-1 rounded-full bg-purple-400" />
                                            Agent: {stage.agent}
                                        </div>
                                    )}

                                    {stage.message && (
                                        <p className="text-xs text-gray-400 leading-relaxed line-clamp-2 group-hover:line-clamp-none transition-all">
                                            {stage.message}
                                        </p>
                                    )}

                                    {/* Expanded Events View */}
                                    <div className={`grid transition-all duration-300 ease-in-out ${stage.expanded ? 'grid-rows-[1fr] mt-4 opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
                                        <div className="overflow-hidden">
                                            <div className="space-y-2 pl-2 border-l border-white/10 ml-1">
                                                {stage.events.map((event, eventIndex) => (
                                                    <div
                                                        key={eventIndex}
                                                        className="text-xs p-2 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors"
                                                        style={{ borderLeft: `2px solid ${getSeverityColor(event.severity)}` }}
                                                    >
                                                        <div className="flex justify-between items-start gap-2 mb-1">
                                                            <span className="font-mono text-gray-500 text-[10px] uppercase">{event.event_type}</span>
                                                            <span className="text-[10px] text-gray-600">{new Date(event.timestamp).toLocaleTimeString()}</span>
                                                        </div>
                                                        <p className="text-gray-300">{event.message}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default ProgressTimeline;
