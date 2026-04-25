import { useQuery } from '@tanstack/react-query'
import { fetchUserProgress, fetchDueCards } from '@/lib/api'
import { Link } from 'react-router-dom'
import { BookOpen, MessageCircle, Flame, Star, Zap } from 'lucide-react'
import { motion } from 'framer-motion'

const games = [
  {
    to: '/practice/flashcard',
    label: 'Tarjetas',
    desc: 'Repaso con repetición espaciada',
    icon: '🃏',
    color:
      'bg-sky-50 dark:bg-sky-950 text-sky-700 dark:text-sky-300 border-sky-100 dark:border-sky-900',
  },
  {
    to: '/practice/listen-choose',
    label: 'Escuchar',
    desc: 'Escucha y elige la palabra',
    icon: '🎧',
    color:
      'bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border-purple-100 dark:border-purple-900',
  },
  {
    to: '/practice/word-match',
    label: 'Emparejar',
    desc: 'Une palabras con su traducción',
    icon: '🔗',
    color:
      'bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300 border-brand-100 dark:border-brand-900',
  },
  {
    to: '/practice/multiple-choice',
    label: 'Test',
    desc: 'Elige la respuesta correcta',
    icon: '❓',
    color:
      'bg-yellow-50 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300 border-yellow-100 dark:border-yellow-900',
  },
  {
    to: '/practice/fill-blank',
    label: 'Rellenar',
    desc: 'Completa la frase',
    icon: '✏️',
    color:
      'bg-orange-50 dark:bg-orange-950 text-orange-700 dark:text-orange-300 border-orange-100 dark:border-orange-900',
  },
  {
    to: '/practice/unscramble',
    label: 'Ordenar',
    desc: 'Ordena las palabras',
    icon: '🔀',
    color:
      'bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 border-red-100 dark:border-red-900',
  },
  {
    to: '/practice/story',
    label: 'Historia',
    desc: 'Lee y responde preguntas',
    icon: '📖',
    color:
      'bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border-teal-100 dark:border-teal-900',
  },
]

export default function Dashboard() {
  const { data: progress } = useQuery({ queryKey: ['user-progress'], queryFn: fetchUserProgress })
  const { data: dueCards } = useQuery({ queryKey: ['due-cards'], queryFn: () => fetchDueCards(5) })
  const dueCount = dueCards?.length ?? 0

  return (
    <div className="space-y-7">
      {/* Stats row */}
      {progress && (
        <div className="grid grid-cols-3 gap-3">
          <StatCard
            icon={<Star size={18} className="text-yellow-500" />}
            value={progress.xp_total}
            label="XP"
            bg="bg-yellow-50 dark:bg-yellow-950/40"
          />
          <StatCard
            icon={<Flame size={18} className="text-orange-500" />}
            value={progress.streak_days}
            label="días"
            bg="bg-orange-50 dark:bg-orange-950/40"
          />
          <StatCard
            icon={<BookOpen size={18} className="text-sky-500" />}
            value={dueCount}
            label="hoy"
            bg="bg-sky-50 dark:bg-sky-950/40"
          />
        </div>
      )}

      {/* Due cards CTA */}
      {dueCount > 0 && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
          <Link
            to="/practice/flashcard"
            className="flex items-center justify-between rounded-2xl bg-brand-500 p-4 text-white shadow-md shadow-brand-200 transition-colors hover:bg-brand-600 dark:shadow-none"
          >
            <div>
              <div className="text-base font-semibold">
                {dueCount === 1 ? '1 tarjeta para repasar' : `${dueCount} tarjetas para repasar`}
              </div>
              <div className="mt-0.5 text-sm text-brand-100">¡Empieza ahora!</div>
            </div>
            <Zap size={24} className="flex-shrink-0 opacity-90" />
          </Link>
        </motion.div>
      )}

      {/* Game grid */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
          Juegos
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {games.map(({ to, label, desc, icon, color }) => (
            <Link
              key={to}
              to={to}
              className={`group flex flex-col rounded-2xl border p-4 text-sm font-medium transition-all hover:-translate-y-0.5 hover:shadow-md ${color}`}
            >
              <span className="mb-2 text-3xl">{icon}</span>
              <span className="font-semibold">{label}</span>
              <span className="mt-0.5 text-xs leading-snug opacity-70">{desc}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Quick links */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
          Explorar
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <Link
            to="/lesson"
            className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-4 transition-all hover:border-brand-400 hover:shadow-sm dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="rounded-xl bg-brand-50 p-2 dark:bg-brand-950">
              <BookOpen size={20} className="text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <div className="text-sm font-semibold">Lecciones</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Vocabulario y gramática
              </div>
            </div>
          </Link>
          <Link
            to="/chat"
            className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-4 transition-all hover:border-brand-400 hover:shadow-sm dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="rounded-xl bg-sky-50 p-2 dark:bg-sky-950">
              <MessageCircle size={20} className="text-sky-600 dark:text-sky-400" />
            </div>
            <div>
              <div className="text-sm font-semibold">Chat IA</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Practica conversación</div>
            </div>
          </Link>
        </div>
      </section>
    </div>
  )
}

function StatCard({
  icon,
  value,
  label,
  bg,
}: {
  icon: React.ReactNode
  value: number
  label: string
  bg: string
}) {
  return (
    <div className={`flex flex-col items-center rounded-2xl py-4 ${bg}`}>
      {icon}
      <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
    </div>
  )
}
