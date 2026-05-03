import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchUnscramble } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { RefreshCw, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameScore } from './hooks/useGameScore'

export default function UnscrambleGame() {
  const level = useAppStore((s) => s.level)
  const [fetchKey, setFetchKey] = useState(0)
  const [chosen, setChosen] = useState<Array<{ word: string; srcIdx: number }>>([])
  const [usedIndices, setUsedIndices] = useState<Set<number>>(new Set())
  const [result, setResult] = useState<'correct' | 'wrong' | null>(null)
  const { score, recordAnswer } = useGameScore()

  const {
    data: exercise,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['unscramble', level, fetchKey],
    queryFn: () => fetchUnscramble(level),
  })

  // Reset local state whenever a new exercise loads
  useEffect(() => {
    setChosen([])
    setUsedIndices(new Set())
    setResult(null)
  }, [exercise])

  const next = () => {
    setFetchKey((k) => k + 1)
  }

  const addWord = (word: string, idx: number) => {
    if (result !== null) return
    setChosen((c) => [...c, { word, srcIdx: idx }])
    setUsedIndices((u) => new Set([...u, idx]))
  }

  const removeWord = (chosenIdx: number) => {
    if (result !== null) return
    const { srcIdx } = chosen[chosenIdx]
    setChosen((c) => c.filter((_, i) => i !== chosenIdx))
    setUsedIndices((u) => {
      const next = new Set(u)
      next.delete(srcIdx)
      return next
    })
  }

  const checkAnswer = () => {
    if (!exercise || result !== null) return
    const attempt = chosen.map((c) => c.word).join(' ') + exercise.trailing_punct
    const isCorrect = attempt === exercise.correct_sentence
    setResult(isCorrect ? 'correct' : 'wrong')
    recordAnswer(isCorrect)
  }

  if (isLoading)
    return (
      <div className="py-12 text-center text-gray-400 dark:text-gray-500">Cargando ejercicio…</div>
    )
  if (isError || !exercise || 'error' in (exercise as object))
    return (
      <div className="py-12 text-center text-yellow-600 dark:text-yellow-400">
        No hay suficientes oraciones de ejemplo para este nivel.
      </div>
    )

  const allWordsChosen = chosen.length === exercise.shuffled_words.length

  return (
    <div className="mx-auto max-w-lg space-y-5">
      <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
        <span>
          Aciertos: {score.correct}/{score.total}
        </span>
      </div>

      {/* Instructions */}
      <div className="space-y-1 rounded-2xl border-2 border-brand-200 bg-white p-4 text-center dark:border-brand-600 dark:bg-gray-800">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Ordena las palabras para formar la oración correcta:
        </p>
        {exercise.sentence_es && (
          <p className="text-base font-medium italic text-gray-700 dark:text-gray-300">
            "{exercise.sentence_es}"
          </p>
        )}
      </div>

      {/* Answer area */}
      <div className="flex min-h-[3rem] flex-wrap gap-2 rounded-xl border-2 border-dashed border-brand-300 bg-brand-50 p-3 dark:border-brand-500 dark:bg-brand-950">
        <AnimatePresence>
          {chosen.map(({ word, srcIdx }, i) => (
            <motion.button
              key={`${srcIdx}-${i}`}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              onClick={() => removeWord(i)}
              className="flex items-center gap-1 rounded-lg bg-brand-500 px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-brand-600"
            >
              {word}
              {result === null && <X size={12} />}
            </motion.button>
          ))}
          {chosen.length === 0 && (
            <span className="self-center text-sm text-gray-400 dark:text-gray-600">
              Toca las palabras para añadirlas…
            </span>
          )}
        </AnimatePresence>
      </div>

      {/* Source words */}
      <div className="flex flex-wrap gap-2">
        {exercise.shuffled_words.map((word, i) => (
          <motion.button
            key={`src-${i}`}
            whileTap={{ scale: 0.95 }}
            onClick={() => addWord(word, i)}
            disabled={usedIndices.has(i) || result !== null}
            className={`rounded-lg border px-3 py-1 text-sm font-medium transition-colors ${
              usedIndices.has(i)
                ? 'cursor-default border-gray-200 bg-transparent text-gray-300 dark:border-gray-700 dark:text-gray-600'
                : 'cursor-pointer border-brand-300 bg-white text-gray-800 hover:bg-brand-50 dark:border-brand-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-brand-950'
            }`}
          >
            {word}
          </motion.button>
        ))}
      </div>

      {/* Check button */}
      {result === null && allWordsChosen && (
        <motion.button
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={checkAnswer}
          className="w-full rounded-xl bg-brand-500 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600"
        >
          Comprobar
        </motion.button>
      )}

      {/* Result */}
      {result !== null && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3"
        >
          {result === 'correct' ? (
            <div className="rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
              ✅ ¡Correcto!
            </div>
          ) : (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
              ❌ Incorrecto. La respuesta correcta es:{' '}
              <span className="font-semibold">{exercise.correct_sentence}</span>
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
