import React from 'react';
import { Wifi, WifiOff } from 'lucide-react';

interface ConnectionStatusProps {
    isConnected: boolean;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ isConnected }) => {
    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${isConnected
                ? 'bg-green-900/20 border-green-800 text-green-400'
                : 'bg-red-900/20 border-red-800 text-red-400'
            }`}>
            {isConnected ? (
                <>
                    <Wifi className="w-3 h-3" />
                    <span>Connected</span>
                </>
            ) : (
                <>
                    <WifiOff className="w-3 h-3" />
                    <span>Disconnected</span>
                </>
            )}
        </div>
    );
};

export default ConnectionStatus;
