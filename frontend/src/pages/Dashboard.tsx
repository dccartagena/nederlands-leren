import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchUserProgress,
  fetchDueCards,
  fetchXpHistory,
  fetchMasteryStats,
  fetchQuests,
  type Quest,
} from '@/lib/api'
import { Link } from 'react-router-dom'
import { BookOpen, MessageCircle, Flame, Star, Zap, Brain, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/stores/appStore'

const DAILY_GOAL_XP = 50

const XP_LEVELS = [
  { level: 1, name: 'Principiante', threshold: 0 },
  { level: 2, name: 'Básico', threshold: 100 },
  { level: 3, name: 'Elemental', threshold: 300 },
  { level: 4, name: 'Intermedio', threshold: 600 },
  { level: 5, name: 'Avanzado', threshold: 1000 },
  { level: 6, name: 'Experto', threshold: 2000 },
  { level: 7, name: 'Maestro', threshold: 3500 },
]

function getLevelInfo(xp: number) {
  let idx = XP_LEVELS.length - 1
  for (let i = XP_LEVELS.length - 1; i >= 0; i--) {
    if (xp >= XP_LEVELS[i].threshold) {
      idx = i
      break
    }
  }
  const current = XP_LEVELS[idx]
  const next = XP_LEVELS[idx + 1]
  const pct = next
    ? Math.min(1, (xp - current.threshold) / (next.threshold - current.threshold))
    : 1
  return { current, next, pct }
}

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
  {
    to: '/practice/dictado',
    label: 'Dictado',
    desc: 'Escucha y escribe la palabra',
    icon: '🎙️',
    color:
      'bg-pink-50 dark:bg-pink-950 text-pink-700 dark:text-pink-300 border-pink-100 dark:border-pink-900',
  },
]

export default function Dashboard() {
  const sereneMode = useAppStore((s) => s.sereneMode)
  const { data: progress } = useQuery({ queryKey: ['user-progress'], queryFn: fetchUserProgress })
  const { data: dueCards } = useQuery({ queryKey: ['due-cards'], queryFn: () => fetchDueCards(5) })
  const { data: stats } = useQuery({ queryKey: ['mastery-stats'], queryFn: fetchMasteryStats })
  const { data: quests } = useQuery({ queryKey: ['quests'], queryFn: fetchQuests })
  const { data: todayHistory } = useQuery({
    queryKey: ['xp-history-today'],
    queryFn: () => fetchXpHistory(1),
  })

  const dueCount = dueCards?.length ?? 0
  const todayXp = todayHistory?.[0]?.xp ?? 0

  return (
    <div className="space-y-7">
      {/* Mastery headline: real ability first, XP secondary */}
      {stats && (
        <div className="flex items-center gap-4 rounded-2xl border border-brand-200 bg-brand-50 p-4 dark:border-brand-800 dark:bg-brand-950/40">
          <div className="rounded-xl bg-white p-2.5 dark:bg-gray-800">
            <Brain size={24} className="text-brand-700 dark:text-brand-400" />
          </div>
          <div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
              Dominas {stats.mastered_words} {stats.mastered_words === 1 ? 'palabra' : 'palabras'}
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              {stats.enrolled_words} en tu mazo · {stats.stories_completed} historias completadas
            </div>
          </div>
        </div>
      )}

      {/* Stats row */}
      {progress && (
        <div className="grid grid-cols-3 gap-3">
          {!sereneMode ? (
            <StatCard
              icon={<Star size={18} className="text-yellow-500" />}
              value={progress.xp_total}
              label="XP"
              bg="bg-yellow-50 dark:bg-yellow-950/40"
            />
          ) : (
            <StatCard
              icon={<Brain size={18} className="text-brand-700 dark:text-brand-400" />}
              value={stats?.mastered_words ?? 0}
              label="dominadas"
              bg="bg-brand-50 dark:bg-brand-950/40"
            />
          )}
          <StatCard
            icon={<Flame size={18} className="text-orange-500" />}
            value={progress.streak_days}
            label="días"
            bg="bg-orange-50 dark:bg-orange-950/40"
            badge={stats && stats.streak_freezes > 0 ? '🧊' : undefined}
            badgeTitle="Protector de racha disponible"
          />
          <StatCard
            icon={<BookOpen size={18} className="text-sky-500" />}
            value={dueCount}
            label="hoy"
            bg="bg-sky-50 dark:bg-sky-950/40"
          />
        </div>
      )}

      {/* Level + daily goal card (XP-based — hidden in modo sereno) */}
      {progress && !sereneMode && <LevelCard xp={progress.xp_total} todayXp={todayXp} />}

      {/* Optional daily quests */}
      {quests && quests.length > 0 && <QuestsCard quests={quests} />}

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

function LevelCard({ xp, todayXp }: { xp: number; todayXp: number }) {
  const { current, next, pct } = getLevelInfo(xp)
  const dailyPct = Math.min(1, todayXp / DAILY_GOAL_XP)
  const dailyDone = todayXp >= DAILY_GOAL_XP

  return (
    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      {/* XP level */}
      <div>
        <div className="mb-1.5 flex items-center justify-between">
          <div>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Nivel {current.level} ·{' '}
            </span>
            <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
              {current.name}
            </span>
          </div>
          {next && <span className="text-xs text-gray-400 dark:text-gray-500">→ {next.name}</span>}
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <motion.div
            className="h-2 rounded-full bg-brand-500"
            initial={{ width: 0 }}
            animate={{ width: `${pct * 100}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>
        {next && (
          <div className="mt-1 text-right text-xs text-gray-400 dark:text-gray-500">
            {xp} / {next.threshold} XP
          </div>
        )}
      </div>

      {/* Daily goal */}
      <div>
        <div className="mb-1.5 flex items-center justify-between text-xs">
          <span className="text-gray-500 dark:text-gray-400">Meta diaria</span>
          <span
            className={
              dailyDone
                ? 'font-semibold text-green-600 dark:text-green-400'
                : 'text-gray-500 dark:text-gray-400'
            }
          >
            {dailyDone ? '✓ ¡Meta cumplida!' : `${todayXp} / ${DAILY_GOAL_XP} XP`}
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <motion.div
            className={`h-1.5 rounded-full ${dailyDone ? 'bg-green-500' : 'bg-yellow-400'}`}
            initial={{ width: 0 }}
            animate={{ width: `${dailyPct * 100}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon,
  value,
  label,
  bg,
  badge,
  badgeTitle,
}: {
  icon: React.ReactNode
  value: number
  label: string
  bg: string
  badge?: string
  badgeTitle?: string
}) {
  return (
    <div className={`relative flex flex-col items-center rounded-2xl py-4 ${bg}`}>
      {badge && (
        <span className="absolute right-2 top-2 text-sm" title={badgeTitle} aria-label={badgeTitle}>
          {badge}
        </span>
      )}
      {icon}
      <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
    </div>
  )
}

const questsSkipKey = () => `nl-quests-skipped:${new Date().toISOString().slice(0, 10)}`

function loadSkippedQuests(): string[] {
  try {
    return JSON.parse(localStorage.getItem(questsSkipKey()) ?? '[]')
  } catch {
    return []
  }
}

function QuestsCard({ quests }: { quests: Quest[] }) {
  const [skipped, setSkipped] = useState<string[]>(loadSkippedQuests)

  const skip = (id: string) => {
    const next = [...skipped, id]
    setSkipped(next)
    localStorage.setItem(questsSkipKey(), JSON.stringify(next))
  }

  const visible = quests.filter((q) => !skipped.includes(q.id))
  if (visible.length === 0) return null

  return (
    <section>
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
        Misiones de hoy <span className="normal-case">(opcionales)</span>
      </h2>
      <div className="space-y-2">
        {visible.map((q) => (
          <div
            key={q.id}
            className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
          >
            <span className="text-lg" aria-hidden>
              {q.done ? '✅' : '🎯'}
            </span>
            <div className="min-w-0 flex-1">
              <div
                className={`text-sm font-medium ${q.done ? 'text-gray-400 line-through dark:text-gray-500' : ''}`}
              >
                {q.title_es}
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700">
                <div
                  className={`h-1.5 rounded-full transition-all ${q.done ? 'bg-brand-500' : 'bg-yellow-400'}`}
                  style={{ width: `${Math.min(100, (q.progress / q.target) * 100)}%` }}
                />
              </div>
            </div>
            <span className="text-xs tabular-nums text-gray-500 dark:text-gray-400">
              {q.progress}/{q.target}
            </span>
            {!q.done && (
              <button
                onClick={() => skip(q.id)}
                aria-label={`Saltar misión: ${q.title_es}`}
                title="Saltar (sin penalización)"
                className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 focus-visible:ring-2 focus-visible:ring-brand-700 dark:hover:bg-gray-700 dark:hover:text-gray-300"
              >
                <X size={14} />
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
