/**
 * Axios instance with:
 * - Base URL pointing at FastAPI via Vite proxy
 * - Request interceptor: attaches Bearer token from Zustand store
 * - Response interceptor: clears auth + redirects on 401
 */
import axios from 'axios'
import { useAuthStore } from '../store/authStore'

// In development: Vite proxy rewrites /api/v1 → http://localhost:8000/api/v1
// In production:  VITE_API_URL is set to the Render backend URL at build time
const BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
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
