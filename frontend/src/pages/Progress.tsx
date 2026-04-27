import { useQuery } from '@tanstack/react-query'
import { fetchUserProgress, fetchDueCards, fetchXpHistory, type XpHistoryEntry } from '@/lib/api'
import { Flame, Star, BookOpen, Trophy } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Link } from 'react-router-dom'

const ACHIEVEMENT_META: Record<string, { emoji: string; title: string; subtitle: string }> = {
  first_word: { emoji: '🌱', title: 'Primera palabra', subtitle: 'Añade tu primera tarjeta' },
  ten_words: { emoji: '📚', title: 'Estudiante', subtitle: 'Añade 10 tarjetas' },
  streak_3: { emoji: '🔥', title: 'En racha', subtitle: '3 días seguidos' },
  streak_7: { emoji: '🏆', title: 'Constante', subtitle: '7 días seguidos' },
  hundred_xp: { emoji: '⭐', title: 'Primeras 100 XP', subtitle: 'Consigue 100 XP' },
  perfect_session: { emoji: '🎯', title: 'Sesión perfecta', subtitle: 'Quiz perfecto en una historia' },
  first_story: { emoji: '📖', title: 'Primer cuento', subtitle: 'Completa tu primera historia' },
  story_streak: { emoji: '🗺️', title: 'Explorador', subtitle: 'Completa 5 historias' },
}

const ALL_SLUGS = Object.keys(ACHIEVEMENT_META)

export default function Progress() {
  const { data: progress } = useQuery({ queryKey: ['user-progress'], queryFn: fetchUserProgress })
  const { data: dueCards } = useQuery({ queryKey: ['due-cards'], queryFn: () => fetchDueCards(50) })
  const { data: history } = useQuery({ queryKey: ['xp-history'], queryFn: () => fetchXpHistory(7) })

  const earnedSlugs = new Set<string>(
    (progress?.settings_json?.achievements ?? []).map((a) => a.slug)
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tu Progreso</h1>

      {/* Stats grid */}
      {progress && (
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            icon={<Star size={22} className="text-yellow-500" />}
            label="XP Total"
            value={progress.xp_total}
            bg="bg-yellow-50 dark:bg-yellow-950/40"
          />
          <StatCard
            icon={<Flame size={22} className="text-orange-500" />}
            label="Días seguidos"
            value={`${progress.streak_days} 🔥`}
            bg="bg-orange-50 dark:bg-orange-950/40"
          />
        </div>
      )}

      {/* XP chart */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <Trophy size={15} className="text-brand-500" />
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

      {/* Due cards */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <BookOpen size={15} className="text-sky-500" />
          Tarjetas pendientes hoy
        </h2>
        {dueCards?.length === 0 ? (
          <p className="text-sm text-brand-600 dark:text-brand-400">
            ✓ ¡Todo al día! Vuelve mañana.
          </p>
        ) : (
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {dueCards?.length} tarjetas para repasar
            </p>
            <Link
              to="/practice/flashcard"
              className="rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-600"
            >
              Practicar
            </Link>
          </div>
        )}
      </section>

      {/* Achievements */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Trophy size={15} className="text-yellow-500" />
          Logros
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {ALL_SLUGS.map((slug) => {
            const meta = ACHIEVEMENT_META[slug]
            const earned = earnedSlugs.has(slug)
            return (
              <div
                key={slug}
                className={`flex flex-col items-center rounded-2xl border p-4 text-center transition-all ${
                  earned
                    ? 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950/40'
                    : 'border-gray-200 bg-gray-50 opacity-40 dark:border-gray-700 dark:bg-gray-800/60'
                }`}
              >
                <span className="mb-1 text-3xl">{meta.emoji}</span>
                <span className="text-xs font-semibold leading-tight text-gray-800 dark:text-gray-200">
                  {meta.title}
                </span>
                <span className="mt-0.5 text-[10px] leading-snug text-gray-500 dark:text-gray-400">
                  {meta.subtitle}
                </span>
              </div>
            )
          })}
        </div>
      </section>
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
