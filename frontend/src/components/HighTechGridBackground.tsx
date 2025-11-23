import React from 'react';

const HighTechGridBackground = () => {
    const symbols = ['{ }', '</>', '01', '&&', '||', '=>', 'fn', 'var', '[]', '()', '#', 'import', 'return', 'class', 'const', 'let', 'async', 'await'];

    return (
        <div className="fixed inset-0 z-0 overflow-hidden bg-[#020204] pointer-events-none">

            {/* 1. Deep Atmospheric Gradient */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,_#1a1a2e_0%,_#000000_80%)] opacity-80" />

            {/* 2. Horizon Glow */}
            <div className="absolute top-[25%] left-0 right-0 h-[2px] bg-cyan-500/80 blur-[4px] shadow-[0_0_30px_rgba(6,182,212,1)] z-10" />
            <div className="absolute top-[25%] left-0 right-0 h-[150px] bg-gradient-to-b from-cyan-500/20 to-transparent blur-[30px] z-0" />

            {/* 3. Moving Grid Container */}
            <div
                className="absolute inset-0 flex items-center justify-center"
                style={{
                    perspective: '1000px',
                    transformStyle: 'preserve-3d',
                }}
            >
                {/* The Grid Plane */}
                <div
                    className="absolute w-[300vw] h-[300vh] origin-center"
                    style={{
                        transform: 'rotateX(75deg) translateY(-100px) translateZ(-100px)',
                        backgroundImage: `
              linear-gradient(to right, rgba(6, 182, 212, 0.3) 2px, transparent 2px),
              linear-gradient(to bottom, rgba(6, 182, 212, 0.3) 2px, transparent 2px)
            `,
                        backgroundSize: '80px 80px',
                        maskImage: 'linear-gradient(to bottom, transparent 0%, black 15%, black 80%, transparent 100%)',
                        WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 15%, black 80%, transparent 100%)',
                        animation: 'gridMove 1.5s linear infinite',
                    }}
                />
            </div>

            {/* 4. Floating Coding Symbols */}
            <div className="absolute inset-0 font-mono z-20">
                {[...Array(30)].map((_, i) => {
                    const symbol = symbols[Math.floor(Math.random() * symbols.length)];
                    const isCyan = Math.random() > 0.5;
                    return (
                        <div
                            key={`sym-${i}`}
                            className={`absolute font-bold ${isCyan ? 'text-cyan-400' : 'text-violet-400'}`}
                            style={{
                                top: `${Math.random() * 100}%`,
                                left: `${Math.random() * 100}%`,
                                opacity: Math.random() * 0.6 + 0.2,
                                fontSize: `${Math.random() * 12 + 10}px`,
                                animation: `floatSymbol ${Math.random() * 10 + 10}s linear infinite`,
                                animationDelay: `-${Math.random() * 10}s`,
                                textShadow: isCyan ? '0 0 5px rgba(6, 182, 212, 0.6)' : '0 0 5px rgba(139, 92, 246, 0.6)'
                            }}
                        >
                            {symbol}
                        </div>
                    );
                })}
            </div>

            <style>{`
        @keyframes gridMove {
          0% { background-position: 0 0; }
          100% { background-position: 0 80px; }
        }
        @keyframes floatSymbol {
          0% { transform: translateY(0px) rotate(0deg); opacity: 0; }
          20% { opacity: 0.8; }
          80% { opacity: 0.8; }
          100% { transform: translateY(-150px) rotate(${Math.random() > 0.5 ? 15 : -15}deg); opacity: 0; }
        }
      `}</style>
        </div>
    );
};

export default HighTechGridBackground;
