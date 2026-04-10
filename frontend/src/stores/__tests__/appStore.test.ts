import { describe, it, expect, beforeEach } from 'vitest'
import { useAppStore } from '@/stores/appStore'

function resetStore() {
  useAppStore.setState({ level: 'a0', theme: 'dark', audioEnabled: true })
  localStorage.clear()
}

describe('appStore', () => {
  beforeEach(() => {
    resetStore()
  })

  it('has correct initial state', () => {
    const state = useAppStore.getState()
    expect(state.level).toBe('a0')
    expect(state.theme).toBe('dark')
    expect(state.audioEnabled).toBe(true)
  })

  it('setLevel updates level', () => {
    useAppStore.getState().setLevel('a1')
    expect(useAppStore.getState().level).toBe('a1')
  })

  it('setTheme updates theme', () => {
    useAppStore.getState().setTheme('light')
    expect(useAppStore.getState().theme).toBe('light')
  })

  it('setTheme to undefined clears theme', () => {
    useAppStore.getState().setTheme(undefined)
    expect(useAppStore.getState().theme).toBeUndefined()
  })

  it('setAudioEnabled toggles to false', () => {
    useAppStore.getState().setAudioEnabled(false)
    expect(useAppStore.getState().audioEnabled).toBe(false)
  })

  it('setAudioEnabled toggles back to true', () => {
    useAppStore.getState().setAudioEnabled(false)
    useAppStore.getState().setAudioEnabled(true)
    expect(useAppStore.getState().audioEnabled).toBe(true)
  })

  it('persists level to localStorage', () => {
    useAppStore.getState().setLevel('a1')
    const stored = JSON.parse(localStorage.getItem('nl-app-settings') || '{}')
    expect(stored?.state?.level).toBe('a1')
  })

  it('persists theme to localStorage', () => {
    useAppStore.getState().setTheme('light')
    const stored = JSON.parse(localStorage.getItem('nl-app-settings') || '{}')
    expect(stored?.state?.theme).toBe('light')
  })
})
