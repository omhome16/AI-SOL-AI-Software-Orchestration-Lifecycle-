import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Code, Cpu, Globe, Zap } from 'lucide-react';
import HighTechGridBackground from '../components/HighTechGridBackground';

const Landing = () => {
    const navigate = useNavigate();

    return (
        <div className="relative min-h-screen bg-black text-white overflow-hidden font-sans selection:bg-primary selection:text-black">
            <HighTechGridBackground />

            {/* Navbar */}
            <nav className="relative z-10 flex items-center justify-between px-8 py-6 border-b border-white/10 backdrop-blur-md">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(var(--primary),0.5)]">
                        <Cpu className="text-black w-5 h-5" />
                    </div>
                    <span className="text-xl font-bold tracking-tighter">AI-SOL</span>
                </div>
                <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-400">
                    <a href="#" className="hover:text-white transition-colors">Features</a>
                    <a href="#" className="hover:text-white transition-colors">How it Works</a>
                    <a href="#" className="hover:text-white transition-colors">Showcase</a>
                </div>
                <button
                    onClick={() => navigate('/requirements')}
                    className="px-5 py-2 bg-white/5 border border-white/10 rounded-full text-sm font-medium hover:bg-white/10 transition-all hover:scale-105"
                >
                    Launch App
                </button>
            </nav>

            {/* Hero Section */}
            <main className="relative z-10 container mx-auto px-6 pt-20 pb-32 flex flex-col items-center text-center">

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-8"
                >
                    <Sparkles className="w-4 h-4" />
                    <span>Autonomous Software Orchestration Lifecycle</span>
                </motion.div>

                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-500"
                >
                    Build Software <br />
                    <span className="text-white">At The Speed of Thought</span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.4 }}
                    className="text-lg md:text-xl text-gray-400 max-w-2xl mb-10 leading-relaxed"
                >
                    AI-SOL isn't just a code generator. It's a full-cycle autonomous workforce.
                    From requirements to deployment, watch your ideas come to life in real-time.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.6 }}
                    className="flex flex-col sm:flex-row items-center gap-4"
                >
                    <button
                        onClick={() => navigate('/requirements')}
                        className="group relative px-8 py-4 bg-primary text-black font-bold rounded-xl overflow-hidden transition-all hover:scale-105 hover:shadow-[0_0_40px_rgba(var(--primary),0.4)]"
                    >
                        <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                        <span className="relative flex items-center gap-2">
                            Start Building <ArrowRight className="w-5 h-5" />
                        </span>
                    </button>
                    <button className="px-8 py-4 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-all">
                        View Demo
                    </button>
                </motion.div>

                {/* Feature Grid */}
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.8 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24 w-full max-w-5xl"
                >
                    {[
                        { icon: <Globe className="w-6 h-6 text-blue-400" />, title: "Full Stack Generation", desc: "React, Python, Node - we handle the entire stack." },
                        { icon: <Code className="w-6 h-6 text-purple-400" />, title: "Clean Code", desc: "Production-ready, maintainable code with best practices." },
                        { icon: <Zap className="w-6 h-6 text-yellow-400" />, title: "Instant Deployment", desc: "From prompt to live URL in minutes via Docker." }
                    ].map((feature, idx) => (
                        <div key={idx} className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-primary/30 transition-colors text-left">
                            <div className="mb-4 p-3 bg-white/5 rounded-lg w-fit">{feature.icon}</div>
                            <h3 className="text-lg font-bold mb-2">{feature.title}</h3>
                            <p className="text-sm text-gray-400">{feature.desc}</p>
                        </div>
                    ))}
                </motion.div>

            </main>
        </div>
    );
};

export default Landing;
