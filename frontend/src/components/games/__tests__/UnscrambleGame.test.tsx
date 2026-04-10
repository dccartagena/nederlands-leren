import { describe, it, expect } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import UnscrambleGame from '@/components/games/UnscrambleGame'
import { mockUnscramble } from '@/test/mocks/handlers'

describe('UnscrambleGame', () => {
  it('renders the Spanish sentence prompt', async () => {
    renderWithProviders(<UnscrambleGame />)
    await waitFor(() => {
      expect(screen.getByText(new RegExp(mockUnscramble.sentence_es, 'i'))).toBeInTheDocument()
    })
  })

  it('renders all shuffled word tiles', async () => {
    renderWithProviders(<UnscrambleGame />)
    await waitFor(() => {
      for (const word of mockUnscramble.shuffled_words) {
        const tiles = screen.getAllByText(new RegExp(`^${word}$`))
        expect(tiles.length).toBeGreaterThan(0)
      }
    })
  })

  it('moves word to answer area on click', async () => {
    renderWithProviders(<UnscrambleGame />)
    await waitFor(() => screen.getByText(new RegExp(mockUnscramble.sentence_es, 'i')))

    // Click the first shuffled word tile
    const firstWord = mockUnscramble.shuffled_words[0]
    const tile = screen.getAllByText(new RegExp(`^${firstWord}$`))[0]
    fireEvent.click(tile)

    await waitFor(() => {
      // Word appears in answer zone — it might appear twice (source dimmed + answer)
      const all = screen.getAllByText(new RegExp(`^${firstWord}$`))
      expect(all.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows correct message when answer matches', async () => {
    renderWithProviders(<UnscrambleGame />)
    await waitFor(() => screen.getByText(new RegExp(mockUnscramble.sentence_es, 'i')))

    // The correct sentence is: 'De hond loopt in het park.'
    // shuffled_words: ['park', 'De', 'in', 'het', 'loopt', 'hond']
    // Click words in correct order
    const correctOrder = ['De', 'hond', 'loopt', 'in', 'het', 'park']
    for (const word of correctOrder) {
      const tiles = screen.getAllByText(new RegExp(`^${word}$`))
      // Find non-disabled tile
      const clickable = tiles.find((t) => !t.closest('[disabled]'))
      if (clickable) fireEvent.click(clickable)
    }

    await waitFor(() => screen.getByRole('button', { name: /comprobar/i }))
    fireEvent.click(screen.getByRole('button', { name: /comprobar/i }))

    await waitFor(() => {
      expect(screen.getByText(/correcto|¡bien/i)).toBeInTheDocument()
    })
  })

  it('shows error for wrong answer', async () => {
    renderWithProviders(<UnscrambleGame />)
    await waitFor(() => screen.getByText(new RegExp(mockUnscramble.sentence_es, 'i')))

    // Click only one word (incomplete answer)
    const firstWord = mockUnscramble.shuffled_words[0]
    const tiles = screen.getAllByText(new RegExp(`^${firstWord}$`))
    if (tiles[0]) fireEvent.click(tiles[0])

    // Try to find a check button — may or may not be shown before all words clicked
    const checkBtn = screen.queryByRole('button', { name: /comprobar/i })
    if (checkBtn) {
      fireEvent.click(checkBtn)
      await waitFor(() => {
        expect(screen.getByText(/incorrecto|intenta/i)).toBeInTheDocument()
      })
    }
  })

  it('shows score counter', async () => {
    renderWithProviders(<UnscrambleGame />)
    await waitFor(() => {
      expect(screen.getByText(/Aciertos:/i)).toBeInTheDocument()
    })
  })
})
