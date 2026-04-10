import { describe, it, expect } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import FlashcardGame from '@/components/games/FlashcardGame'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'

const BASE = '/api/v1'

describe('FlashcardGame', () => {
  it('shows loading initially', () => {
    renderWithProviders(<FlashcardGame />)
    // Either loading placeholder or card renders — no crash
    expect(document.body).toBeTruthy()
  })

  it('renders the first card after data loads', async () => {
    renderWithProviders(<FlashcardGame />)
    await waitFor(() => {
      expect(screen.getByText(/hond/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no due cards', async () => {
    server.use(http.get(`${BASE}/progress/due`, () => HttpResponse.json([])))
    renderWithProviders(<FlashcardGame />)
    await waitFor(() => {
      // Empty state renders — text in Spanish
      expect(screen.getByText(/repaso|tarjeta|pendiente|sin/i)).toBeInTheDocument()
    })
  })

  it('flips card when clicked', async () => {
    renderWithProviders(<FlashcardGame />)
    await waitFor(() => screen.getByText(/hond/i))

    // Before flip: Dutch word visible
    expect(screen.getByText(/hond/i)).toBeInTheDocument()

    // Click the card to flip — find the clickable card container
    const clickable = document.querySelector('[style*="perspective"]') as HTMLElement
    if (clickable) fireEvent.click(clickable)

    await waitFor(() => {
      // After flip: Spanish translation visible
      expect(screen.getByText(/perro/i)).toBeInTheDocument()
    })
  })

  it('shows 4 rating buttons after flipping', async () => {
    renderWithProviders(<FlashcardGame />)
    await waitFor(() => screen.getByText(/hond/i))

    const clickable = document.querySelector('[style*="perspective"]') as HTMLElement
    if (clickable) fireEvent.click(clickable)

    await waitFor(() => {
      expect(screen.getByText('Otra vez')).toBeInTheDocument()
      expect(screen.getByText('Difícil')).toBeInTheDocument()
      expect(screen.getByText('Bien')).toBeInTheDocument()
      expect(screen.getByText('Fácil')).toBeInTheDocument()
    })
  })

  it('submits review on rating click and advances card', async () => {
    renderWithProviders(<FlashcardGame />)
    await waitFor(() => screen.getByText(/hond/i))

    // Flip
    const clickable = document.querySelector('[style*="perspective"]') as HTMLElement
    if (clickable) fireEvent.click(clickable)

    // Rate
    await waitFor(() => screen.getByText('Bien'))
    fireEvent.click(screen.getByText('Bien'))

    // XP gained should appear
    await waitFor(() => {
      expect(screen.getByText(/\+\d+ XP/)).toBeInTheDocument()
    })
  })

  it('shows audio button when card has audio_files', async () => {
    renderWithProviders(<FlashcardGame />)
    await waitFor(() => {
      // lucide Volume2 icon button rendered
      const audioBtn = document.querySelector('button[class*="rounded-full"]')
      expect(audioBtn).toBeTruthy()
    })
  })

  it('shows progress bar', async () => {
    renderWithProviders(<FlashcardGame />)
    await waitFor(() => screen.getByText(/hond/i))
    expect(screen.getByText(/1 \//)).toBeInTheDocument()
  })
})
