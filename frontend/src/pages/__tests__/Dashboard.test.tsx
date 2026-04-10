import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '@/test/utils'
import Dashboard from '@/pages/Dashboard'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import { mockUserProgress } from '@/test/mocks/handlers'

const BASE = '/api/v1'

describe('Dashboard', () => {
  it('renders game grid links', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Tarjetas')).toBeInTheDocument()
      expect(screen.getByText('Escuchar')).toBeInTheDocument()
      expect(screen.getByText('Emparejar')).toBeInTheDocument()
      expect(screen.getByText('Test')).toBeInTheDocument()
      expect(screen.getByText('Rellenar')).toBeInTheDocument()
      expect(screen.getByText('Ordenar')).toBeInTheDocument()
      expect(screen.getByText('Historia')).toBeInTheDocument()
    })
  })

  it('renders stat cards when progress loads', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('XP')).toBeInTheDocument()
      expect(screen.getByText('Racha')).toBeInTheDocument()
      expect(screen.getByText('Pendientes')).toBeInTheDocument()
    })
  })

  it('renders xp_total from user progress', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText(mockUserProgress.xp_total.toString())).toBeInTheDocument()
    })
  })

  it('shows due-card review CTA when due cards exist', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText(/tarjetas para repasar/i)).toBeInTheDocument()
    })
  })

  it('hides CTA when no due cards', async () => {
    server.use(http.get(`${BASE}/progress/due`, () => HttpResponse.json([])))
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.queryByText(/tarjetas para repasar/i)).toBeNull()
    })
  })

  it('renders quick links to lesson and chat', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Lecciones')).toBeInTheDocument()
      expect(screen.getByText('Chat IA')).toBeInTheDocument()
    })
  })
})
