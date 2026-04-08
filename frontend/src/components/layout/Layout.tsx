import { Outlet, NavLink } from 'react-router-dom'
import { Home, BookOpen, Gamepad2, BarChart2, MessageCircle } from 'lucide-react'

const navItems = [
  { to: '/dashboard', icon: Home, label: 'Inicio' },
  { to: '/lesson', icon: BookOpen, label: 'Lección' },
  { to: '/practice', icon: Gamepad2, label: 'Práctica' },
  { to: '/progress', icon: BarChart2, label: 'Progreso' },
  { to: '/chat', icon: MessageCircle, label: 'Chat' },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top nav */}
      <header className="sticky top-0 z-30 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <span className="text-xl font-bold text-dutch-700">🇳🇱 Nederlands Leren</span>
          <nav className="hidden md:flex gap-1">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-dutch-100 text-dutch-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-30">
        <div className="flex">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center py-2 text-xs font-medium transition-colors ${
                  isActive ? 'text-dutch-600' : 'text-gray-500'
                }`
              }
            >
              <Icon size={20} />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
