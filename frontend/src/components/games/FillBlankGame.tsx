import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchFillBlank, getFeedback } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

export default function FillBlankGame() {
  const level = useAppStore((s) => s.level)
  const [selected, setSelected] = useState<number | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [fbLoading, setFbLoading] = useState(false)
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const [fetchKey, setFetchKey] = useState(0)

  const {
    data: exercise,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['fill-blank', level, fetchKey],
    queryFn: () => fetchFillBlank(level),
  })

  const next = () => {
    setSelected(null)
    setFeedback(null)
    setFetchKey((k) => k + 1)
  }

  const handleSelect = async (optionIndex: number) => {
    if (selected !== null || !exercise) return
    setSelected(optionIndex)
    const chosenWord = exercise.options[optionIndex].dutch_word
    const isCorrect = chosenWord === exercise.correct_word
    setScore((s) => ({ correct: s.correct + (isCorrect ? 1 : 0), total: s.total + 1 }))
    if (!isCorrect) {
      setFbLoading(true)
      try {
        const { feedback: fb } = await getFeedback(
          `Completa: "${exercise.sentence_with_blank}"`,
          exercise.correct_word,
          chosenWord
        )
        setFeedback(fb)
      } catch {
        /* ignore */
      }
      setFbLoading(false)
    }
  }

  if (isLoading)
    return (
      <div className="py-12 text-center text-gray-400 dark:text-gray-500">Cargando ejercicio…</div>
    )
  if (isError || !exercise || 'error' in (exercise as object))
    return (
      <div className="py-12 text-center text-yellow-600 dark:text-yellow-400">
        No hay suficientes oraciones de ejemplo para este nivel. Añade vocabulario con oraciones de
        ejemplo primero.
      </div>
    )

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
        <span>
          Aciertos: {score.correct}/{score.total}
        </span>
      </div>

      {/* Sentence with blank */}
      <div className="space-y-2 rounded-2xl border-2 border-brand-200 bg-white p-5 text-center dark:border-brand-600 dark:bg-gray-800">
        <p className="text-sm text-gray-500 dark:text-gray-400">Elige la palabra correcta:</p>
        <p className="text-xl font-semibold leading-relaxed text-gray-800 dark:text-gray-200">
          {exercise.sentence_with_blank}
        </p>
        {exercise.sentence_es && (
          <p className="text-sm italic text-gray-400 dark:text-gray-500">
            {exercise.sentence_es.replace(exercise.correct_word, '___')}
          </p>
        )}
      </div>

      {/* Options */}
      <div className="grid grid-cols-2 gap-3">
        {exercise.options.map((opt, i) => {
          const isCorrect = opt.dutch_word === exercise.correct_word
          const isSelected = selected === i
          let cls = 'p-3 rounded-xl border-2 text-sm font-medium transition-colors '
          if (selected !== null) {
            cls += isCorrect
              ? 'border-green-500 bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
              : isSelected
                ? 'border-red-400 bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-300'
                : 'border-gray-100 dark:border-gray-700 text-gray-400 dark:text-gray-600'
          } else {
            cls +=
              'border-gray-200 dark:border-gray-600 hover:border-brand-400 hover:bg-brand-50 dark:hover:border-brand-400 dark:hover:bg-brand-950 text-gray-800 dark:text-gray-200 cursor-pointer'
          }
          return (
            <motion.button
              key={i}
              whileTap={{ scale: 0.97 }}
              className={cls}
              onClick={() => handleSelect(i)}
            >
              {opt.article ? `${opt.article} ` : ''}
              {opt.dutch_word}
            </motion.button>
          )
        })}
      </div>

      {selected !== null && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3"
        >
          {fbLoading && (
            <div className="animate-pulse rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-600 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400">
              Cargando retroalimentación…
            </div>
          )}
          {feedback && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
              {feedback}
            </div>
          )}
          {exercise.options[selected]?.dutch_word === exercise.correct_word && (
            <div className="rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
              ✅ ¡Correcto!
            </div>
          )}
          <button
            onClick={next}
            className="mx-auto flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm text-white transition-colors hover:bg-brand-600"
          >
            <RefreshCw size={16} /> Siguiente
          </button>
        </motion.div>
      )}
    </div>
  )
}
