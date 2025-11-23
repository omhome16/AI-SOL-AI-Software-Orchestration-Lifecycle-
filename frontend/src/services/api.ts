import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8005/api/v1';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const projectService = {
    createProject: async (data: FormData) => {
        // Don't use the default api instance for FormData - it has JSON headers
        const response = await axios.post(`${API_BASE_URL}/projects/create`, data, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },
    getProjectStatus: async (projectId: string) => {
        const response = await api.get(`/projects/${projectId}/status`);
        return response.data;
    },
    getProjectLogs: async (projectId: string) => {
        const response = await api.get(`/projects/${projectId}/logs`);
        return response.data;
    },
    listProjects: async () => {
        const response = await api.get('/projects');
        return response.data;
    },
    getProject: async (projectId: string) => {
        const response = await api.get(`/projects/${projectId}`);
        return response.data;
    },
    deleteProject: async (projectId: string) => {
        const response = await api.delete(`/projects/${projectId}`);
        return response.data;
    },
    restartProject: async (projectId: string) => {
        const response = await api.post(`/projects/${projectId}/restart`);
        return response.data;
    },
    resumeProject: async (projectId: string, userInput: string) => {
        const response = await api.post(`/projects/${projectId}/resume`, { user_input: userInput });
        return response.data;
    },
    chatWithOrchestrator: async (projectId: string, message: string) => {
        const response = await api.post('/chat', { project_id: projectId, message });
        return response.data;
    },
    listFiles: async (projectId: string) => {
        const response = await api.get(`/projects/${projectId}/files`);
        return response.data;
    },
    getFileContent: async (projectId: string, filePath: string) => {
        const response = await api.get(`/projects/${projectId}/files/content`, {
            params: { file_path: filePath }
        });
        return response.data;
    },
    uploadImage: async (projectId: string, file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post(`/projects/${projectId}/upload-image`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },
    startWorkflow: async (projectId: string) => {
        const response = await api.post(`/projects/${projectId}/start-workflow`);
        return response.data;
    }
};

export const healthService = {
    checkHealth: async () => {
        const response = await api.get('/health');
        return response.data;
    },
    getConfig: async () => {
        const response = await api.get('/config');
        return response.data;
    }
};

export default api;
