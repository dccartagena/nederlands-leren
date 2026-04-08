import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchVocabulary, getFeedback } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

function buildQuestion(items: Array<{ dutch_word: string; spanish: string; article?: string }>) {
  if (items.length < 4) return null
  const idx = Math.floor(Math.random() * items.length)
  const correct = items[idx]
  const distractors = items.filter((_, i) => i !== idx).sort(() => Math.random() - 0.5).slice(0, 3)
  const options = [...distractors, correct].sort(() => Math.random() - 0.5)
  return { correct, options }
}

export default function MultipleChoiceGame() {
  const level = useAppStore(s => s.level)
  const { data: vocab } = useQuery({ queryKey: ['vocabulary', level], queryFn: () => fetchVocabulary(level) })

  const [selected, setSelected] = useState<number | null>(null)
  const [fbLoading, setFbLoading] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const [question, setQuestion] = useState<ReturnType<typeof buildQuestion>>(null)

  if (!question && vocab && vocab.length >= 4) {
    setQuestion(buildQuestion(vocab))
  }

  const next = () => {
    setSelected(null)
    setFeedback(null)
    if (vocab) setQuestion(buildQuestion(vocab))
  }

  const handleSelect = async (index: number) => {
    if (selected !== null || !question) return
    setSelected(index)
    const isCorrect = question.options[index].dutch_word === question.correct.dutch_word
    setScore(s => ({ correct: s.correct + (isCorrect ? 1 : 0), total: s.total + 1 }))
    if (!isCorrect) {
      setFbLoading(true)
      try {
        const { feedback: fb } = await getFeedback(
          `¿Cómo se dice "${question.correct.spanish}" en neerlandés?`,
          question.correct.dutch_word,
          question.options[index].dutch_word,
        )
        setFeedback(fb)
      } catch { /* ignore */ }
      setFbLoading(false)
    }
  }

  if (!vocab || vocab.length < 4) return <div className="text-gray-400 text-center py-12">Cargando vocabulario…</div>
  if (!question) return null

  return (
    <div className="space-y-5 max-w-md mx-auto">
      <div className="flex justify-between text-sm text-gray-500">
        <span>Aciertos: {score.correct}/{score.total}</span>
      </div>

      <div className="p-5 rounded-2xl bg-white border-2 border-dutch-200 text-center">
        <p className="text-sm text-gray-500 mb-1">¿Cómo se dice en neerlandés?</p>
        <p className="text-2xl font-bold text-gray-800">{question.correct.spanish}</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {question.options.map((opt, i) => {
          const isCorrect = opt.dutch_word === question.correct.dutch_word
          const isSelected = selected === i
          let cls = 'p-3 rounded-xl border-2 text-sm font-medium transition-colors '
          if (selected !== null) {
            cls += isCorrect ? 'border-green-500 bg-green-50 text-green-700' :
              isSelected ? 'border-red-400 bg-red-50 text-red-600' : 'border-gray-100 text-gray-400'
          } else {
            cls += 'border-gray-200 hover:border-dutch-400 hover:bg-dutch-50 text-gray-800 cursor-pointer'
          }
          return (
            <motion.button key={i} whileTap={{ scale: 0.97 }} className={cls} onClick={() => handleSelect(i)}>
              {opt.article ? `${opt.article} ` : ''}{opt.dutch_word}
            </motion.button>
          )
        })}
      </div>

      {selected !== null && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
          {feedback && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-800">
              {fbLoading ? 'Cargando retroalimentación…' : feedback}
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
