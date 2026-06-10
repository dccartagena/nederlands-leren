import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchVocabulary } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { Volume2, RefreshCw } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function DictadoGame() {
  const level = useAppStore((s) => s.level)
  const audioEnabled = useAppStore((s) => s.audioEnabled)

  const [shuffled, setShuffled] = useState<ReturnType<typeof useVocab>['data']>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [input, setInput] = useState('')
  const [result, setResult] = useState<'correct' | 'wrong' | null>(null)
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const [xpGained, setXpGained] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: vocabulary, isLoading } = useVocab(level)

  // Shuffle once when vocabulary loads
  useEffect(() => {
    if (vocabulary?.length) {
      setShuffled([...vocabulary].sort(() => Math.random() - 0.5))
      setCurrentIdx(0)
    }
  }, [vocabulary])

  const currentWord = shuffled?.[currentIdx % (shuffled?.length || 1)]

  const playAudio = () => {
    if (!currentWord || !audioEnabled) return
    const path = `/audio/gtts_${currentWord.dutch_word}_${currentWord.level}.wav`
    const audio = new Audio(path)
    audio.play().catch(() => {})
  }

  // Auto-play when a new word appears
  useEffect(() => {
    if (!currentWord) return
    const t = setTimeout(playAudio, 200)
    return () => clearTimeout(t)
  }, [currentWord?.dutch_word])

  const handleSubmit = () => {
    if (!currentWord || !input.trim() || result !== null) return
    const userInput = input.trim().toLowerCase()
    const correctWord = currentWord.dutch_word.toLowerCase()
    const correctWithArticle = currentWord.article
      ? `${currentWord.article} ${currentWord.dutch_word}`.toLowerCase()
      : correctWord
    const isCorrect = userInput === correctWord || userInput === correctWithArticle
    setResult(isCorrect ? 'correct' : 'wrong')
    setScore((s) => ({ correct: s.correct + (isCorrect ? 1 : 0), total: s.total + 1 }))
    if (isCorrect) setXpGained((x) => x + 8)
  }

  const next = () => {
    setInput('')
    setResult(null)
    setCurrentIdx((i) => i + 1)
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  if (isLoading || !shuffled?.length)
    return (
      <div className="py-12 text-center text-gray-400 dark:text-gray-500">
        Cargando vocabulario…
      </div>
    )

  if (!currentWord)
    return (
      <div className="py-12 text-center text-gray-400 dark:text-gray-500">
        No hay palabras disponibles.
      </div>
    )

  return (
    <div className="mx-auto flex max-w-sm flex-col items-center gap-6">
      {/* Score bar */}
      <div className="flex w-full justify-between text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          {score.correct} / {score.total} correctas
        </span>
        <span className="font-semibold text-yellow-600 dark:text-yellow-400">+{xpGained} XP</span>
      </div>

      <p className="text-center text-sm text-gray-600 dark:text-gray-400">
        Escucha la palabra y escríbela en neerlandés
      </p>

      {/* Audio play button */}
      <button
        onClick={playAudio}
        className="flex h-24 w-24 flex-col items-center justify-center gap-1.5 rounded-full bg-brand-100 text-sm font-medium text-brand-600 transition-colors hover:bg-brand-200 dark:bg-brand-900 dark:text-brand-300 dark:hover:bg-brand-700"
      >
        <Volume2 size={32} />
        Escuchar
      </button>

      {/* Text input */}
      <div className="w-full space-y-3">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          disabled={result !== null}
          placeholder="Escribe la palabra…"
          className="w-full rounded-xl border-2 border-gray-200 bg-white px-4 py-3 text-center text-lg font-medium outline-none transition-colors focus:border-brand-400 disabled:text-gray-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-brand-400"
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
        />
        {result === null && (
          <button
            onClick={handleSubmit}
            disabled={!input.trim()}
            className="w-full rounded-xl bg-brand-500 py-3 font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-40"
          >
            Comprobar
          </button>
        )}
      </div>

      {/* Result feedback */}
      <AnimatePresence>
        {result !== null && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="w-full space-y-3 text-center"
          >
            {result === 'correct' ? (
              <div className="text-lg font-semibold text-green-600 dark:text-green-400">
                ✓ ¡Correcto!
              </div>
            ) : (
              <div className="space-y-1">
                <div className="text-lg font-semibold text-red-600 dark:text-red-400">
                  ✗ Incorrecto
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Respuesta:{' '}
                  <strong>
                    {currentWord.article ? `${currentWord.article} ` : ''}
                    {currentWord.dutch_word}
                  </strong>{' '}
                  ({currentWord.spanish})
                </div>
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
      </AnimatePresence>
    </div>
  )
}

function useVocab(level: string) {
  return useQuery({
    queryKey: ['vocabulary-dictado', level],
    queryFn: () => fetchVocabulary(level, undefined, 200),
  })
}
