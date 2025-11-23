/**
 * Loading Spinner Component
 */
import React from 'react';

interface LoadingSpinnerProps {
    size?: 'small' | 'medium' | 'large';
    text?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'medium', text }) => {
    const sizes = {
        small: 'w-4 h-4 border-2',
        medium: 'w-8 h-8 border-3',
        large: 'w-12 h-12 border-4'
    };

    return (
        <div className="flex flex-col items-center justify-center gap-3">
            <div className={`${sizes[size]} border-blue-500 border-t-transparent rounded-full animate-spin`} />
            {text && <p className="text-sm text-gray-400">{text}</p>}
        </div>
    );
};

export default LoadingSpinner;
