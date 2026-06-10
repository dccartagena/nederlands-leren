import { describe, it, expect } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import Settings from '@/pages/Settings'

describe('Settings — maintenance panel', () => {
  it('lists background jobs with status', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getByText(/Mantenimiento automático/i)).toBeInTheDocument()
      expect(screen.getByText(/Copia de seguridad diaria/i)).toBeInTheDocument()
    })
    // seed job shows its last status chip
    expect(screen.getByText('ok')).toBeInTheDocument()
    // never-run job shows "nunca"
    expect(screen.getByText(/nunca/i)).toBeInTheDocument()
  })

  it('runs a job on demand', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() => screen.getByText(/Copia de seguridad diaria/i))
    const button = screen.getByLabelText(/Ejecutar Copia de seguridad/i)
    fireEvent.click(button)
    await waitFor(() => {
      expect(button).not.toBeDisabled()
    })
  })

  it('still renders the serene mode toggle', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getByText(/Modo sereno desactivado/i)).toBeInTheDocument()
    })
  })
})
