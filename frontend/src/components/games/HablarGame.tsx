import { useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchVocabulary, submitSessionComplete, vocabAudioUrl } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { motion } from 'framer-motion'
import { Mic, MicOff, Volume2 } from 'lucide-react'
import SessionSummary from '@/components/SessionSummary'

const ROUND_LENGTH = 5

/* Minimal typing for the (non-standard) Web Speech API */
interface SpeechRecognitionLike {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

function getSpeechRecognition(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as Record<string, unknown>
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as
    | (new () => SpeechRecognitionLike)
    | null
}

const normalize = (s: string) =>
  s
    .toLowerCase()
    .trim()
    .replace(/[.,!?;:]/g, '')

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

export default function HablarGame() {
  const level = useAppStore((s) => s.level)
  const audioEnabled = useAppStore((s) => s.audioEnabled)
  const queryClient = useQueryClient()
  const SpeechRecognitionCtor = useMemo(getSpeechRecognition, [])

  const { data: vocab } = useQuery({
    queryKey: ['vocabulary', level],
    queryFn: () => fetchVocabulary(level),
  })
  const round = useMemo(() => (vocab ? shuffle(vocab).slice(0, ROUND_LENGTH) : []), [vocab])

  const [index, setIndex] = useState(0)
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState<string | null>(null)
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null)
  const [correctCount, setCorrectCount] = useState(0)
  const [finished, setFinished] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)

  const item = round[index]

  if (!SpeechRecognitionCtor)
    return (
      <div className="space-y-3 py-12 text-center">
        <MicOff size={32} className="mx-auto text-gray-400" />
        <p className="font-semibold">Tu navegador no soporta reconocimiento de voz</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          El reconocimiento de neerlandés solo funciona en navegadores basados en Chromium (Chrome,
          Edge). Prueba el juego «Escribir» mientras tanto.
        </p>
      </div>
    )

  const playModel = () => {
    if (!audioEnabled || !item) return
    const audio = new Audio(vocabAudioUrl(item.id))
    audio.play().catch(() => {})
  }

  const listen = () => {
    if (!item || listening) return
    const recognition = new SpeechRecognitionCtor()
    recognition.lang = 'nl-NL'
    recognition.interimResults = false
    recognition.maxAlternatives = 3
    recognitionRef.current = recognition
    setListening(true)
    setTranscript(null)
    setIsCorrect(null)

    recognition.onresult = (event) => {
      const alternatives = Array.from(
        { length: event.results[0].length },
        (_, i) => event.results[0][i].transcript
      )
      const heard = alternatives[0] ?? ''
      setTranscript(heard)
      const target = normalize(item.dutch_word)
      const ok = alternatives.some(
        (alt) => normalize(alt).split(' ').includes(target) || normalize(alt) === target
      )
      setIsCorrect(ok)
      if (ok) setCorrectCount((n) => n + 1)
    }
    recognition.onerror = () => setListening(false)
    recognition.onend = () => setListening(false)
    recognition.start()
  }

  const next = async () => {
    setTranscript(null)
    setIsCorrect(null)
    if (index + 1 >= round.length) {
      setFinished(true)
      try {
        await submitSessionComplete('hablar', correctCount, round.length)
        queryClient.invalidateQueries({ queryKey: ['quests'] })
        queryClient.invalidateQueries({ queryKey: ['user-progress'] })
      } catch {
        /* offline — summary still shows */
      }
    } else {
      setIndex((i) => i + 1)
    }
  }

  if (!vocab) return <div className="py-12 text-center text-gray-400">Cargando vocabulario…</div>
  if (vocab.length < ROUND_LENGTH)
    return (
      <div className="py-12 text-center text-gray-400">
        Necesitas más vocabulario en este nivel para jugar.
      </div>
    )

  if (finished)
    return (
      <SessionSummary
        correct={correctCount}
        total={round.length}
        onRestart={() => {
          setIndex(0)
          setCorrectCount(0)
          setFinished(false)
        }}
      />
    )

  if (!item) return null

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
        <span>
          Palabra {index + 1} / {round.length}
        </span>
        <span>Aciertos: {correctCount}</span>
      </div>

      <div className="rounded-2xl border-2 border-brand-200 bg-white p-6 text-center dark:border-brand-600 dark:bg-gray-800">
        <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">Di en voz alta:</p>
        <p className="text-3xl font-bold text-brand-700 dark:text-brand-300">
          {item.article ? `${item.article} ` : ''}
          {item.dutch_word}
        </p>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">({item.spanish})</p>
        <button
          onClick={playModel}
          aria-label="Escuchar pronunciación modelo"
          className="mt-3 min-h-[44px] min-w-[44px] rounded-full bg-brand-50 p-2 text-brand-700 transition-colors hover:bg-brand-100 dark:bg-brand-900 dark:text-brand-300"
        >
          <Volume2 size={18} className="mx-auto" />
        </button>
      </div>

      <div className="flex flex-col items-center gap-3">
        <button
          onClick={listen}
          disabled={listening}
          aria-label="Pulsar y hablar"
          className={`flex h-20 w-20 items-center justify-center rounded-full text-white transition-all ${
            listening ? 'animate-pulse bg-red-500' : 'bg-brand-500 hover:bg-brand-600'
          }`}
        >
          <Mic size={32} />
        </button>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {listening ? 'Escuchando…' : 'Pulsa y pronuncia la palabra'}
        </span>
      </div>

      {transcript !== null && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          aria-live="polite"
        >
          {isCorrect ? (
            <div className="rounded-xl border border-green-200 bg-green-50 p-3 text-center text-sm text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
              ✓ ¡Bien pronunciado! Entendí «{transcript}»
            </div>
          ) : (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-center text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
              Entendí «{transcript}» — escucha el modelo e inténtalo otra vez, o continúa.
            </div>
          )}
        </motion.div>
      )}

      {transcript !== null && (
        <button
          onClick={next}
          className="min-h-[44px] w-full rounded-xl bg-brand-500 py-2.5 font-medium text-white transition-colors hover:bg-brand-600"
        >
          {index + 1 >= round.length ? 'Ver resumen' : 'Siguiente'}
        </button>
      )}
    </div>
  )
}
