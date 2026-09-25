import { create } from 'zustand'

interface UIState {
  sidebarCollapsed: boolean
  flashMessage: string | null
  toggleSidebar: () => void
  setFlash: (message: string | null) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  flashMessage: null,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setFlash: (message) => {
    set({ flashMessage: message })
    if (message) {
      setTimeout(() => set({ flashMessage: null }), 6000)
    }
  },
}))
