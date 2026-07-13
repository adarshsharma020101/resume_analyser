/**
 * API client — all requests go to localhost backend only.
 * No external API calls are made from this client.
 */
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080' || 'http://localhost:8000' 

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 180_000,
})

// Attach JWT from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ats_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ats_token')
      localStorage.removeItem('ats_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// ── Auth ───────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/api/auth/login', { username, password }).then(r => r.data),
  register: (username: string, password: string) =>
    api.post('/api/auth/register', { username, password }).then(r => r.data),
}

// ── Documents ─────────────────────────────────────────────────────────────────
export const documentsApi = {
  uploadResume: (file: File) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post('/api/documents/resume', fd).then(r => r.data)
  },
  addLinkedInIdentifier: (linkedin_url?: string, linkedin_id?: string) =>
    api.post('/api/documents/linkedin/identifier', null, {
      params: { linkedin_url, linkedin_id },
    }).then(r => r.data),
  uploadLinkedInProfile: (file: File, profile_format = 'auto') => {
    const fd = new FormData(); fd.append('file', file); fd.append('profile_format', profile_format)
    return api.post('/api/documents/linkedin/profile', fd).then(r => r.data)
  },
  list: (doc_type?: string) =>
    api.get('/api/documents', { params: { doc_type } }).then(r => r.data),
  delete: (id: string) =>
    api.delete(`/api/documents/${id}`).then(r => r.data),
}

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsApi = {
  addDescription: (body: { raw_text: string; title?: string; company?: string }) =>
    api.post('/api/jobs/description', body).then(r => r.data),
  uploadDescription: (file: File) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post('/api/jobs/description/upload', fd).then(r => r.data)
  },
  importDataset: (file: File) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post('/api/jobs/dataset', fd).then(r => r.data)
  },
  listOpportunities: (dataset_id?: string) =>
    api.get('/api/jobs/opportunities', { params: { dataset_id } }).then(r => r.data),
  listDatasets: () =>
    api.get('/api/jobs/datasets').then(r => r.data),
  listDescriptions: () =>
    api.get('/api/jobs/descriptions').then(r => r.data),
}

// ── Analysis ──────────────────────────────────────────────────────────────────
export const analysisApi = {
  start: (body: {
    resume_document_id: string
    linkedin_document_id?: string
    target_job_id?: string
    job_ids_to_match?: string[]
  }) => api.post('/api/analysis', body).then(r => r.data),
  get: (session_id: string) =>
    api.get(`/api/analysis/${session_id}`).then(r => r.data),
  list: () =>
    api.get('/api/analysis').then(r => r.data),
  getProvenance: (session_id: string) =>
    api.get(`/api/analysis/${session_id}/provenance`).then(r => r.data),
}

// ── Reports ───────────────────────────────────────────────────────────────────
export const reportsApi = {
  generate: (session_id: string, format: 'json' | 'html' | 'pdf') =>
    api.post('/api/reports/generate', { session_id, format }).then(r => r.data),
  downloadUrl: (session_id: string, fmt: string) =>
    `${BASE_URL}/api/reports/download/${session_id}/${fmt}`,
}

// ── Privacy ───────────────────────────────────────────────────────────────────
export const privacyApi = {
  deleteAll: () =>
    api.delete('/api/privacy/my-data').then(r => r.data),
  exportData: () =>
    api.get('/api/privacy/export').then(r => r.data),
}

// ── Settings ──────────────────────────────────────────────────────────────────
export const settingsApi = {
  getScoringWeights: () =>
    api.get('/api/settings/scoring-weights').then(r => r.data),
}
