import { http } from './http'

export const publicApi = {
  login: (payload) => http.post('/public/login', payload),
  me: () => http.get('/public/me'),
  projects: (params) => http.get('/public/projects', { params }),
  releases: (projectId, params) => http.get(`/public/projects/${projectId}/releases`, { params }),
  release: (releaseId) => http.get(`/public/releases/${releaseId}`),
  downloadUrl: (assetId) => `/api/public/assets/${assetId}/download`
}
