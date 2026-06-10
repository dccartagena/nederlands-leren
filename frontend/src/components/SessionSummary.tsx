import { motion } from 'framer-motion'
import { useAppStore } from '@/stores/appStore'

interface SessionSummaryProps {
  correct: number
  total: number
  xpGained?: number
  /** Cards that moved up an FSRS state during the session */
  promotions?: number
  maxCombo?: number
  onRestart: () => void
  restartLabel?: string
}

export default function SessionSummary({
  correct,
  total,
  xpGained = 0,
  promotions,
  maxCombo,
  onRestart,
  restartLabel = 'Otra ronda',
}: SessionSummaryProps) {
  const sereneMode = useAppStore((s) => s.sereneMode)
  const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="mx-auto max-w-md space-y-5 py-8 text-center"
      aria-live="polite"
    >
      <div className="text-5xl">{accuracy >= 80 ? '🎉' : '💪'}</div>
      <h2 className="text-xl font-bold">¡Sesión completada!</h2>

      <div className="grid grid-cols-2 gap-3">
        <SummaryStat label="Aciertos" value={`${correct} / ${total}`} />
        <SummaryStat label="Precisión" value={`${accuracy}%`} />
        {!sereneMode && xpGained > 0 && <SummaryStat label="XP ganados" value={`+${xpGained}`} />}
        {promotions !== undefined && promotions > 0 && (
          <SummaryStat label="Palabras que avanzaron" value={`↑ ${promotions}`} />
        )}
        {!sereneMode && maxCombo !== undefined && maxCombo >= 5 && (
          <SummaryStat label="Mejor combo" value={`🔥 ${maxCombo}`} />
        )}
      </div>

      {accuracy < 70 && total >= 5 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Hoy estuvo difícil — prueba un repaso más corto o un juego más sencillo mañana.
        </p>
      )}

      <button
        onClick={onRestart}
        className="min-h-[44px] rounded-xl bg-brand-500 px-6 py-2 font-medium text-white transition-colors hover:bg-brand-600 focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2"
      >
        {restartLabel}
      </button>
    </motion.div>
  )
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="text-xl font-bold tabular-nums">{value}</div>
      <div className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{label}</div>
    </div>
  )
}
