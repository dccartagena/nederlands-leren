import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import Dashboard from '@/pages/Dashboard'
import Lesson from '@/pages/Lesson'
import Practice from '@/pages/Practice'
import Progress from '@/pages/Progress'
import Chat from '@/pages/Chat'
import { useAppStore } from '@/stores/appStore'

export default function App() {
  const theme = useAppStore(s => s.theme)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme !== 'light')
  }, [theme])

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="lesson/:level?" element={<Lesson />} />
        <Route path="practice/:gameType?" element={<Practice />} />
        <Route path="progress" element={<Progress />} />
        <Route path="chat" element={<Chat />} />
      </Route>
    </Routes>
  )
}
