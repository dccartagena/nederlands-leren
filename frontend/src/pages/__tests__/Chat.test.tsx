import { describe, it, expect } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import Chat from '@/pages/Chat'

describe('Chat', () => {
  it('renders initial assistant greeting', () => {
    renderWithProviders(<Chat />)
    expect(screen.getByText(/neerlandés/i)).toBeInTheDocument()
  })

  it('renders provider selector', () => {
    renderWithProviders(<Chat />)
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('renders send button', () => {
    renderWithProviders(<Chat />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('send button is disabled when input is empty', () => {
    renderWithProviders(<Chat />)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
  })

  it('send button enabled when input has text', async () => {
    renderWithProviders(<Chat />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Hallo' } })
    await waitFor(() => {
      expect(screen.getByRole('button')).not.toBeDisabled()
    })
  })

  it('sends message and displays user text', async () => {
    renderWithProviders(<Chat />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Hoe zeg je hond?' } })
    fireEvent.click(screen.getByRole('button'))
    await waitFor(() => {
      expect(screen.getByText('Hoe zeg je hond?')).toBeInTheDocument()
    })
  })

  it('displays assistant reply after send', async () => {
    renderWithProviders(<Chat />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Test' } })
    fireEvent.click(screen.getByRole('button'))
    await waitFor(() => {
      // The MSW mock returns 'Hallo! Hoe gaat het?'
      expect(screen.getByText(/Hallo! Hoe gaat het?/)).toBeInTheDocument()
    })
  })

  it('Enter key sends message', async () => {
    renderWithProviders(<Chat />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Test Enter key' } })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })
    await waitFor(() => {
      expect(screen.getByText('Test Enter key')).toBeInTheDocument()
    })
  })

  it('Shift+Enter does NOT send message', async () => {
    renderWithProviders(<Chat />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Shift-Enter test' } })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', shiftKey: true })
    // Message should NOT appear in the chat (it stays in input)
    expect(screen.queryByText('Shift-Enter test')).toBeNull()
  })

  it('clears input after send', async () => {
    renderWithProviders(<Chat />)
    const input = screen.getByRole('textbox') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Test clear' } })
    fireEvent.click(screen.getByRole('button'))
    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })
})
