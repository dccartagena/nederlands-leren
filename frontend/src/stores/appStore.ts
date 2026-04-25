import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LLMProvider } from '@/lib/api'

interface AppState {
  level: 'a0' | 'a1'
  theme?: string
  audioEnabled: boolean
  llmProvider: LLMProvider
  setLevel: (l: 'a0' | 'a1') => void
  setTheme: (t: string | undefined) => void
  setAudioEnabled: (v: boolean) => void
  setLlmProvider: (p: LLMProvider) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      level: 'a0',
      theme: 'dark',
      audioEnabled: true,
      llmProvider: 'default',
      setLevel: (level) => set({ level }),
      setTheme: (theme) => set({ theme }),
      setAudioEnabled: (audioEnabled) => set({ audioEnabled }),
      setLlmProvider: (llmProvider) => set({ llmProvider }),
    }),
    { name: 'nl-app-settings' }
  )
)
