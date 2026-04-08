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
  1: 'bg-red-100 hover:bg-red-200 text-red-700',
  2: 'bg-orange-100 hover:bg-orange-200 text-orange-700',
  3: 'bg-green-100 hover:bg-green-200 text-green-700',
  4: 'bg-blue-100 hover:bg-blue-200 text-blue-700',
}

export default function FlashcardGame() {
  const audioEnabled = useAppStore(s => s.audioEnabled)
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
      setXpGained(x => x + data.xp_earned)
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
      nextCard()
    },
  })

  const nextCard = () => {
    setFlipped(false)
    setIndex(i => i + 1)
  }

  const playAudio = (path: string) => {
    if (!audioEnabled) return
    const audio = new Audio(`/audio/${path}`)
    audio.play().catch(() => {})
  }

  if (isLoading) return <LoadingPlaceholder />
  if (!cards || cards.length === 0) return <EmptyState />

  const card = cards[index]
  if (!card) return <FinishedState xpGained={xpGained} onRestart={() => { setIndex(0); setXpGained(0) }} />

  const item = card.vocab_item

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Progress */}
      <div className="w-full max-w-md">
        <div className="flex justify-between text-sm text-gray-500 mb-1">
          <span>{index + 1} / {cards.length}</span>
          <span className="text-yellow-600">+{xpGained} XP</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full">
          <div
            className="h-2 bg-dutch-600 rounded-full transition-all"
            style={{ width: `${((index) / cards.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Flashcard */}
      <div
        className="w-full max-w-md h-56 cursor-pointer"
        onClick={() => setFlipped(f => !f)}
        style={{ perspective: 1000 }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={flipped ? 'back' : 'front'}
            initial={{ rotateY: flipped ? -90 : 90, opacity: 0 }}
            animate={{ rotateY: 0, opacity: 1 }}
            exit={{ rotateY: flipped ? 90 : -90, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full flex flex-col items-center justify-center p-6 rounded-2xl bg-white border-2 border-dutch-200 shadow-md"
          >
            {!flipped ? (
              <>
                <div className="text-4xl font-bold text-dutch-700">
                  {item.article ? `${item.article} ` : ''}{item.dutch_word}
                </div>
                {item.example_nl && (
                  <div className="text-sm text-gray-400 mt-3 italic text-center">{item.example_nl}</div>
                )}
                {item.audio_files.length > 0 && (
                  <button
                    onClick={e => { e.stopPropagation(); playAudio(item.audio_files[0].file_path) }}
                    className="mt-4 p-2 rounded-full bg-dutch-50 hover:bg-dutch-100 text-dutch-700 transition-colors"
                  >
                    <Volume2 size={20} />
                  </button>
                )}
                <div className="text-xs text-gray-400 mt-4">Toca para ver la respuesta</div>
              </>
            ) : (
              <>
                <div className="text-3xl font-semibold text-gray-800">{item.spanish}</div>
                {item.example_es && (
                  <div className="text-sm text-gray-400 mt-3 italic text-center">{item.example_es}</div>
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
          className="grid grid-cols-4 gap-2 w-full max-w-md"
        >
          {([1, 2, 3, 4] as const).map(r => (
            <button
              key={r}
              onClick={() => reviewMutation.mutate({ cardId: card.id, rating: r })}
              disabled={reviewMutation.isPending}
              className={`py-2 rounded-xl text-sm font-medium transition-colors ${RATING_COLORS[r]}`}
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
  return <div className="text-center text-gray-400 py-12">Cargando tarjetas…</div>
}

function EmptyState() {
  return (
    <div className="text-center py-12 space-y-2">
      <div className="text-4xl">🎉</div>
      <div className="font-semibold text-lg">¡No tienes tarjetas pendientes!</div>
      <div className="text-sm text-gray-500">Añade vocabulario desde las lecciones para empezar.</div>
    </div>
  )
}

function FinishedState({ xpGained, onRestart }: { xpGained: number; onRestart: () => void }) {
  return (
    <div className="text-center py-12 space-y-3">
      <div className="text-5xl">✅</div>
      <div className="font-bold text-xl">¡Sesión completada!</div>
      <div className="text-yellow-600 font-semibold">+{xpGained} XP ganados</div>
      <button
        onClick={onRestart}
        className="mt-4 px-6 py-2 rounded-xl bg-dutch-700 text-white hover:bg-dutch-600 transition-colors"
      >
        Repetir
      </button>
    </div>
  )
}
