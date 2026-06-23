import api from './client'

export interface RegisterPayload {
  email:        string
  password:     string
  full_name:    string
  company_name?: string
}

export interface LoginPayload {
  email:    string
  password: string
}

export interface TokenResponse {
  access_token:  string
  refresh_token: string
  token_type:    string
  expires_in:    number
}

export interface UserProfile {
  id:           string
  email:        string
  full_name:    string
  company_name: string | null
  role:         string
  is_active:    boolean
  created_at:   string
}

export const registerApi = (payload: RegisterPayload) =>
  api.post<UserProfile>('/auth/register', payload).then((r) => r.data)

export const loginApi = (payload: LoginPayload) =>
  api.post<TokenResponse>('/auth/login', payload).then((r) => r.data)

export const getMeApi = () =>
  api.get<UserProfile>('/auth/me').then((r) => r.data)

export const logoutApi = () =>
  api.post('/auth/logout').then((r) => r.data)
