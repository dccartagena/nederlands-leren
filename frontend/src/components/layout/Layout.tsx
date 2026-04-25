import { Outlet, NavLink } from 'react-router-dom'
import {
  Home,
  BookOpen,
  Gamepad2,
  BarChart2,
  MessageCircle,
  Settings,
  Sun,
  Moon,
} from 'lucide-react'
import { useAppStore } from '@/stores/appStore'

const navItems = [
  { to: '/dashboard', icon: Home, label: 'Inicio' },
  { to: '/lesson', icon: BookOpen, label: 'Lección' },
  { to: '/practice', icon: Gamepad2, label: 'Práctica' },
  { to: '/progress', icon: BarChart2, label: 'Progreso' },
  { to: '/chat', icon: MessageCircle, label: 'Chat' },
  { to: '/settings', icon: Settings, label: 'Ajustes' },
]

export default function Layout() {
  const { theme, setTheme } = useAppStore()
  const isDark = theme !== 'light'

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top header */}
      <header className="sticky top-0 z-30 border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
          <span className="text-lg font-bold tracking-tight text-gray-900 dark:text-white">
            🇳🇱 Nederlands
          </span>

          {/* Desktop nav */}
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300'
                      : 'text-gray-500 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white'
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Dark mode toggle */}
          <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 pb-24 md:pb-8">
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      <nav className="safe-area-inset-bottom fixed inset-x-0 bottom-0 z-30 border-t border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 md:hidden">
        <div className="flex">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors ${
                  isActive
                    ? 'text-brand-600 dark:text-brand-400'
                    : 'text-gray-400 dark:text-gray-500'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={20} strokeWidth={isActive ? 2.5 : 1.75} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
