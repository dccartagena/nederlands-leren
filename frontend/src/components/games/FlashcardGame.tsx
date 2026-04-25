import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDueCards, submitReview } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { motion, AnimatePresence } from 'framer-motion'
import { Volume2 } from 'lucide-react'

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
  const queryClient = useQueryClient()
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [xpGained, setXpGained] = useState(0)

  const { data: cards, isLoading } = useQuery({
    queryKey: ['due-cards-game'],
    queryFn: () => fetchDueCards(20),
  })

  const reviewMutation = useMutation({
    mutationFn: ({ cardId, rating }: { cardId: number; rating: 1 | 2 | 3 | 4 }) =>
      submitReview(cardId, rating),
    onSuccess: (data) => {
      setXpGained((x) => x + data.xp_earned)
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
      nextCard()
    },
  })

  const nextCard = () => {
    setFlipped(false)
    setIndex((i) => i + 1)
  }

  const playAudio = (path: string) => {
    if (!audioEnabled) return
    const url = path.startsWith('audio/') ? `/${path}` : `/audio/${path}`
    const audio = new Audio(url)
    audio.play().catch(() => {})
  }

  if (isLoading) return <LoadingPlaceholder />
  if (!cards || cards.length === 0) return <EmptyState />

  const card = cards[index]
  if (!card)
    return (
      <FinishedState
        xpGained={xpGained}
        onRestart={() => {
          setIndex(0)
          setXpGained(0)
        }}
      />
    )

  const item = card.vocab_item

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Progress */}
      <div className="w-full max-w-md">
        <div className="mb-1 flex justify-between text-sm text-gray-500 dark:text-gray-400">
          <span>
            {index + 1} / {cards.length}
          </span>
          <span className="text-yellow-600">+{xpGained} XP</span>
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
                <div className="text-4xl font-bold text-brand-500 dark:text-brand-300">
                  {item.article ? `${item.article} ` : ''}
                  {item.dutch_word}
                </div>
                {item.example_nl && (
                  <div className="mt-3 text-center text-sm italic text-gray-400">
                    {item.example_nl}
                  </div>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    playAudio(`/audio/gtts_${item.dutch_word}_${item.level}.wav`)
                  }}
                  className="mt-4 rounded-full bg-brand-50 p-2 text-brand-500 transition-colors hover:bg-brand-100 dark:bg-brand-900 dark:text-brand-300 dark:hover:bg-brand-600"
                >
                  <Volume2 size={20} />
                </button>
                <div className="mt-4 text-xs text-gray-400">Toca para ver la respuesta</div>
              </>
            ) : (
              <>
                <div className="text-3xl font-semibold text-gray-800 dark:text-gray-200">
                  {item.spanish}
                </div>
                {item.example_es && (
                  <div className="mt-3 text-center text-sm italic text-gray-400">
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
              onClick={() => reviewMutation.mutate({ cardId: card.id, rating: r })}
              disabled={reviewMutation.isPending}
              className={`rounded-xl py-2 text-sm font-medium transition-colors ${RATING_COLORS[r]}`}
            >
              {RATING_LABELS[r]}
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

function FinishedState({ xpGained, onRestart }: { xpGained: number; onRestart: () => void }) {
  return (
    <div className="space-y-3 py-12 text-center">
      <div className="text-5xl">✅</div>
      <div className="text-xl font-bold">¡Sesión completada!</div>
      <div className="font-semibold text-yellow-600">+{xpGained} XP ganados</div>
      <button
        onClick={onRestart}
        className="mt-4 rounded-xl bg-brand-500 px-6 py-2 text-white transition-colors hover:bg-brand-600"
      >
        Repetir
      </button>
    </div>
  )
}
