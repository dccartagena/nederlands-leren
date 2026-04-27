import { useState, useMemo, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchStories,
  fetchStory,
  fetchVocabulary,
  fetchUserProgress,
  submitStoryComplete,
} from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { ChevronRight, BookOpen, RefreshCw, Volume2, CheckCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { VocabularyItem } from '@/lib/api'

type Phase = 'list' | 'read' | 'quiz' | 'results'

export default function StoryModeGame() {
  const level = useAppStore((s) => s.level)
  const audioEnabled = useAppStore((s) => s.audioEnabled)
  const queryClient = useQueryClient()

  const [phase, setPhase] = useState<Phase>('list')
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [showSpanish, setShowSpanish] = useState(false)
  const [answers, setAnswers] = useState<(number | null)[]>([])
  const [currentQ, setCurrentQ] = useState(0)
  const [sessionResult, setSessionResult] = useState<{ xp: number; achievements: string[] } | null>(null)
  const [selectedWord, setSelectedWord] = useState<VocabularyItem | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

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

  const { data: vocabulary } = useQuery({
    queryKey: ['vocabulary-full', level],
    queryFn: () => fetchVocabulary(level, undefined, 500),
  })

  const { data: userProgress } = useQuery({
    queryKey: ['user-progress'],
    queryFn: fetchUserProgress,
  })

  const completedSlugs = useMemo(
    () => new Set(userProgress?.settings_json?.completed_stories ?? []),
    [userProgress]
  )

  const vocabMap = useMemo(() => {
    const map = new Map<string, VocabularyItem>()
    vocabulary?.forEach((v) => map.set(v.dutch_word.toLowerCase(), v))
    return map
  }, [vocabulary])

  const completeMutation = useMutation({
    mutationFn: ({ slug, correct, total }: { slug: string; correct: number; total: number }) =>
      submitStoryComplete(slug, correct, total),
    onSuccess: (data) => {
      setSessionResult({ xp: data.xp_earned, achievements: data.new_achievements })
      queryClient.invalidateQueries({ queryKey: ['user-progress'] })
      queryClient.invalidateQueries({ queryKey: ['xp-history-today'] })
    },
  })

  const startStory = (slug: string) => {
    setSelectedSlug(slug)
    setPhase('read')
    setShowSpanish(false)
    setAnswers([])
    setCurrentQ(0)
    setSessionResult(null)
    setSelectedWord(null)
  }

  const startQuiz = () => {
    if (!story?.questions_json?.length) return
    setAnswers(new Array(story.questions_json.length).fill(null))
    setCurrentQ(0)
    setPhase('quiz')
    setSelectedWord(null)
  }

  const handleAnswer = (optionIndex: number) => {
    if (answers[currentQ] !== null) return
    const updated = [...answers]
    updated[currentQ] = optionIndex
    setAnswers(updated)
    setTimeout(() => {
      if (currentQ + 1 < (story?.questions_json?.length ?? 0)) {
        setCurrentQ((q) => q + 1)
      } else {
        const questions = story?.questions_json ?? []
        const correctCount = updated.filter((a, i) => a === questions[i]?.answer_index).length
        completeMutation.mutate({ slug: selectedSlug!, correct: correctCount, total: questions.length })
        setPhase('results')
      }
    }, 900)
  }

  const restart = () => {
    setPhase('list')
    setSelectedSlug(null)
    setAnswers([])
    setCurrentQ(0)
    setSessionResult(null)
    setSelectedWord(null)
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
  }

  const playStoryAudio = () => {
    if (!story?.audio_path || !audioEnabled) return
    if (audioRef.current) audioRef.current.pause()
    const path = story.audio_path.startsWith('/') ? story.audio_path : `/audio/${story.audio_path}`
    const audio = new Audio(path)
    audioRef.current = audio
    audio.play().catch(() => {})
  }

  // ── List phase ───────────────────────────────────────────────────────────────
  if (phase === 'list') {
    if (loadingList)
      return (
        <div className="py-12 text-center text-gray-400 dark:text-gray-500">Cargando historias…</div>
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
        {stories.map((s) => {
          const done = completedSlugs.has(s.slug)
          return (
            <motion.button
              key={s.slug}
              whileTap={{ scale: 0.98 }}
              onClick={() => startStory(s.slug)}
              className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-white p-4 text-left transition-colors hover:border-brand-400 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-brand-400"
            >
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-gray-800 dark:text-gray-200">{s.title_nl}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">{s.title_es}</div>
                {s.theme && (
                  <div className="mt-0.5 text-xs text-brand-600 dark:text-brand-400">{s.theme}</div>
                )}
              </div>
              {done ? (
                <CheckCircle size={18} className="ml-3 shrink-0 text-green-500" />
              ) : (
                <ChevronRight size={18} className="ml-3 shrink-0 text-gray-400" />
              )}
            </motion.button>
          )
        })}
      </div>
    )
  }

  // ── Read phase ───────────────────────────────────────────────────────────────
  if (phase === 'read') {
    if (loadingStory || !story)
      return (
        <div className="py-12 text-center text-gray-400 dark:text-gray-500">Cargando historia…</div>
      )
    return (
      <div className="mx-auto max-w-lg space-y-5">
        <button
          onClick={restart}
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          ← Historias
        </button>

        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200">{story.title_nl}</h2>
            <p className="text-sm italic text-gray-500 dark:text-gray-400">{story.title_es}</p>
          </div>
          {story.audio_path && audioEnabled && (
            <button
              onClick={playStoryAudio}
              className="flex shrink-0 items-center gap-1.5 rounded-full bg-brand-50 px-3 py-2 text-xs font-medium text-brand-600 transition-colors hover:bg-brand-100 dark:bg-brand-950 dark:text-brand-300 dark:hover:bg-brand-900"
            >
              <Volume2 size={15} />
              Escuchar
            </button>
          )}
        </div>

        <div className="space-y-3 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
          {vocabMap.size > 0 ? (
            <ClickableStoryText
              text={story.content_nl ?? ''}
              vocabMap={vocabMap}
              onWordClick={setSelectedWord}
            />
          ) : (
            <p className="whitespace-pre-wrap leading-relaxed text-gray-800 dark:text-gray-200">
              {story.content_nl}
            </p>
          )}

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

        {/* Word tooltip panel */}
        <AnimatePresence>
          {selectedWord && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="rounded-xl border border-brand-200 bg-brand-50 p-3 dark:border-brand-700 dark:bg-brand-950"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="font-semibold text-brand-700 dark:text-brand-300">
                    {selectedWord.article ? `${selectedWord.article} ` : ''}
                    {selectedWord.dutch_word}
                  </span>
                  <span className="text-gray-600 dark:text-gray-300"> → {selectedWord.spanish}</span>
                  {selectedWord.word_type && (
                    <span className="ml-2 text-xs text-gray-400">({selectedWord.word_type})</span>
                  )}
                </div>
                <button
                  onClick={() => setSelectedWord(null)}
                  className="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  ×
                </button>
              </div>
              {selectedWord.example_nl && (
                <div className="mt-1 text-xs italic text-gray-500 dark:text-gray-400">
                  {selectedWord.example_nl}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

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

  // ── Quiz phase ───────────────────────────────────────────────────────────────
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

  // ── Results phase ────────────────────────────────────────────────────────────
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

        {sessionResult && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="inline-flex items-center gap-2 rounded-full bg-yellow-100 px-4 py-2 font-semibold text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300"
          >
            ⭐ +{sessionResult.xp} XP ganados
          </motion.div>
        )}

        {sessionResult?.achievements.length ? (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-300"
          >
            🏅{' '}
            {sessionResult.achievements.length === 1 ? '¡Nuevo logro desbloqueado!' : '¡Nuevos logros!'}
          </motion.div>
        ) : null}

        <div className="flex flex-wrap justify-center gap-3 pt-2">
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

// Renders story text with clickable Dutch words that have a known vocabulary entry.
function ClickableStoryText({
  text,
  vocabMap,
  onWordClick,
}: {
  text: string
  vocabMap: Map<string, VocabularyItem>
  onWordClick: (v: VocabularyItem) => void
}) {
  const paragraphs = text.split('\n')
  return (
    <div className="space-y-3 leading-relaxed text-gray-800 dark:text-gray-200">
      {paragraphs.map((para, pi) =>
        para.trim() ? (
          <p key={pi}>
            {para.split(/(\s+)/).map((token, ti) => {
              if (/^\s+$/.test(token)) return <span key={ti}>{token}</span>
              // Strip leading/trailing punctuation for lookup, keep original for display
              const clean = token.replace(/^[^a-zA-ZÀ-ÿ]+|[^a-zA-ZÀ-ÿ]+$/g, '').toLowerCase()
              const vocab = vocabMap.get(clean)
              return vocab ? (
                <button
                  key={ti}
                  className="rounded underline decoration-dotted transition-colors hover:text-brand-700 text-brand-600 dark:text-brand-400 dark:hover:text-brand-200"
                  onClick={() => onWordClick(vocab)}
                >
                  {token}
                </button>
              ) : (
                <span key={ti}>{token}</span>
              )
            })}
          </p>
        ) : (
          <br key={pi} />
        )
      )}
    </div>
  )
}
