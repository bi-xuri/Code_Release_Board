import { http } from './http'

export const publicApi = {
  projects: (params) => http.get('/public/projects', { params }),
  releases: (projectId, params) => http.get(`/public/projects/${projectId}/releases`, { params }),
  release: (releaseId) => http.get(`/public/releases/${releaseId}`),
  downloadUrl: (assetId) => `/api/public/assets/${assetId}/download`
}
