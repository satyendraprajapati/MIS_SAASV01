import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserProfile } from '../api/auth'

interface AuthState {
  accessToken:  string | null
  refreshToken: string | null
  user:         UserProfile | null

  setAuth:  (access: string, refresh: string, user: UserProfile) => void
  setUser:  (user: UserProfile) => void
  logout:   () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken:  null,
      refreshToken: null,
      user:         null,

      setAuth: (access, refresh, user) =>
        set({ accessToken: access, refreshToken: refresh, user }),

      setUser: (user) => set({ user }),

      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: 'auth-storage',
      // Only persist tokens + user — no ephemeral UI state
      partialize: (s) => ({
        accessToken:  s.accessToken,
        refreshToken: s.refreshToken,
        user:         s.user,
      }),
    },
  ),
)
