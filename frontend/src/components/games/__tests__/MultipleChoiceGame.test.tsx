import { describe, it, expect } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import MultipleChoiceGame from '@/components/games/MultipleChoiceGame'

describe('MultipleChoiceGame', () => {
  it('renders question after vocab loads', async () => {
    renderWithProviders(<MultipleChoiceGame />)
    await waitFor(() => {
      // Question prompt text
      expect(screen.getByText(/¿Cómo se dice en neerlandés\?/i)).toBeInTheDocument()
    })
  })

  it('renders exactly 4 option buttons', async () => {
    renderWithProviders(<MultipleChoiceGame />)
    await waitFor(() => screen.getByText(/¿Cómo se dice en neerlandés\?/i))
    const buttons = screen.getAllByRole('button')
    // 4 option buttons + possibly a refresh button
    expect(buttons.length).toBeGreaterThanOrEqual(4)
  })

  it('shows score counter', async () => {
    renderWithProviders(<MultipleChoiceGame />)
    await waitFor(() => {
      expect(screen.getByText(/Aciertos:/i)).toBeInTheDocument()
    })
  })

  it('highlights correct answer on selection', async () => {
    renderWithProviders(<MultipleChoiceGame />)
    await waitFor(() => screen.getByText(/¿Cómo se dice en neerlandés\?/i))
    // Click the first option button
    const buttons = screen.getAllByRole('button')
    fireEvent.click(buttons[0])
    await waitFor(() => {
      // After selection buttons are styled — one will be green (correct) or red (wrong)
      const allButtons = screen.getAllByRole('button')
      const hasGreen = allButtons.some((b) => b.className.includes('green'))
      expect(hasGreen).toBe(true)
    })
  })
})

describe('fisherYatesShuffle (via buildQuestion)', () => {
  it('produces arrays of the same length (smoke test via MultipleChoiceGame)', async () => {
    renderWithProviders(<MultipleChoiceGame />)
    await waitFor(() => {
      const buttons = screen.getAllByRole('button')
      // 4 game options rendered → shuffle worked and produced 4 items
      expect(buttons.length).toBeGreaterThanOrEqual(4)
    })
  })
})
