import { http } from './http'

export const adminApi = {
  login: (payload) => http.post('/admin/login', payload),
  repositories: () => http.get('/admin/repositories'),
  createRepository: (payload) => http.post('/admin/repositories', payload),
  updateRepository: (id, payload) => http.put(`/admin/repositories/${id}`, payload),
  deleteRepository: (id) => http.delete(`/admin/repositories/${id}`),
  syncRepository: (id) => http.post(`/admin/repositories/${id}/sync`),
  syncLogs: () => http.get('/admin/sync-logs'),
  downloadLogs: () => http.get('/admin/download-logs')
}
