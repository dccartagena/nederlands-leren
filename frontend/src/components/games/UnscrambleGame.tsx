import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchUnscramble } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { RefreshCw, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function UnscrambleGame() {
  const level = useAppStore(s => s.level)
  const [fetchKey, setFetchKey] = useState(0)
  const [chosen, setChosen] = useState<string[]>([])
  const [usedIndices, setUsedIndices] = useState<Set<number>>(new Set())
  const [result, setResult] = useState<'correct' | 'wrong' | null>(null)
  const [score, setScore] = useState({ correct: 0, total: 0 })

  const { data: exercise, isLoading, isError } = useQuery({
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
    setFetchKey(k => k + 1)
  }

  const addWord = (word: string, idx: number) => {
    if (result !== null) return
    setChosen(c => [...c, word])
    setUsedIndices(u => new Set([...u, idx]))
  }

  const removeWord = (chosenIdx: number) => {
    if (result !== null) return
    // Find the first available source index that matches this word
    const word = chosen[chosenIdx]
    const sourceIdx = exercise!.shuffled_words.findIndex(
      (w, i) => w === word && !Array.from(usedIndices).slice(0, chosenIdx).includes(i) && usedIndices.has(i)
    )
    setChosen(c => c.filter((_, i) => i !== chosenIdx))
    if (sourceIdx !== -1) {
      setUsedIndices(u => {
        const next = new Set(u)
        next.delete(sourceIdx)
        return next
      })
    }
  }

  const checkAnswer = () => {
    if (!exercise || result !== null) return
    const attempt = chosen.join(' ') + exercise.trailing_punct
    const isCorrect = attempt === exercise.correct_sentence
    setResult(isCorrect ? 'correct' : 'wrong')
    setScore(s => ({ correct: s.correct + (isCorrect ? 1 : 0), total: s.total + 1 }))
  }

  if (isLoading) return <div className="text-center text-gray-400 dark:text-gray-500 py-12">Cargando ejercicio…</div>
  if (isError || !exercise || 'error' in (exercise as object))
    return <div className="text-center text-yellow-600 dark:text-yellow-400 py-12">No hay suficientes oraciones de ejemplo para este nivel.</div>

  const allWordsChosen = chosen.length === exercise.shuffled_words.length

  return (
    <div className="space-y-5 max-w-lg mx-auto">
      <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
        <span>Aciertos: {score.correct}/{score.total}</span>
      </div>

      {/* Instructions */}
      <div className="p-4 rounded-2xl bg-white dark:bg-gray-800 border-2 border-dutch-200 dark:border-dutch-800 text-center space-y-1">
        <p className="text-sm text-gray-500 dark:text-gray-400">Ordena las palabras para formar la oración correcta:</p>
        {exercise.sentence_es && (
          <p className="text-base font-medium text-gray-700 dark:text-gray-300 italic">"{exercise.sentence_es}"</p>
        )}
      </div>

      {/* Answer area */}
      <div className="min-h-[3rem] p-3 rounded-xl border-2 border-dashed border-dutch-300 dark:border-dutch-700 bg-dutch-50 dark:bg-dutch-950 flex flex-wrap gap-2">
        <AnimatePresence>
          {chosen.map((word, i) => (
            <motion.button
              key={`${word}-${i}`}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              onClick={() => removeWord(i)}
              className="flex items-center gap-1 px-3 py-1 rounded-lg bg-dutch-700 text-white text-sm font-medium hover:bg-dutch-600 transition-colors"
            >
              {word}
              {result === null && <X size={12} />}
            </motion.button>
          ))}
          {chosen.length === 0 && (
            <span className="text-sm text-gray-400 dark:text-gray-600 self-center">Toca las palabras para añadirlas…</span>
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
            className={`px-3 py-1 rounded-lg border text-sm font-medium transition-colors ${
              usedIndices.has(i)
                ? 'border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-600 bg-transparent cursor-default'
                : 'border-dutch-300 dark:border-dutch-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 hover:bg-dutch-50 dark:hover:bg-dutch-950 cursor-pointer'
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
          className="w-full py-2 rounded-xl bg-dutch-700 text-white hover:bg-dutch-600 transition-colors text-sm font-medium"
        >
          Comprobar
        </motion.button>
      )}

      {/* Result */}
      {result !== null && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
          {result === 'correct' ? (
            <div className="p-3 rounded-xl bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 text-sm text-green-700 dark:text-green-300">
              ✅ ¡Correcto!
            </div>
          ) : (
            <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
              ❌ Incorrecto. La respuesta correcta es: <span className="font-semibold">{exercise.correct_sentence}</span>
            </div>
          )}
          <button
            onClick={next}
            className="flex items-center gap-2 mx-auto px-5 py-2 rounded-xl bg-dutch-700 text-white hover:bg-dutch-600 transition-colors text-sm"
          >
            <RefreshCw size={16} /> Siguiente
          </button>
        </motion.div>
      )}
    </div>
  )
}
