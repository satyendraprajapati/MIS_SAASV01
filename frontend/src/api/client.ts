/**
 * Axios instance with:
 * - Base URL pointing at FastAPI via Vite proxy
 * - Request interceptor: attaches Bearer token from Zustand store
 * - Response interceptor: clears auth + redirects on 401
 */
import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      // Hard redirect — clears any in-flight requests cleanly
      window.location.replace('/login')
    }
    return Promise.reject(err)
  },
)

export default api
