import api from './client'

export interface LoginPayload {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export const loginApi = (payload: LoginPayload) =>
  api.post<TokenResponse>('/auth/login', payload).then((r) => r.data)
