import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import EscribirGame, { gradeAnswer } from '@/components/games/EscribirGame'
import type { VocabularyItem } from '@/lib/api'

const noun: VocabularyItem = {
  id: 1,
  dutch_word: 'hond',
  spanish: 'perro',
  article: 'de',
  level: 'a0',
  theme: 'animales',
}

const verb: VocabularyItem = {
  id: 2,
  dutch_word: 'lopen',
  spanish: 'caminar',
  level: 'a0',
  theme: 'acciones',
}

describe('gradeAnswer', () => {
  it('accepts noun with correct article', () => {
    expect(gradeAnswer(noun, 'de hond')).toBe('correct')
  })

  it('is case- and punctuation-insensitive', () => {
    expect(gradeAnswer(noun, '  De Hond. ')).toBe('correct')
  })

  it('flags missing article on nouns', () => {
    expect(gradeAnswer(noun, 'hond')).toBe('article')
  })

  it('flags wrong article on nouns', () => {
    expect(gradeAnswer(noun, 'het hond')).toBe('article')
  })

  it('rejects wrong word', () => {
    expect(gradeAnswer(noun, 'de kat')).toBe('wrong')
  })

  it('accepts non-nouns without article', () => {
    expect(gradeAnswer(verb, 'lopen')).toBe('correct')
  })
})

describe('EscribirGame', () => {
  it('renders the Spanish prompt and input', async () => {
    renderWithProviders(<EscribirGame />)
    await waitFor(() => {
      expect(screen.getByText(/Escribe en neerlandés/i)).toBeInTheDocument()
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })
  })
})
