import React from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';

interface DiffViewerProps {
    oldCode: string;
    newCode: string;
    language?: string;
}

const DiffViewer: React.FC<DiffViewerProps> = ({ oldCode, newCode, language = 'javascript' }) => {
    return (
        <div className="diff-container h-full overflow-auto bg-[#1e1e1e] rounded-md border border-[#333]">
            <ReactDiffViewer
                oldValue={oldCode}
                newValue={newCode}
                splitView={true}
                compareMethod={DiffMethod.WORDS}
                styles={{
                    variables: {
                        dark: {
                            diffViewerBackground: '#1e1e1e',
                            diffViewerTitleBackground: '#2d2d2d',
                            addedBackground: '#044B53',
                            removedBackground: '#632F34',
                            gutterBackground: '#2d2d2d',
                            gutterBackgroundDark: '#262626',
                            highlightBackground: '#2a3942',
                            highlightGutterBackground: '#2d2d2d',
                            codeFoldGutterBackground: '#212121',
                            codeFoldBackground: '#262626',
                            emptyLineBackground: '#363946',
                            gutterColor: '#464c67',
                            addedGutterBackground: '#034148',
                            removedGutterBackground: '#632b30',
                            codeFoldContentColor: '#555a7b',
                            diffViewerTitleColor: '#555a7b',
                        }
                    },
                    line: {
                        padding: '10px 2px',
                        '&:hover': {
                            background: '#2a2d35',
                        },
                    }
                }}
                useDarkTheme={true}
                leftTitle="Original"
                rightTitle="Modified"
            />
        </div>
    );
};

export default DiffViewer;
