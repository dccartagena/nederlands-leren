import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchUserProgress,
  fetchDueCards,
  fetchXpHistory,
  fetchMasteryStats,
  type XpHistoryEntry,
  type MasteryStats,
  type UserProgress,
} from '@/lib/api'
import { Flame, Star, BookOpen, Trophy, Brain, CalendarDays } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Link } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'

interface AchievementMeta {
  emoji: string
  title: string
  subtitle: string
  /** Current progress toward the goal, for the visible tiered map */
  progress?: (p: UserProgress, s?: MasteryStats) => { current: number; target: number }
}

const storiesDone = (p: UserProgress) => p.settings_json?.completed_stories?.length ?? 0

// Tiered, visible, explained achievement map (B2): every badge names the
// skill it tracks and shows progress toward it.
const ACHIEVEMENT_GROUPS: Array<{ label: string; items: Record<string, AchievementMeta> }> = [
  {
    label: 'Palabras dominadas',
    items: {
      mastered_10: {
        emoji: '🌿',
        title: 'Brote',
        subtitle: 'Domina 10 palabras (memoria > 21 días)',
        progress: (_p, s) => ({ current: s?.mastered_words ?? 0, target: 10 }),
      },
      mastered_50: {
        emoji: '🌳',
        title: 'Árbol joven',
        subtitle: 'Domina 50 palabras',
        progress: (_p, s) => ({ current: s?.mastered_words ?? 0, target: 50 }),
      },
      mastered_150: {
        emoji: '🌲',
        title: 'Bosque',
        subtitle: 'Domina 150 palabras',
        progress: (_p, s) => ({ current: s?.mastered_words ?? 0, target: 150 }),
      },
      mastered_300: {
        emoji: '🏞️',
        title: 'Nivel A1 a la vista',
        subtitle: 'Domina 300 palabras',
        progress: (_p, s) => ({ current: s?.mastered_words ?? 0, target: 300 }),
      },
    },
  },
  {
    label: 'Constancia',
    items: {
      streak_3: {
        emoji: '🔥',
        title: 'En racha',
        subtitle: '3 días seguidos',
        progress: (p) => ({ current: p.streak_days, target: 3 }),
      },
      streak_7: {
        emoji: '🏆',
        title: 'Constante',
        subtitle: '7 días seguidos',
        progress: (p) => ({ current: p.streak_days, target: 7 }),
      },
      streak_30: {
        emoji: '🌙',
        title: 'Un mes entero',
        subtitle: '30 días seguidos',
        progress: (p) => ({ current: p.streak_days, target: 30 }),
      },
      streak_100: {
        emoji: '💯',
        title: 'Centenario',
        subtitle: '100 días seguidos',
        progress: (p) => ({ current: p.streak_days, target: 100 }),
      },
    },
  },
  {
    label: 'Historias',
    items: {
      first_story: {
        emoji: '📖',
        title: 'Primer cuento',
        subtitle: 'Completa tu primera historia',
        progress: (p) => ({ current: storiesDone(p), target: 1 }),
      },
      story_streak: {
        emoji: '🗺️',
        title: 'Explorador',
        subtitle: 'Completa 5 historias',
        progress: (p) => ({ current: storiesDone(p), target: 5 }),
      },
      stories_15: {
        emoji: '🧭',
        title: 'Viajero',
        subtitle: 'Completa 15 historias',
        progress: (p) => ({ current: storiesDone(p), target: 15 }),
      },
      stories_40: {
        emoji: '🌍',
        title: 'Trotamundos',
        subtitle: 'Completa 40 historias',
        progress: (p) => ({ current: storiesDone(p), target: 40 }),
      },
    },
  },
  {
    label: 'Primeros pasos',
    items: {
      first_word: { emoji: '🌱', title: 'Primera palabra', subtitle: 'Añade tu primera tarjeta' },
      ten_words: { emoji: '📚', title: 'Estudiante', subtitle: 'Añade 10 tarjetas' },
      hundred_xp: { emoji: '⭐', title: 'Primeras 100 XP', subtitle: 'Consigue 100 XP' },
      perfect_session: {
        emoji: '🎯',
        title: 'Sesión perfecta',
        subtitle: 'Quiz perfecto en una historia',
      },
    },
  },
]

export default function Progress() {
  const sereneMode = useAppStore((s) => s.sereneMode)
  const { data: progress } = useQuery({ queryKey: ['user-progress'], queryFn: fetchUserProgress })
  const { data: stats } = useQuery({ queryKey: ['mastery-stats'], queryFn: fetchMasteryStats })
  const { data: dueCards } = useQuery({ queryKey: ['due-cards'], queryFn: () => fetchDueCards(50) })
  const { data: history } = useQuery({ queryKey: ['xp-history'], queryFn: () => fetchXpHistory(7) })
  const { data: yearHistory } = useQuery({
    queryKey: ['xp-history-year'],
    queryFn: () => fetchXpHistory(365),
  })

  const earnedSlugs = new Set<string>(
    (progress?.settings_json?.achievements ?? []).map((a) => a.slug)
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tu Progreso</h1>

      {/* Stats grid: mastery first, XP secondary */}
      {progress && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard
            icon={<Brain size={22} className="text-brand-700 dark:text-brand-400" />}
            label="Dominadas"
            value={stats?.mastered_words ?? 0}
            bg="bg-brand-50 dark:bg-brand-950/40"
          />
          <StatCard
            icon={<Flame size={22} className="text-orange-500" />}
            label="Días seguidos"
            value={`${progress.streak_days}${stats && stats.streak_freezes > 0 ? ' 🧊' : ''}`}
            bg="bg-orange-50 dark:bg-orange-950/40"
          />
          <StatCard
            icon={<BookOpen size={22} className="text-teal-600" />}
            label="Historias"
            value={stats?.stories_completed ?? 0}
            bg="bg-teal-50 dark:bg-teal-950/40"
          />
          {!sereneMode && (
            <StatCard
              icon={<Star size={22} className="text-yellow-500" />}
              label="XP Total"
              value={progress.xp_total}
              bg="bg-yellow-50 dark:bg-yellow-950/40"
            />
          )}
        </div>
      )}

      {/* Activity heatmap (last 12 months) */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <CalendarDays size={15} className="text-brand-700 dark:text-brand-400" />
          Calendario de actividad
        </h2>
        {yearHistory && yearHistory.length > 0 ? (
          <ActivityHeatmap data={yearHistory} />
        ) : (
          <div className="flex h-24 items-center justify-center text-sm text-gray-400 dark:text-gray-500">
            Aún no hay actividad registrada
          </div>
        )}
      </section>

      {/* XP chart */}
      {!sereneMode && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Trophy size={15} className="text-brand-700 dark:text-brand-400" />
            XP esta semana
          </h2>
          {history && history.length > 0 ? (
            <XpBarChart data={history} />
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-gray-400 dark:text-gray-500">
              Aún no hay datos de esta semana
            </div>
          )}
        </section>
      )}

      {/* Due cards */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <BookOpen size={15} className="text-sky-500" />
          Tarjetas pendientes hoy
        </h2>
        {dueCards?.length === 0 ? (
          <p className="text-sm text-brand-700 dark:text-brand-400">
            ✓ ¡Todo al día! Vuelve mañana.
          </p>
        ) : (
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {dueCards?.length} tarjetas para repasar
            </p>
            <Link
              to="/practice/flashcard"
              className="min-h-[44px] rounded-lg bg-brand-500 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-600 focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2"
            >
              Practicar
            </Link>
          </div>
        )}
      </section>

      {/* Tiered achievement map */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Trophy size={15} className="text-yellow-500" />
          Logros
        </h2>
        <div className="space-y-5">
          {ACHIEVEMENT_GROUPS.map((group) => (
            <div key={group.label}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                {group.label}
              </h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Object.entries(group.items).map(([slug, meta]) => {
                  const earned = earnedSlugs.has(slug)
                  const prog =
                    !earned && progress && meta.progress
                      ? meta.progress(progress, stats)
                      : undefined
                  return (
                    <div
                      key={slug}
                      className={`flex flex-col items-center rounded-2xl border p-4 text-center transition-all ${
                        earned
                          ? 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950/40'
                          : 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/60'
                      }`}
                    >
                      <span className={`mb-1 text-3xl ${earned ? '' : 'opacity-40 grayscale'}`}>
                        {meta.emoji}
                      </span>
                      <span className="text-xs font-semibold leading-tight text-gray-800 dark:text-gray-200">
                        {meta.title}
                      </span>
                      <span className="mt-0.5 text-[10px] leading-snug text-gray-500 dark:text-gray-400">
                        {meta.subtitle}
                      </span>
                      {prog && (
                        <>
                          <div className="mt-2 h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                            <div
                              className="h-1.5 rounded-full bg-brand-500 transition-all"
                              style={{
                                width: `${Math.min(100, (prog.current / prog.target) * 100)}%`,
                              }}
                            />
                          </div>
                          <span className="mt-1 text-[10px] tabular-nums text-gray-400 dark:text-gray-500">
                            {Math.min(prog.current, prog.target)} / {prog.target}
                          </span>
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function heatColor(xp: number): string {
  if (xp <= 0) return 'bg-gray-200 dark:bg-gray-700'
  if (xp < 20) return 'bg-brand-200'
  if (xp < 50) return 'bg-brand-400'
  return 'bg-brand-600'
}

function ActivityHeatmap({ data }: { data: XpHistoryEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Group days into columns of 7 (weeks), padding the first column so
  // weekdays align: row 0 = Monday.
  const firstDay = new Date(data[0].date + 'T12:00:00')
  const padding = (firstDay.getDay() + 6) % 7 // JS Sunday=0 → Monday-first index
  const cells: Array<XpHistoryEntry | null> = [...Array(padding).fill(null), ...data]
  const weeks: Array<Array<XpHistoryEntry | null>> = []
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7))
  }

  // Show the most recent weeks first on small screens
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollLeft = el.scrollWidth
  }, [data])

  return (
    <div ref={scrollRef} className="overflow-x-auto pb-1">
      <div className="flex gap-[3px]" role="img" aria-label="Actividad diaria del último año">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-[3px]">
            {week.map((day, di) =>
              day ? (
                <div
                  key={day.date}
                  className={`h-2.5 w-2.5 rounded-[3px] ${heatColor(day.xp)}`}
                  title={`${new Date(day.date + 'T12:00:00').toLocaleDateString('es', {
                    dateStyle: 'medium',
                  })}: ${day.xp} XP`}
                />
              ) : (
                <div key={`pad-${di}`} className="h-2.5 w-2.5" />
              )
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function XpBarChart({ data }: { data: XpHistoryEntry[] }) {
  const maxXp = Math.max(...data.map((d) => d.xp), 1)
  return (
    <ResponsiveContainer width="100%" height={140}>
      <BarChart data={data} barCategoryGap="30%">
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: 'currentColor' }}
          tickFormatter={(d) =>
            new Date(d + 'T12:00:00').toLocaleDateString('es', { weekday: 'short' })
          }
          axisLine={false}
          tickLine={false}
          className="text-gray-400 dark:text-gray-500"
        />
        <YAxis hide domain={[0, maxXp * 1.2]} />
        <Tooltip
          formatter={(v) => [`${v ?? 0} XP`, '']}
          labelFormatter={(d) =>
            new Date(d + 'T12:00:00').toLocaleDateString('es', { dateStyle: 'medium' })
          }
          contentStyle={{
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            fontSize: '12px',
            padding: '6px 10px',
          }}
          cursor={{ fill: 'rgba(0,0,0,0.04)' }}
        />
        <Bar dataKey="xp" radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.date} fill={entry.xp > 0 ? '#58CC02' : '#e5e7eb'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function StatCard({
  icon,
  label,
  value,
  bg,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  bg: string
}) {
  return (
    <div className={`flex flex-col items-center rounded-2xl py-5 ${bg}`}>
      {icon}
      <div className="mt-1 text-2xl font-bold">{value}</div>
      <div className="text-sm text-gray-500 dark:text-gray-400">{label}</div>
    </div>
  )
}
