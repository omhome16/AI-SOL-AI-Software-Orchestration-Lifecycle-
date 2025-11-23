import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Upload, ArrowRight, Loader2, X, Github, Settings } from 'lucide-react';
import { projectService } from '../services/api';

const Requirements = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [images, setImages] = useState<File[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [formData, setFormData] = useState({
        name: '',
        type: 'website',
        requirements: '',
        enable_github: false,
        github_username: '',
        github_token: '',
        generate_tests: true,
        generate_devops: true,
    });

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const newFiles = Array.from(e.target.files);
            const totalFiles = [...images, ...newFiles].slice(0, 3); // Max 3
            setImages(totalFiles);
        }
    };

    const removeImage = (index: number) => {
        setImages(images.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        // Simulate progress bar
        const progressInterval = setInterval(() => {
            setProgress(prev => {
                if (prev >= 90) return prev;
                return prev + 5;
            });
        }, 200);

        try {
            const data = new FormData();
            data.append('name', formData.name);
            data.append('type', formData.type);
            data.append('requirements', formData.requirements);
            data.append('enable_github', String(formData.enable_github));
            data.append('github_username', formData.github_username);
            data.append('github_token', formData.github_token);
            data.append('generate_tests', String(formData.generate_tests));
            data.append('generate_devops', String(formData.generate_devops));

            images.forEach((image) => {
                data.append('images', image);
            });

            const response = await projectService.createProject(data);

            setProgress(100);
            clearInterval(progressInterval);

            const { project_id } = response;
            // Navigate to configuration page instead of dashboard
            setTimeout(() => navigate(`/configure/${project_id}`), 500);

        } catch (error) {
            console.error('Error creating project:', error);
            alert('Failed to create project. Is the backend running?');
            setLoading(false);
            clearInterval(progressInterval);
        }
    };

    // Animation variants
    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: {
            opacity: 1,
            y: 0,
            transition: {
                type: "spring",
                stiffness: 100,
                damping: 10
            }
        }
    };

    return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center p-6 relative overflow-hidden font-sans">
            {/* Dynamic Background */}
            <div className="absolute inset-0 overflow-hidden -z-10">
                <div className="absolute top-[-20%] left-[-10%] w-[800px] h-[800px] bg-purple-600/20 rounded-full blur-[120px] animate-pulse" style={{ animationDuration: '8s' }} />
                <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-blue-600/20 rounded-full blur-[100px] animate-pulse" style={{ animationDuration: '10s', animationDelay: '1s' }} />
                <div className="absolute top-[40%] left-[30%] w-[400px] h-[400px] bg-cyan-500/10 rounded-full blur-[80px] animate-pulse" style={{ animationDuration: '12s', animationDelay: '2s' }} />
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
            </div>

            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="w-full max-w-3xl"
            >
                <motion.div variants={itemVariants} className="mb-10 text-center">
                    <h2 className="text-5xl font-extrabold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400 tracking-tight">
                        Build Your Vision
                    </h2>
                    <p className="text-lg text-gray-400 max-w-lg mx-auto leading-relaxed">
                        Describe your dream application, and let our AI architects bring it to life.
                    </p>
                </motion.div>

                <motion.form
                    variants={itemVariants}
                    onSubmit={handleSubmit}
                    className="space-y-8 bg-white/5 p-10 rounded-[2rem] border border-white/10 backdrop-blur-xl shadow-2xl relative overflow-hidden"
                >
                    {/* Decorative glow inside form */}
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50" />

                    <motion.div variants={itemVariants} className="space-y-3">
                        <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider ml-1">Project Name</label>
                        <input
                            type="text"
                            required
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="w-full bg-black/40 border border-white/10 rounded-xl p-5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all text-white placeholder-gray-600 text-lg"
                            placeholder="e.g., Quantum Task Manager"
                        />
                    </motion.div>

                    <motion.div variants={itemVariants} className="space-y-3">
                        <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider ml-1">Platform</label>
                        <div className="grid grid-cols-3 gap-4">
                            {['website', 'android', 'ios'].map((type) => (
                                <button
                                    key={type}
                                    type="button"
                                    onClick={() => setFormData({ ...formData, type })}
                                    className={`p-4 rounded-xl border-2 transition-all capitalize font-bold text-sm tracking-wide ${formData.type === type
                                        ? 'bg-blue-600/20 border-blue-500 text-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.3)]'
                                        : 'bg-black/40 border-transparent hover:border-white/10 text-gray-500 hover:text-gray-300'
                                        }`}
                                >
                                    {type}
                                </button>
                            ))}
                        </div>
                    </motion.div>

                    <motion.div variants={itemVariants} className="space-y-3">
                        <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider ml-1">Vision & Requirements</label>
                        <textarea
                            required
                            value={formData.requirements}
                            onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
                            className="w-full h-48 bg-black/40 border border-white/10 rounded-xl p-5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all resize-none text-white placeholder-gray-600 text-base leading-relaxed"
                            placeholder="Describe the core features, target audience, and design aesthetic..."
                        />
                    </motion.div>

                    {/* Advanced Options */}
                    <motion.div variants={itemVariants} className="space-y-6 pt-6 border-t border-white/5">
                        <div className="flex items-center gap-2 text-gray-400 font-medium text-sm">
                            <Settings className="w-4 h-4" /> Configuration
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <label className="flex items-center gap-4 p-4 bg-black/20 rounded-xl border border-white/5 cursor-pointer hover:bg-white/5 transition-all group">
                                <div className={`w-6 h-6 rounded-md border flex items-center justify-center transition-colors ${formData.generate_tests ? 'bg-blue-500 border-blue-500' : 'border-gray-600 group-hover:border-gray-500'}`}>
                                    {formData.generate_tests && <span className="text-white text-xs">✓</span>}
                                </div>
                                <input
                                    type="checkbox"
                                    checked={formData.generate_tests}
                                    onChange={(e) => setFormData({ ...formData, generate_tests: e.target.checked })}
                                    className="hidden"
                                />
                                <span className="text-sm text-gray-300 group-hover:text-white transition-colors">Generate Test Suite</span>
                            </label>

                            <label className="flex items-center gap-4 p-4 bg-black/20 rounded-xl border border-white/5 cursor-pointer hover:bg-white/5 transition-all group">
                                <div className={`w-6 h-6 rounded-md border flex items-center justify-center transition-colors ${formData.generate_devops ? 'bg-blue-500 border-blue-500' : 'border-gray-600 group-hover:border-gray-500'}`}>
                                    {formData.generate_devops && <span className="text-white text-xs">✓</span>}
                                </div>
                                <input
                                    type="checkbox"
                                    checked={formData.generate_devops}
                                    onChange={(e) => setFormData({ ...formData, generate_devops: e.target.checked })}
                                    className="hidden"
                                />
                                <span className="text-sm text-gray-300 group-hover:text-white transition-colors">DevOps Configuration</span>
                            </label>
                        </div>

                        <div className="space-y-4">
                            <label className="flex items-center gap-4 p-4 bg-black/20 rounded-xl border border-white/5 cursor-pointer hover:bg-white/5 transition-all group">
                                <div className={`w-6 h-6 rounded-md border flex items-center justify-center transition-colors ${formData.enable_github ? 'bg-purple-500 border-purple-500' : 'border-gray-600 group-hover:border-gray-500'}`}>
                                    {formData.enable_github && <span className="text-white text-xs">✓</span>}
                                </div>
                                <input
                                    type="checkbox"
                                    checked={formData.enable_github}
                                    onChange={(e) => setFormData({ ...formData, enable_github: e.target.checked })}
                                    className="hidden"
                                />
                                <div className="flex items-center gap-3">
                                    <Github className="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
                                    <span className="text-sm text-gray-300 group-hover:text-white transition-colors">Connect GitHub Repository</span>
                                </div>
                            </label>

                            <AnimatePresence>
                                {formData.enable_github && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0, marginTop: 0 }}
                                        animate={{ opacity: 1, height: 'auto', marginTop: 16 }}
                                        exit={{ opacity: 0, height: 0, marginTop: 0 }}
                                        className="grid grid-cols-1 md:grid-cols-2 gap-4 overflow-hidden"
                                    >
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Username</label>
                                            <input
                                                type="text"
                                                value={formData.github_username}
                                                onChange={(e) => setFormData({ ...formData, github_username: e.target.value })}
                                                className="w-full bg-black/40 border border-white/10 rounded-lg p-3 text-sm focus:border-purple-500 outline-none text-white transition-colors"
                                                placeholder="octocat"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Access Token</label>
                                            <input
                                                type="password"
                                                value={formData.github_token}
                                                onChange={(e) => setFormData({ ...formData, github_token: e.target.value })}
                                                className="w-full bg-black/40 border border-white/10 rounded-lg p-3 text-sm focus:border-purple-500 outline-none text-white transition-colors"
                                                placeholder="ghp_..."
                                            />
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>

                    <motion.div variants={itemVariants} className="pt-2">
                        <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider ml-1 mb-3 block">Reference Images</label>
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center hover:border-blue-500/50 hover:bg-blue-500/5 transition-all cursor-pointer group relative overflow-hidden"
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                className="hidden"
                                accept="image/*"
                                multiple
                            />
                            <div className="relative z-10">
                                <Upload className="w-10 h-10 mx-auto mb-3 text-gray-600 group-hover:text-blue-400 transition-colors" />
                                <p className="text-sm text-gray-400 group-hover:text-gray-300 transition-colors">Drop images here or click to upload</p>
                            </div>
                        </div>

                        {/* Image Previews */}
                        {images.length > 0 && (
                            <div className="flex gap-3 mt-4 overflow-x-auto pb-2 scrollbar-hide">
                                {images.map((file, idx) => (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.8 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        key={idx}
                                        className="relative w-24 h-24 rounded-xl overflow-hidden border border-white/10 flex-shrink-0 group"
                                    >
                                        <img
                                            src={URL.createObjectURL(file)}
                                            alt="preview"
                                            className="w-full h-full object-cover"
                                        />
                                        <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); removeImage(idx); }}
                                            className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            <X className="w-5 h-5 text-white" />
                                        </button>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </motion.div>

                    <motion.button
                        variants={itemVariants}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        type="submit"
                        disabled={loading}
                        className="w-full py-5 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold text-lg rounded-xl hover:shadow-[0_0_30px_rgba(37,99,235,0.4)] transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden group"
                    >
                        {loading ? (
                            <div className="w-full flex flex-col items-center">
                                <div className="flex items-center gap-2 mb-2 text-sm font-medium tracking-wide">
                                    <Loader2 className="w-4 h-4 animate-spin" /> INITIALIZING ARCHITECT...
                                </div>
                                <div className="w-64 h-1 bg-black/20 rounded-full overflow-hidden backdrop-blur-sm">
                                    <motion.div
                                        className="h-full bg-white"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progress}%` }}
                                    />
                                </div>
                            </div>
                        ) : (
                            <>
                                Launch Project <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </motion.button>
                </motion.form>
            </motion.div>
        </div>
    );
};

export default Requirements;
