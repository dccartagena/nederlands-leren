import { useQuery } from '@tanstack/react-query'
import { fetchUserProgress, fetchDueCards } from '@/lib/api'
import { Link } from 'react-router-dom'
import { BookOpen, MessageCircle, Flame, Star } from 'lucide-react'

const games = [
  { to: '/practice/flashcard', label: 'Tarjetas', icon: '🃏', color: 'bg-blue-50 hover:bg-blue-100 text-blue-700 dark:bg-blue-950 dark:hover:bg-blue-900 dark:text-blue-300' },
  { to: '/practice/listen-choose', label: 'Escuchar', icon: '🎧', color: 'bg-purple-50 hover:bg-purple-100 text-purple-700 dark:bg-purple-950 dark:hover:bg-purple-900 dark:text-purple-300' },
  { to: '/practice/word-match', label: 'Emparejar', icon: '🔗', color: 'bg-green-50 hover:bg-green-100 text-green-700 dark:bg-green-950 dark:hover:bg-green-900 dark:text-green-300' },
  { to: '/practice/multiple-choice', label: 'Test', icon: '❓', color: 'bg-yellow-50 hover:bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:hover:bg-yellow-900 dark:text-yellow-300' },
  { to: '/practice/fill-blank', label: 'Rellenar', icon: '✏️', color: 'bg-orange-50 hover:bg-orange-100 text-orange-700 dark:bg-orange-950 dark:hover:bg-orange-900 dark:text-orange-300' },
  { to: '/practice/unscramble', label: 'Ordenar', icon: '🔀', color: 'bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-950 dark:hover:bg-red-900 dark:text-red-300' },
  { to: '/practice/story', label: 'Historia', icon: '📖', color: 'bg-teal-50 hover:bg-teal-100 text-teal-700 dark:bg-teal-950 dark:hover:bg-teal-900 dark:text-teal-300' },
]

export default function Dashboard() {
  const { data: progress } = useQuery({ queryKey: ['user-progress'], queryFn: fetchUserProgress })
  const { data: dueCards } = useQuery({ queryKey: ['due-cards'], queryFn: () => fetchDueCards(5) })

  return (
    <div className="space-y-6">
      {/* Stats bar */}
      {progress && (
        <div className="grid grid-cols-3 gap-4">
          <StatCard icon={<Star className="text-yellow-500" size={20} />} label="XP" value={progress.xp_total} />
          <StatCard icon={<Flame className="text-orange-500" size={20} />} label="Racha" value={`${progress.streak_days} días`} />
          <StatCard icon={<BookOpen className="text-blue-500" size={20} />} label="Pendientes" value={dueCards?.length ?? 0} />
        </div>
      )}

      {/* Due cards CTA */}
      {dueCards && dueCards.length > 0 && (
        <Link
          to="/practice/flashcard"
          className="block p-4 rounded-xl bg-dutch-700 text-white shadow hover:bg-dutch-600 transition-colors"
        >
          <div className="font-semibold text-lg">Tienes {dueCards.length} tarjetas para repasar</div>
          <div className="text-sm opacity-80 mt-0.5">¡Revisar ahora!</div>
        </Link>
      )}

      {/* Game grid */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Juegos</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {games.map(({ to, label, icon, color }) => (
            <Link
              key={to}
              to={to}
              className={`flex flex-col items-center justify-center p-4 rounded-xl font-medium text-sm transition-colors ${color}`}
            >
              <span className="text-3xl mb-1">{icon}</span>
              {label}
            </Link>
          ))}
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 gap-4">
        <Link to="/lesson" className="flex items-center gap-3 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-dutch-500 transition-colors">
          <BookOpen className="text-dutch-600" size={22} />
          <div>
            <div className="font-medium">Lecciones</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Vocabulario y gramática</div>
          </div>
        </Link>
        <Link to="/chat" className="flex items-center gap-3 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-dutch-500 transition-colors">
          <MessageCircle className="text-dutch-600" size={22} />
          <div>
            <div className="font-medium">Chat IA</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Practica conversación</div>
          </div>
        </Link>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex flex-col items-center p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
      {icon}
      <div className="text-xl font-bold mt-1">{value}</div>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
    </div>
  )
}
