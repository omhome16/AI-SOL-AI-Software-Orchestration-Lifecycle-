import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Wand2, Plus, Trash2, ArrowRight, Loader2 } from 'lucide-react';
import { projectService } from '../services/api';

interface ConfigField {
    name: string;
    label: string;
    type: 'text' | 'color' | 'file' | 'number' | 'select' | 'checkbox';
    options?: string[];
    required: boolean;
    default?: any;
    description?: string;
}

const ProjectConfiguration: React.FC = () => {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();

    const [fields, setFields] = useState<ConfigField[]>([]);
    const [values, setValues] = useState<Record<string, any>>({});
    const [customFields, setCustomFields] = useState<ConfigField[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [addingCustomField, setAddingCustomField] = useState(false);
    const [customFieldDescription, setCustomFieldDescription] = useState('');

    useEffect(() => {
        fetchConfigFields();
    }, []);

    const fetchConfigFields = async () => {
        try {
            setLoading(true);

            // Get project details to know type and requirements
            console.log('[CONFIG] Fetching project details for:', projectId);
            const projectData = await projectService.getProject(projectId!);
            console.log('[CONFIG] Project data:', projectData);

            // Generate config fields based on project type
            const requestBody = {
                project_type: projectData.user_context?.project_type || projectData.type || 'website',
                requirements: projectData.requirements || ''
            };

            console.log('[CONFIG] Requesting config fields with:', requestBody);

            const response = await fetch(`http://localhost:8005/api/v1/projects/${projectId}/generate-config-fields`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${await response.text()}`);
            }

            const data = await response.json();
            console.log('[CONFIG] Received fields:', data.fields);
            setFields(data.fields);

            // Initialize values with defaults
            const initialValues: Record<string, any> = {};
            data.fields.forEach((field: ConfigField) => {
                initialValues[field.name] = field.default;
            });
            setValues(initialValues);

        } catch (error) {
            console.error('Failed to fetch config fields:', error);
            alert(`Failed to generate configuration fields:\n${error}\n\nPlease check the console and backend logs.`);
        } finally {
            setLoading(false);
        }
    };

    const handleValueChange = (fieldName: string, value: any) => {
        setValues(prev => ({ ...prev, [fieldName]: value }));
    };

    const handleAddCustomField = async () => {
        if (!customFieldDescription.trim()) return;

        try {
            setAddingCustomField(true);

            const response = await fetch(`http://localhost:8005/api/v1/projects/${projectId}/validate-custom-field?description=${encodeURIComponent(customFieldDescription)}`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const data = await response.json();

            if (!data.field || !data.field.name) {
                throw new Error("Invalid field data received from AI");
            }

            const newField = data.field;

            setCustomFields(prev => [...prev, newField]);
            setValues(prev => ({ ...prev, [newField.name]: newField.default }));
            setCustomFieldDescription('');

        } catch (error) {
            console.error('Failed to add custom field:', error);
            alert("Could not create a configuration field from your description.\n\nPlease try being more specific (e.g., 'Upload a background image' or 'Set a custom font size').");
        } finally {
            setAddingCustomField(false);
        }
    };

    const handleRemoveCustomField = (fieldName: string) => {
        setCustomFields(prev => prev.filter(f => f.name !== fieldName));
        const newValues = { ...values };
        delete newValues[fieldName];
        setValues(newValues);
    };

    const handleSubmit = async () => {
        try {
            setSaving(true);

            // Save configuration
            await fetch(`http://localhost:8005/api/v1/projects/${projectId}/save-configuration`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ configuration: values })
            });

            // Start workflow
            await projectService.startWorkflow(projectId!);

            // Navigate to dashboard
            navigate(`/dashboard/${projectId}`);

        } catch (error) {
            console.error('Failed to save configuration:', error);
        } finally {
            setSaving(false);
        }
    };

    const renderField = (field: ConfigField) => {
        const value = values[field.name];

        switch (field.type) {
            case 'color':
                return (
                    <div className="flex gap-3 items-center">
                        <input
                            type="color"
                            value={value || field.default}
                            onChange={(e) => handleValueChange(field.name, e.target.value)}
                            className="w-16 h-12 rounded-lg border-2 border-white/10 cursor-pointer"
                        />
                        <input
                            type="text"
                            value={value || field.default}
                            onChange={(e) => handleValueChange(field.name, e.target.value)}
                            className="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none"
                            placeholder="#000000"
                        />
                    </div>
                );

            case 'file':
                return (
                    <div className="border-2 border-dashed border-white/10 rounded-lg p-6 text-center hover:border-cyan-500/50 transition-colors cursor-pointer">
                        <input
                            type="file"
                            accept="image/*"
                            onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) {
                                    const reader = new FileReader();
                                    reader.onload = () => handleValueChange(field.name, reader.result);
                                    reader.readAsDataURL(file);
                                }
                            }}
                            className="hidden"
                            id={`file-${field.name}`}
                        />
                        <label htmlFor={`file-${field.name}`} className="cursor-pointer">
                            <div className="text-gray-400 mb-2">Click to upload {field.label}</div>
                            {value && <img src={value} alt="Preview" className="max-w-xs mx-auto mt-2 rounded-lg" />}
                        </label>
                    </div>
                );

            case 'select':
                return (
                    <div className="relative">
                        <select
                            value={value || field.default}
                            onChange={(e) => handleValueChange(field.name, e.target.value)}
                            className="w-full bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg px-4 py-3 text-white focus:border-cyan-500 focus:outline-none appearance-none cursor-pointer hover:bg-black/50 transition-colors"
                            style={{ backgroundImage: 'none' }} // Remove default arrow in some browsers
                        >
                            {field.options?.map(option => (
                                <option key={option} value={option} className="bg-gray-900 text-white py-2">
                                    {option}
                                </option>
                            ))}
                        </select>
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
                            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </div>
                    </div>
                );

            case 'checkbox':
                return (
                    <label className="flex items-center gap-3 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={value || field.default}
                            onChange={(e) => handleValueChange(field.name, e.target.checked)}
                            className="w-5 h-5 rounded border-white/10 bg-black/40 text-cyan-500 focus:ring-cyan-500"
                        />
                        <span className="text-gray-300">Enable {field.label}</span>
                    </label>
                );

            case 'number':
                return (
                    <input
                        type="number"
                        value={value || field.default}
                        onChange={(e) => handleValueChange(field.name, parseInt(e.target.value))}
                        className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none"
                    />
                );

            default: // text
                return (
                    <input
                        type="text"
                        value={value || field.default}
                        onChange={(e) => handleValueChange(field.name, e.target.value)}
                        className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none"
                        placeholder={field.description}
                    />
                );
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-cyan-500 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Generating configuration fields...</p>
                </div>
            </div>
        );
    }

    const allFields = [...fields, ...customFields];

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900">
            <div className="max-w-4xl mx-auto px-6 py-12">
                {/* Header */}
                <div className="mb-12">
                    <h1 className="text-4xl font-bold text-white mb-3">Configure Your Project</h1>
                    <p className="text-gray-400">Customize your project settings and preferences</p>
                </div>

                {/* Configuration Fields */}
                <div className="space-y-6 mb-8">
                    {allFields.map((field) => {
                        const isCustom = customFields.includes(field);

                        return (
                            <div
                                key={field.name}
                                className="bg-gray-800/40 backdrop-blur-sm border border-white/10 rounded-xl p-6 hover:border-white/20 transition-all"
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex-1">
                                        <label className="block text-white font-semibold mb-1">
                                            {field.label}
                                            {field.required && <span className="text-red-400 ml-1">*</span>}
                                        </label>
                                        {field.description && (
                                            <p className="text-sm text-gray-400 mb-3">{field.description}</p>
                                        )}
                                    </div>
                                    {isCustom && (
                                        <button
                                            onClick={() => handleRemoveCustomField(field.name)}
                                            className="text-red-400 hover:text-red-300 p-2"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    )}
                                </div>
                                {renderField(field)}
                            </div>
                        );
                    })}
                </div>

                {/* Add Custom Field */}
                <div className="bg-gray-800/20 border border-white/5 rounded-xl p-6 mb-8">
                    <div className="flex items-center gap-2 mb-4">
                        <Wand2 className="w-5 h-5 text-purple-400" />
                        <h3 className="text-white font-semibold">Add Custom Field</h3>
                    </div>
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={customFieldDescription}
                            onChange={(e) => setCustomFieldDescription(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleAddCustomField()}
                            placeholder="Describe the field you need (e.g., 'Upload background image')"
                            className="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                            disabled={addingCustomField}
                        />
                        <button
                            onClick={handleAddCustomField}
                            disabled={addingCustomField || !customFieldDescription.trim()}
                            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-lg transition-all flex items-center gap-2"
                        >
                            {addingCustomField ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Plus className="w-5 h-5" />
                            )}
                            Add Field
                        </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">AI will generate an appropriate field based on your description</p>
                </div>

                {/* Submit Button */}
                <button
                    onClick={handleSubmit}
                    disabled={saving}
                    className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:from-gray-700 disabled:to-gray-700 text-white font-bold py-4 rounded-xl transition-all shadow-lg shadow-cyan-900/20 flex items-center justify-center gap-3 group"
                >
                    {saving ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Saving Configuration...
                        </>
                    ) : (
                        <>
                            Start Building
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </>
                    )}
                </button>
            </div>
        </div>
    );
};

export default ProjectConfiguration;
