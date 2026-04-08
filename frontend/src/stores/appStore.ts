import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  level: 'a0' | 'a1'
  theme?: string
  audioEnabled: boolean
  setLevel: (l: 'a0' | 'a1') => void
  setTheme: (t: string | undefined) => void
  setAudioEnabled: (v: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      level: 'a0',
      theme: undefined,
      audioEnabled: true,
      setLevel: (level) => set({ level }),
      setTheme: (theme) => set({ theme }),
      setAudioEnabled: (audioEnabled) => set({ audioEnabled }),
    }),
    { name: 'nl-app-settings' }
  )
)
