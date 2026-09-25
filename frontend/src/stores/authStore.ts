import { create } from 'zustand'
import api, { setCsrfToken } from '@/lib/api'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  csrfToken: string
  isLoading: boolean
  isInitialized: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchMe: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  csrfToken: '',
  isLoading: false,
  isInitialized: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const res = await api.post('auth/login', { json: { email, password } }).json<{ user: User; csrf_token: string }>()
      setCsrfToken(res.csrf_token)
      set({ user: res.user, csrfToken: res.csrf_token, isLoading: false, isInitialized: true })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed'
      let detail = message
      try {
        if (err && typeof err === 'object' && 'response' in err) {
          const response = (err as { response: Response }).response
          const body = await response.json() as { detail?: string }
          detail = body.detail || message
        }
      } catch { /* use default */ }
      set({ isLoading: false, error: detail })
      throw new Error(detail)
    }
  },

  logout: async () => {
    try {
      await api.post('auth/logout')
    } catch { /* ignore */ }
    setCsrfToken('')
    set({ user: null, csrfToken: '', isInitialized: true })
  },

  fetchMe: async () => {
    try {
      const res = await api.get('auth/me').json<{ user: User; csrf_token: string }>()
      setCsrfToken(res.csrf_token)
      set({ user: res.user, csrfToken: res.csrf_token, isInitialized: true })
    } catch {
      setCsrfToken('')
      set({ user: null, csrfToken: '', isInitialized: true })
    }
  },

  clearError: () => set({ error: null }),
}))
