import { useEffect, useRef } from 'react';

const ParticleCube = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationFrameId: number;
        let particles: { x: number; y: number; z: number; size: number }[] = [];
        const particleCount = 400; // Number of particles
        const cubeSize = 200; // Size of the cube
        let angleX = 0;
        let angleY = 0;
        let mouseX = 0;
        let mouseY = 0;

        // Initialize particles in a cube shape
        for (let i = 0; i < particleCount; i++) {
            particles.push({
                x: (Math.random() - 0.5) * cubeSize,
                y: (Math.random() - 0.5) * cubeSize,
                z: (Math.random() - 0.5) * cubeSize,
                size: Math.random() * 2 + 0.5
            });
        }

        const handleMouseMove = (e: MouseEvent) => {
            const rect = canvas.getBoundingClientRect();
            mouseX = (e.clientX - rect.left - canvas.width / 2) * 0.0005;
            mouseY = (e.clientY - rect.top - canvas.height / 2) * 0.0005;
        };

        window.addEventListener('mousemove', handleMouseMove);

        const resizeCanvas = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        const draw = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const focalLength = 400;

            // Rotate cube based on mouse or auto-rotation
            angleX += (mouseY - angleX) * 0.05 + 0.002;
            angleY += (mouseX - angleY) * 0.05 + 0.002;

            const cx = Math.cos(angleX);
            const sx = Math.sin(angleX);
            const cy = Math.cos(angleY);
            const sy = Math.sin(angleY);

            particles.forEach(p => {
                // Rotation X
                let y = p.y * cx - p.z * sx;
                let z = p.y * sx + p.z * cx;

                // Rotation Y
                let x = p.x * cy - z * sy;
                z = p.x * sy + z * cy;

                // Projection
                const scale = focalLength / (focalLength + z);
                const projX = x * scale + centerX;
                const projY = y * scale + centerY;

                // Draw particle
                const alpha = (z + cubeSize / 2) / cubeSize; // Fade based on depth
                ctx.fillStyle = `rgba(100, 200, 255, ${Math.max(0.1, alpha)})`;
                ctx.beginPath();
                ctx.arc(projX, projY, p.size * scale, 0, Math.PI * 2);
                ctx.fill();
            });

            animationFrameId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('resize', resizeCanvas);
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 z-0 pointer-events-none opacity-60"
        />
    );
};

export default ParticleCube;
