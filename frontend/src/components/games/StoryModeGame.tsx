import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchStories, fetchStory } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { ChevronRight, BookOpen, RefreshCw } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

type Phase = 'list' | 'read' | 'quiz' | 'results'

export default function StoryModeGame() {
  const level = useAppStore(s => s.level)
  const [phase, setPhase] = useState<Phase>('list')
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [showSpanish, setShowSpanish] = useState(false)
  const [answers, setAnswers] = useState<(number | null)[]>([])
  const [currentQ, setCurrentQ] = useState(0)

  const { data: stories, isLoading: loadingList } = useQuery({
    queryKey: ['stories', level],
    queryFn: () => fetchStories(level),
    enabled: phase === 'list',
  })

  const { data: story, isLoading: loadingStory } = useQuery({
    queryKey: ['story', selectedSlug],
    queryFn: () => fetchStory(selectedSlug!),
    enabled: !!selectedSlug,
  })

  const startStory = (slug: string) => {
    setSelectedSlug(slug)
    setPhase('read')
    setShowSpanish(false)
    setAnswers([])
    setCurrentQ(0)
  }

  const startQuiz = () => {
    if (!story?.questions_json?.length) return
    setAnswers(new Array(story.questions_json.length).fill(null))
    setCurrentQ(0)
    setPhase('quiz')
  }

  const handleAnswer = (optionIndex: number) => {
    if (answers[currentQ] !== null) return
    const updated = [...answers]
    updated[currentQ] = optionIndex
    setAnswers(updated)
    // Auto-advance after a short delay
    setTimeout(() => {
      if (currentQ + 1 < (story?.questions_json?.length ?? 0)) {
        setCurrentQ(q => q + 1)
      } else {
        setPhase('results')
      }
    }, 900)
  }

  const restart = () => {
    setPhase('list')
    setSelectedSlug(null)
    setAnswers([])
    setCurrentQ(0)
  }

  // ── List phase ──────────────────────────────────────────────────────────────
  if (phase === 'list') {
    if (loadingList) return <div className="text-center text-gray-400 dark:text-gray-500 py-12">Cargando historias…</div>
    if (!stories?.length) return (
      <div className="text-center py-12 space-y-2">
        <div className="text-4xl">📖</div>
        <div className="font-semibold">No hay historias disponibles para el nivel {level.toUpperCase()}</div>
        <div className="text-sm text-gray-500 dark:text-gray-400">Añade historias en data/stories/ y vuelve a sembrar la base de datos.</div>
      </div>
    )
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 text-sm">
          <BookOpen size={16} />
          <span>Elige una historia para leer y practicar comprensión:</span>
        </div>
        {stories.map(s => (
          <motion.button
            key={s.slug}
            whileTap={{ scale: 0.98 }}
            onClick={() => startStory(s.slug)}
            className="w-full flex items-center justify-between p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-dutch-500 dark:hover:border-dutch-500 transition-colors text-left"
          >
            <div>
              <div className="font-semibold text-gray-800 dark:text-gray-200">{s.title_nl}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">{s.title_es}</div>
              {s.theme && <div className="text-xs text-dutch-600 dark:text-dutch-400 mt-0.5">{s.theme}</div>}
            </div>
            <ChevronRight size={18} className="text-gray-400 shrink-0" />
          </motion.button>
        ))}
      </div>
    )
  }

  // ── Read phase ──────────────────────────────────────────────────────────────
  if (phase === 'read') {
    if (loadingStory || !story) return <div className="text-center text-gray-400 dark:text-gray-500 py-12">Cargando historia…</div>
    return (
      <div className="space-y-5 max-w-lg mx-auto">
        <div className="flex items-center gap-2">
          <button onClick={restart} className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">← Historias</button>
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200">{story.title_nl}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 italic">{story.title_es}</p>
        </div>

        <div className="p-5 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 space-y-3">
          <p className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">{story.content_nl}</p>
          {story.content_es && (
            <>
              <button
                onClick={() => setShowSpanish(v => !v)}
                className="text-xs text-dutch-600 dark:text-dutch-400 underline"
              >
                {showSpanish ? 'Ocultar traducción' : 'Ver traducción al español'}
              </button>
              <AnimatePresence>
                {showSpanish && (
                  <motion.p
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed italic whitespace-pre-wrap overflow-hidden"
                  >
                    {story.content_es}
                  </motion.p>
                )}
              </AnimatePresence>
            </>
          )}
        </div>

        {story.questions_json?.length ? (
          <button
            onClick={startQuiz}
            className="w-full py-3 rounded-xl bg-dutch-700 text-white hover:bg-dutch-600 transition-colors font-medium"
          >
            Responder preguntas →
          </button>
        ) : (
          <button onClick={restart} className="w-full py-3 rounded-xl border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm">
            ← Volver a historias
          </button>
        )}
      </div>
    )
  }

  // ── Quiz phase ──────────────────────────────────────────────────────────────
  if (phase === 'quiz' && story?.questions_json) {
    const questions = story.questions_json
    const q = questions[currentQ]
    const answered = answers[currentQ]

    return (
      <div className="space-y-5 max-w-md mx-auto">
        <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
          <span>Pregunta {currentQ + 1} / {questions.length}</span>
          <div className="h-2 w-32 bg-gray-200 dark:bg-gray-700 rounded-full self-center">
            <div
              className="h-2 bg-dutch-600 rounded-full transition-all"
              style={{ width: `${((currentQ + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white dark:bg-gray-800 border-2 border-dutch-200 dark:border-dutch-800 text-center">
          <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">{q.question_es}</p>
        </div>

        <div className="space-y-2">
          {q.options.map((opt, i) => {
            const isCorrect = i === q.answer_index
            const isSelected = answered === i
            let cls = 'w-full p-3 rounded-xl border-2 text-sm font-medium transition-colors text-left '
            if (answered !== null) {
              cls += isCorrect
                ? 'border-green-500 bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
                : isSelected
                ? 'border-red-400 bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-300'
                : 'border-gray-100 dark:border-gray-700 text-gray-400 dark:text-gray-600'
            } else {
              cls += 'border-gray-200 dark:border-gray-600 hover:border-dutch-400 hover:bg-dutch-50 dark:hover:border-dutch-500 dark:hover:bg-dutch-950 text-gray-800 dark:text-gray-200 cursor-pointer'
            }
            return (
              <motion.button key={i} whileTap={{ scale: 0.98 }} className={cls} onClick={() => handleAnswer(i)}>
                {opt}
              </motion.button>
            )
          })}
        </div>

        {answered !== null && q.explanation_es && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 text-sm text-amber-800 dark:text-amber-300">
            💡 {q.explanation_es}
          </motion.div>
        )}
      </div>
    )
  }

  // ── Results phase ───────────────────────────────────────────────────────────
  if (phase === 'results' && story?.questions_json) {
    const questions = story.questions_json
    const correct = answers.filter((a, i) => a === questions[i].answer_index).length
    const pct = Math.round((correct / questions.length) * 100)
    return (
      <div className="text-center space-y-4 py-8">
        <div className="text-5xl">{pct >= 80 ? '🏆' : pct >= 50 ? '👍' : '📚'}</div>
        <div className="text-xl font-bold text-gray-800 dark:text-gray-200">
          {correct} / {questions.length} correctas
        </div>
        <div className="text-gray-500 dark:text-gray-400 text-sm">
          {pct >= 80 ? '¡Excelente comprensión!' : pct >= 50 ? '¡Buen trabajo! Sigue practicando.' : 'Vuelve a leer la historia e inténtalo de nuevo.'}
        </div>
        <div className="flex gap-3 justify-center flex-wrap">
          <button
            onClick={() => { setPhase('read'); setAnswers([]); setCurrentQ(0) }}
            className="flex items-center gap-2 px-5 py-2 rounded-xl border border-dutch-400 text-dutch-700 dark:text-dutch-300 hover:bg-dutch-50 dark:hover:bg-dutch-950 transition-colors text-sm"
          >
            <BookOpen size={16} /> Releer historia
          </button>
          <button
            onClick={restart}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-dutch-700 text-white hover:bg-dutch-600 transition-colors text-sm"
          >
            <RefreshCw size={16} /> Otra historia
          </button>
        </div>
      </div>
    )
  }

  return null
}
