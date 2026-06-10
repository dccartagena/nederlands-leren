import { useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchVocabulary, getFeedback, submitSessionComplete, type VocabularyItem } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { motion } from 'framer-motion'
import { PenLine } from 'lucide-react'
import SessionSummary from '@/components/SessionSummary'

const ROUND_LENGTH = 5

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

const normalize = (s: string) =>
  s
    .toLowerCase()
    .trim()
    .replace(/[.,!?;:]/g, '')
    .replace(/\s+/g, ' ')

type Verdict = 'correct' | 'article' | 'wrong'

/** Grade a typed answer. Nouns require the article — a missing or wrong
 *  article is its own verdict so feedback can target the de/het trap. */
export function gradeAnswer(item: VocabularyItem, raw: string): Verdict {
  const answer = normalize(raw)
  const word = normalize(item.dutch_word)
  if (item.article) {
    if (answer === `${item.article} ${word}`) return 'correct'
    const otherArticle = item.article === 'de' ? 'het' : 'de'
    if (answer === word || answer === `${otherArticle} ${word}`) return 'article'
    return 'wrong'
  }
  return answer === word ? 'correct' : 'wrong'
}

export default function EscribirGame() {
  const level = useAppStore((s) => s.level)
  const queryClient = useQueryClient()
  const { data: vocab } = useQuery({
    queryKey: ['vocabulary', level],
    queryFn: () => fetchVocabulary(level),
  })

  const round = useMemo(() => (vocab ? shuffle(vocab).slice(0, ROUND_LENGTH) : []), [vocab])
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [fbLoading, setFbLoading] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [finished, setFinished] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const item = round[index]

  const expected = item
    ? item.article
      ? `${item.article} ${item.dutch_word}`
      : item.dutch_word
    : ''

  const check = async () => {
    if (!item || verdict !== null || !answer.trim()) return
    const v = gradeAnswer(item, answer)
    setVerdict(v)
    if (v === 'correct') {
      setCorrectCount((n) => n + 1)
    } else if (v === 'article') {
      setFeedback(
        `Casi: la palabra es correcta, pero el artículo es «${item.article}». ` +
          `Recuerda: de/het no se deduce del español — apréndelo con la palabra.`
      )
    } else {
      setFbLoading(true)
      try {
        const { feedback: fb } = await getFeedback(
          `Escribe "${item.spanish}" en neerlandés`,
          expected,
          answer
        )
        setFeedback(fb)
      } catch {
        setFeedback(`La respuesta correcta es «${expected}».`)
      }
      setFbLoading(false)
    }
  }

  const next = async () => {
    setAnswer('')
    setVerdict(null)
    setFeedback(null)
    if (index + 1 >= round.length) {
      setFinished(true)
      try {
        await submitSessionComplete('escribir', correctCount, round.length)
        queryClient.invalidateQueries({ queryKey: ['quests'] })
        queryClient.invalidateQueries({ queryKey: ['user-progress'] })
      } catch {
        /* offline — summary still shows */
      }
    } else {
      setIndex((i) => i + 1)
      inputRef.current?.focus()
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
          queryClient.invalidateQueries({ queryKey: ['vocabulary', level] })
        }}
      />
    )

  if (!item) return null

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
        <span>
          Frase {index + 1} / {round.length}
        </span>
        <span>Aciertos: {correctCount}</span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className="h-1.5 rounded-full bg-brand-600 transition-all"
          style={{ width: `${(index / round.length) * 100}%` }}
        />
      </div>

      <div className="rounded-2xl border-2 border-brand-200 bg-white p-5 text-center dark:border-brand-600 dark:bg-gray-800">
        <p className="mb-1 flex items-center justify-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
          <PenLine size={14} /> Escribe en neerlandés
          {item.article && <span className="text-xs">(con artículo)</span>}
        </p>
        <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{item.spanish}</p>
        {item.example_es && (
          <p className="mt-2 text-sm italic text-gray-500 dark:text-gray-400">{item.example_es}</p>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (verdict === null) check()
          else next()
        }}
        className="space-y-3"
      >
        <input
          ref={inputRef}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          disabled={verdict !== null}
          autoFocus
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          placeholder={item.article ? 'de/het + palabra…' : 'Escribe aquí…'}
          aria-label="Tu respuesta en neerlandés"
          className={`min-h-[44px] w-full rounded-xl border-2 bg-white px-4 py-3 text-lg outline-none transition-colors dark:bg-gray-800 ${
            verdict === null
              ? 'border-gray-200 focus:border-brand-400 dark:border-gray-600'
              : verdict === 'correct'
                ? 'border-green-500 bg-green-50 dark:bg-green-950'
                : 'border-red-400 bg-red-50 dark:bg-red-950'
          }`}
        />

        {/* Feedback adjacent to the answer (spatial contiguity) */}
        {verdict !== null && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            aria-live="polite"
          >
            {verdict === 'correct' ? (
              <div className="rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
                ✓ ¡Correcto! «{expected}»
              </div>
            ) : (
              <div className="space-y-2">
                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
                  La respuesta correcta es «{expected}»
                  {item.example_nl && (
                    <span className="mt-1 block italic opacity-80">{item.example_nl}</span>
                  )}
                </div>
                {(feedback || fbLoading) && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
                    {fbLoading ? 'Analizando tu respuesta…' : feedback}
                  </div>
                )}
              </div>
            )}
          </motion.div>
        )}

        <button
          type="submit"
          disabled={verdict === null && !answer.trim()}
          className="min-h-[44px] w-full rounded-xl bg-brand-500 py-2.5 font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-40"
        >
          {verdict === null ? 'Comprobar' : index + 1 >= round.length ? 'Ver resumen' : 'Siguiente'}
        </button>
      </form>
    </div>
  )
}
