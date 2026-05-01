import axios from 'axios'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api'
})

http.interceptors.request.use((config) => {
  const isAdminRequest = config.url?.startsWith('/admin')
  const token = isAdminRequest ? localStorage.getItem('admin_token') : localStorage.getItem('public_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (location.pathname.startsWith('/admin')) {
        localStorage.removeItem('admin_token')
        location.href = '/admin/login'
      } else {
        localStorage.removeItem('public_token')
        localStorage.removeItem('public_user')
        location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
