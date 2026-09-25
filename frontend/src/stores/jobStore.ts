import { create } from 'zustand'
import api from '@/lib/api'
import type { Job } from '@/types'

interface JobState {
  currentJob: Job | null
  isLoading: boolean
  pollTimer: ReturnType<typeof setInterval> | null
  fetchJob: (id: string) => Promise<void>
  startPolling: (id: string, onComplete: (job: Job) => void) => void
  stopPolling: () => void
}

export const useJobStore = create<JobState>((set, get) => ({
  currentJob: null,
  isLoading: false,
  pollTimer: null,

  fetchJob: async (id: string) => {
    set({ isLoading: true })
    const res = await api.get(`jobs/${id}`).json<{ job: Job }>()
    set({ currentJob: res.job, isLoading: false })
  },

  startPolling: (id: string, onComplete: (job: Job) => void) => {
    const { stopPolling } = get()
    stopPolling()
    const timer = setInterval(async () => {
      try {
        const res = await api.get(`jobs/${id}/status`).json<{ status: string }>()
        const current = get().currentJob
        if (current && res.status !== current.status) {
          stopPolling()
          const full = await api.get(`jobs/${id}`).json<{ job: Job }>()
          set({ currentJob: full.job })
          onComplete(full.job)
        }
      } catch { /* ignore transient errors */ }
    }, 2500)
    set({ pollTimer: timer })
  },

  stopPolling: () => {
    const { pollTimer } = get()
    if (pollTimer) {
      clearInterval(pollTimer)
      set({ pollTimer: null })
    }
  },
}))
