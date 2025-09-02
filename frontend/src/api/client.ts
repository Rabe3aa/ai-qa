import axios from 'axios';
import { getToken, clearToken } from '../auth';

const baseURL = (import.meta as any).env?.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      clearToken();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export async function login(username: string, password: string): Promise<string> {
  const params = new URLSearchParams();
  params.set('username', username);
  params.set('password', password);
  params.set('grant_type', 'password');
  const res = await api.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return res.data.access_token as string;
}

export async function getProjects() {
  const res = await api.get('/projects/');
  return res.data;
}

export async function getDashboardStats(params: { project_id?: number; start_date?: string; end_date?: string } = {}) {
  const res = await api.get('/dashboard/stats', { params });
  return res.data;
}

export async function getAgentPerformance(params: { project_id?: number; start_date?: string; end_date?: string; agent?: string } = {}) {
  const res = await api.get('/dashboard/agent-performance', { params });
  return res.data;
}

export async function exportAgentPerformance(params: { project_id?: number; start_date?: string; end_date?: string; agent?: string } = {}) {
  const res = await api.get('/dashboard/agent-performance/export', { params, responseType: 'blob' });
  return res.data as Blob;
}

// Calls
export async function getCalls(params: { project_id?: number; status?: string; start_date?: string; end_date?: string; agent?: string; q?: string; limit?: number } = {}) {
  const res = await api.get('/calls/', { params });
  return res.data;
}

export async function exportCalls(params: { project_id?: number; status?: string; start_date?: string; end_date?: string; agent?: string; q?: string } = {}) {
  const res = await api.get('/calls/export', { params, responseType: 'blob' });
  return res.data as Blob;
}

export async function createUploadUrl(projectId: number, req: { filename: string; content_type: string }) {
  const res = await api.post('/calls/upload-url', req, { params: { project_id: projectId } });
  return res.data as { upload_url: string; s3_key: string; call_id: number };
}

export async function uploadToPresignedUrl(url: string, file: File) {
  const contentType = file.type || 'application/octet-stream';
  // Use plain axios to avoid baseURL
  const res = await axios.put(url, file, { headers: { 'Content-Type': contentType } });
  return res.status;
}

export async function analyzeCall(callId: number, model = 'gpt-4o') {
  const res = await api.post(`/calls/${callId}/analyze`, null, { params: { model } });
  return res.data;
}

export async function getCall(callId: number) {
  const res = await api.get(`/calls/${callId}`);
  return res.data;
}

export async function getCallReport(callId: number) {
  const res = await api.get(`/calls/${callId}/report`);
  return res.data;
}
