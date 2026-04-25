import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchStories, fetchStory } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { ChevronRight, BookOpen, RefreshCw } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

type Phase = 'list' | 'read' | 'quiz' | 'results'

export default function StoryModeGame() {
  const level = useAppStore((s) => s.level)
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
        setCurrentQ((q) => q + 1)
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
    if (loadingList)
      return (
        <div className="py-12 text-center text-gray-400 dark:text-gray-500">
          Cargando historias…
        </div>
      )
    if (!stories?.length)
      return (
        <div className="space-y-2 py-12 text-center">
          <div className="text-4xl">📖</div>
          <div className="font-semibold">
            No hay historias disponibles para el nivel {level.toUpperCase()}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Añade historias en data/stories/ y vuelve a sembrar la base de datos.
          </div>
        </div>
      )
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <BookOpen size={16} />
          <span>Elige una historia para leer y practicar comprensión:</span>
        </div>
        {stories.map((s) => (
          <motion.button
            key={s.slug}
            whileTap={{ scale: 0.98 }}
            onClick={() => startStory(s.slug)}
            className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-white p-4 text-left transition-colors hover:border-brand-400 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-brand-400"
          >
            <div>
              <div className="font-semibold text-gray-800 dark:text-gray-200">{s.title_nl}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">{s.title_es}</div>
              {s.theme && (
                <div className="mt-0.5 text-xs text-brand-600 dark:text-brand-400">{s.theme}</div>
              )}
            </div>
            <ChevronRight size={18} className="shrink-0 text-gray-400" />
          </motion.button>
        ))}
      </div>
    )
  }

  // ── Read phase ──────────────────────────────────────────────────────────────
  if (phase === 'read') {
    if (loadingStory || !story)
      return (
        <div className="py-12 text-center text-gray-400 dark:text-gray-500">Cargando historia…</div>
      )
    return (
      <div className="mx-auto max-w-lg space-y-5">
        <div className="flex items-center gap-2">
          <button
            onClick={restart}
            className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            ← Historias
          </button>
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200">{story.title_nl}</h2>
          <p className="text-sm italic text-gray-500 dark:text-gray-400">{story.title_es}</p>
        </div>

        <div className="space-y-3 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
          <p className="whitespace-pre-wrap leading-relaxed text-gray-800 dark:text-gray-200">
            {story.content_nl}
          </p>
          {story.content_es && (
            <>
              <button
                onClick={() => setShowSpanish((v) => !v)}
                className="text-xs text-brand-600 underline dark:text-brand-400"
              >
                {showSpanish ? 'Ocultar traducción' : 'Ver traducción al español'}
              </button>
              <AnimatePresence>
                {showSpanish && (
                  <motion.p
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden whitespace-pre-wrap text-sm italic leading-relaxed text-gray-500 dark:text-gray-400"
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
            className="w-full rounded-xl bg-brand-500 py-3 font-medium text-white transition-colors hover:bg-brand-600"
          >
            Responder preguntas →
          </button>
        ) : (
          <button
            onClick={restart}
            className="w-full rounded-xl border border-gray-300 py-3 text-sm text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
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
      <div className="mx-auto max-w-md space-y-5">
        <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
          <span>
            Pregunta {currentQ + 1} / {questions.length}
          </span>
          <div className="h-2 w-32 self-center rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className="h-2 rounded-full bg-brand-600 transition-all"
              style={{ width: `${((currentQ + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>

        <div className="rounded-2xl border-2 border-brand-200 bg-white p-5 text-center dark:border-brand-600 dark:bg-gray-800">
          <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">{q.question_es}</p>
        </div>

        <div className="space-y-2">
          {q.options.map((opt, i) => {
            const isCorrect = i === q.answer_index
            const isSelected = answered === i
            let cls =
              'w-full p-3 rounded-xl border-2 text-sm font-medium transition-colors text-left '
            if (answered !== null) {
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
                whileTap={{ scale: 0.98 }}
                className={cls}
                onClick={() => handleAnswer(i)}
              >
                {opt}
              </motion.button>
            )
          })}
        </div>

        {answered !== null && q.explanation_es && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300"
          >
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
      <div className="space-y-4 py-8 text-center">
        <div className="text-5xl">{pct >= 80 ? '🏆' : pct >= 50 ? '👍' : '📚'}</div>
        <div className="text-xl font-bold text-gray-800 dark:text-gray-200">
          {correct} / {questions.length} correctas
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {pct >= 80
            ? '¡Excelente comprensión!'
            : pct >= 50
              ? '¡Buen trabajo! Sigue practicando.'
              : 'Vuelve a leer la historia e inténtalo de nuevo.'}
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          <button
            onClick={() => {
              setPhase('read')
              setAnswers([])
              setCurrentQ(0)
            }}
            className="flex items-center gap-2 rounded-xl border border-brand-400 px-5 py-2 text-sm text-brand-500 transition-colors hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-brand-950"
          >
            <BookOpen size={16} /> Releer historia
          </button>
          <button
            onClick={restart}
            className="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm text-white transition-colors hover:bg-brand-600"
          >
            <RefreshCw size={16} /> Otra historia
          </button>
        </div>
      </div>
    )
  }

  return null
}
