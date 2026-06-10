import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchVocabulary, getFeedback } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'
import SessionSummary from '@/components/SessionSummary'

const ROUND_LENGTH = 10

function fisherYatesShuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function buildQuestion(items: Array<{ dutch_word: string; spanish: string; article?: string }>) {
  if (items.length < 4) return null
  const idx = Math.floor(Math.random() * items.length)
  const correct = items[idx]
  const distractors = fisherYatesShuffle(items.filter((_, i) => i !== idx)).slice(0, 3)
  const options = fisherYatesShuffle([...distractors, correct])
  return { correct, options }
}

export default function MultipleChoiceGame() {
  const level = useAppStore((s) => s.level)
  const { data: vocab } = useQuery({
    queryKey: ['vocabulary', level],
    queryFn: () => fetchVocabulary(level),
  })

  const [selected, setSelected] = useState<number | null>(null)
  const [fbLoading, setFbLoading] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const [question, setQuestion] = useState<ReturnType<typeof buildQuestion>>(null)

  if (!question && vocab && vocab.length >= 4 && score.total < ROUND_LENGTH) {
    setQuestion(buildQuestion(vocab))
  }

  const next = () => {
    setSelected(null)
    setFeedback(null)
    setQuestion(score.total < ROUND_LENGTH && vocab ? buildQuestion(vocab) : null)
  }

  const handleSelect = async (index: number) => {
    if (selected !== null || !question) return
    setSelected(index)
    const isCorrect = question.options[index].dutch_word === question.correct.dutch_word
    setScore((s) => ({ correct: s.correct + (isCorrect ? 1 : 0), total: s.total + 1 }))
    if (!isCorrect) {
      setFbLoading(true)
      try {
        const { feedback: fb } = await getFeedback(
          `¿Cómo se dice "${question.correct.spanish}" en neerlandés?`,
          question.correct.dutch_word,
          question.options[index].dutch_word
        )
        setFeedback(fb)
      } catch {
        /* ignore */
      }
      setFbLoading(false)
    }
  }

  // Keyboard: 1–4 select an option, Enter advances
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
      if (selected === null && ['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault()
        handleSelect(Number(e.key) - 1)
      } else if (selected !== null && e.key === 'Enter') {
        e.preventDefault()
        next()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, question, score.total])

  if (!vocab || vocab.length < 4)
    return <div className="py-12 text-center text-gray-400">Cargando vocabulario…</div>

  if (score.total >= ROUND_LENGTH)
    return (
      <SessionSummary
        correct={score.correct}
        total={score.total}
        onRestart={() => {
          setScore({ correct: 0, total: 0 })
          setSelected(null)
          setFeedback(null)
          setQuestion(buildQuestion(vocab))
        }}
      />
    )

  if (!question) return null

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
        <span>
          Aciertos: {score.correct}/{score.total}
        </span>
        <span>
          Pregunta {score.total + 1} / {ROUND_LENGTH}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className="h-1.5 rounded-full bg-brand-600 transition-all"
          style={{ width: `${(score.total / ROUND_LENGTH) * 100}%` }}
        />
      </div>

      <div className="rounded-2xl border-2 border-brand-200 bg-white p-5 text-center dark:border-brand-600 dark:bg-gray-800">
        <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">
          ¿Cómo se dice en neerlandés?
        </p>
        <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">
          {question.correct.spanish}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {question.options.map((opt, i) => {
          const isCorrect = opt.dutch_word === question.correct.dutch_word
          const isSelected = selected === i
          let cls =
            'min-h-[44px] p-3 rounded-xl border-2 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2 '
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
          aria-live="polite"
        >
          {(feedback || fbLoading) && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
              {fbLoading ? 'Cargando retroalimentación…' : feedback}
            </div>
          )}
          <button
            onClick={next}
            className="mx-auto flex min-h-[44px] items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm text-white transition-colors hover:bg-brand-600 focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2"
          >
            <RefreshCw size={16} /> Siguiente
          </button>
        </motion.div>
      )}
    </div>
  )
}
