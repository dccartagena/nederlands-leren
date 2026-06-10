import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDueCards, submitReview, vocabAudioUrl } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { motion, AnimatePresence } from 'framer-motion'
import { Volume2, Snail } from 'lucide-react'
import SessionSummary from '@/components/SessionSummary'

const COMBO_THRESHOLD = 5

const RATING_LABELS: Record<number, string> = {
  1: 'Otra vez',
  2: 'Difícil',
  3: 'Bien',
  4: 'Fácil',
}
const RATING_COLORS: Record<number, string> = {
  1: 'bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-950 dark:hover:bg-red-900 dark:text-red-300',
  2: 'bg-orange-100 hover:bg-orange-200 text-orange-700 dark:bg-orange-950 dark:hover:bg-orange-900 dark:text-orange-300',
  3: 'bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-950 dark:hover:bg-green-900 dark:text-green-300',
  4: 'bg-blue-100 hover:bg-blue-200 text-blue-700 dark:bg-blue-950 dark:hover:bg-blue-900 dark:text-blue-300',
}

export default function FlashcardGame() {
  const audioEnabled = useAppStore((s) => s.audioEnabled)
  const sereneMode = useAppStore((s) => s.sereneMode)
  const queryClient = useQueryClient()
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [xpGained, setXpGained] = useState(0)
  const [correctCount, setCorrectCount] = useState(0)
  const [ratedCount, setRatedCount] = useState(0)
  const [combo, setCombo] = useState(0)
  const [maxCombo, setMaxCombo] = useState(0)
  const [promotions, setPromotions] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const { data: cards, isLoading } = useQuery({
    queryKey: ['due-cards-game'],
    queryFn: () => fetchDueCards(20),
  })

  const card = cards?.[index]
  const comboActive = combo >= COMBO_THRESHOLD

  const reviewMutation = useMutation({
    mutationFn: ({ cardId, rating }: { cardId: number; rating: 1 | 2 | 3 | 4 }) =>
      submitReview(cardId, rating, comboActive),
    onSuccess: (data, { rating }) => {
      setXpGained((x) => x + data.xp_earned)
      setRatedCount((n) => n + 1)
      if (card && data.state > card.state) setPromotions((n) => n + 1)
      if (rating >= 3) {
        setCorrectCount((n) => n + 1)
        setCombo((c) => {
          const next = c + 1
          setMaxCombo((m) => Math.max(m, next))
          return next
        })
      } else {
        setCombo(0)
      }
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
      queryClient.invalidateQueries({ queryKey: ['quests'] })
      nextCard()
    },
  })

  const nextCard = () => {
    setFlipped(false)
    setIndex((i) => i + 1)
  }

  const playAudio = (url: string, rate = 1) => {
    if (!audioEnabled) return
    const audio = new Audio(url)
    audio.playbackRate = rate
    audioRef.current = audio
    audio.play().catch(() => {})
  }

  const rate = (r: 1 | 2 | 3 | 4) => {
    if (!card || reviewMutation.isPending) return
    reviewMutation.mutate({ cardId: card.id, rating: r })
  }

  // Keyboard shortcuts: Space = flip, 1–4 = FSRS rating
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
      if (!card) return
      if (e.code === 'Space') {
        e.preventDefault()
        setFlipped((f) => !f)
      } else if (flipped && ['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault()
        rate(Number(e.key) as 1 | 2 | 3 | 4)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [card?.id, flipped, comboActive, reviewMutation.isPending])

  if (isLoading) return <LoadingPlaceholder />
  if (!cards || cards.length === 0) return <EmptyState />

  if (!card)
    return (
      <SessionSummary
        correct={correctCount}
        total={ratedCount}
        xpGained={xpGained}
        promotions={promotions}
        maxCombo={maxCombo}
        onRestart={() => {
          setIndex(0)
          setFlipped(false)
          setXpGained(0)
          setCorrectCount(0)
          setRatedCount(0)
          setCombo(0)
          setMaxCombo(0)
          setPromotions(0)
          queryClient.invalidateQueries({ queryKey: ['due-cards-game'] })
        }}
      />
    )

  const item = card.vocab_item
  const audioFile = vocabAudioUrl(item.id)

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Progress */}
      <div className="w-full max-w-md">
        <div className="mb-1 flex justify-between text-sm text-gray-500 dark:text-gray-400">
          <span>
            {index + 1} / {cards.length}
          </span>
          <span className="flex items-center gap-2">
            {!sereneMode && comboActive && (
              <span
                className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700 dark:bg-orange-950 dark:text-orange-300"
                aria-live="polite"
              >
                🔥 Combo ×1.5
              </span>
            )}
            {!sereneMode && <span className="text-yellow-600">+{xpGained} XP</span>}
          </span>
        </div>
        <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700">
          <div
            className="h-2 rounded-full bg-brand-600 transition-all"
            style={{ width: `${(index / cards.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Flashcard */}
      <div
        className="h-56 w-full max-w-md cursor-pointer"
        onClick={() => setFlipped((f) => !f)}
        style={{ perspective: 1000 }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={flipped ? 'back' : 'front'}
            initial={{ rotateY: flipped ? -90 : 90, opacity: 0 }}
            animate={{ rotateY: 0, opacity: 1 }}
            exit={{ rotateY: flipped ? 90 : -90, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex h-full w-full flex-col items-center justify-center rounded-2xl border-2 border-brand-200 bg-white p-6 shadow-md dark:border-brand-600 dark:bg-gray-800"
          >
            {!flipped ? (
              <>
                <div className="text-4xl font-bold text-brand-700 dark:text-brand-300">
                  {item.article ? `${item.article} ` : ''}
                  {item.dutch_word}
                </div>
                {item.example_nl && (
                  <div className="mt-3 text-center text-sm italic text-gray-500 dark:text-gray-400">
                    {item.example_nl}
                  </div>
                )}
                <div className="mt-4 flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      playAudio(audioFile)
                    }}
                    aria-label="Escuchar pronunciación"
                    className="min-h-[44px] min-w-[44px] rounded-full bg-brand-50 p-2 text-brand-700 transition-colors hover:bg-brand-100 focus-visible:ring-2 focus-visible:ring-brand-700 dark:bg-brand-900 dark:text-brand-300 dark:hover:bg-brand-600"
                  >
                    <Volume2 size={20} className="mx-auto" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      playAudio(audioFile, 0.7)
                    }}
                    aria-label="Escuchar despacio"
                    className="min-h-[44px] min-w-[44px] rounded-full bg-gray-100 p-2 text-gray-600 transition-colors hover:bg-gray-200 focus-visible:ring-2 focus-visible:ring-brand-700 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    <Snail size={20} className="mx-auto" />
                  </button>
                </div>
                <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                  Toca o pulsa Espacio para ver la respuesta
                </div>
              </>
            ) : (
              <>
                <div className="text-3xl font-semibold text-gray-800 dark:text-gray-200">
                  {item.spanish}
                </div>
                {item.example_es && (
                  <div className="mt-3 text-center text-sm italic text-gray-500 dark:text-gray-400">
                    {item.example_es}
                  </div>
                )}
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Rating buttons */}
      {flipped && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid w-full max-w-md grid-cols-2 gap-2 sm:grid-cols-4"
        >
          {([1, 2, 3, 4] as const).map((r) => (
            <button
              key={r}
              onClick={() => rate(r)}
              disabled={reviewMutation.isPending}
              className={`min-h-[44px] rounded-xl py-2 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2 ${RATING_COLORS[r]}`}
            >
              {RATING_LABELS[r]}
              <span className="ml-1 hidden text-xs opacity-50 sm:inline">{r}</span>
            </button>
          ))}
        </motion.div>
      )}
    </div>
  )
}

function LoadingPlaceholder() {
  return (
    <div className="py-12 text-center text-gray-400 dark:text-gray-500">Cargando tarjetas…</div>
  )
}

function EmptyState() {
  return (
    <div className="space-y-2 py-12 text-center">
      <div className="text-4xl">🎉</div>
      <div className="text-lg font-semibold">¡No tienes tarjetas pendientes!</div>
      <div className="text-sm text-gray-500 dark:text-gray-400">
        Añade vocabulario desde las lecciones para empezar.
      </div>
    </div>
  )
}
