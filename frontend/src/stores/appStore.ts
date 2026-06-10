import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LLMProvider } from '@/lib/api'

interface AppState {
  level: 'a0' | 'a1'
  theme?: string
  audioEnabled: boolean
  llmProvider: LLMProvider
  // "Modo sereno": hides XP and combo UI for intrinsically-motivated sessions
  sereneMode: boolean
  setLevel: (l: 'a0' | 'a1') => void
  setTheme: (t: string | undefined) => void
  setAudioEnabled: (v: boolean) => void
  setLlmProvider: (p: LLMProvider) => void
  setSereneMode: (v: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      level: 'a0',
      theme: 'dark',
      audioEnabled: true,
      llmProvider: 'default',
      sereneMode: false,
      setLevel: (level) => set({ level }),
      setTheme: (theme) => set({ theme }),
      setAudioEnabled: (audioEnabled) => set({ audioEnabled }),
      setLlmProvider: (llmProvider) => set({ llmProvider }),
      setSereneMode: (sereneMode) => set({ sereneMode }),
    }),
    { name: 'nl-app-settings' }
  )
)
