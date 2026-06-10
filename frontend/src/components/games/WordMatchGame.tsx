import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchWordMatch } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

interface Pair {
  id: number
  dutch: string
  spanish: string
}

export default function WordMatchGame() {
  const level = useAppStore((s) => s.level)
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['word-match', level],
    queryFn: () => fetchWordMatch(level),
  })

  const [selectedDutch, setSelectedDutch] = useState<number | null>(null)
  const [selectedSpanish, setSelectedSpanish] = useState<number | null>(null)
  const [matched, setMatched] = useState<Set<number>>(new Set())
  const [errors, setErrors] = useState<Set<number>>(new Set())
  const [shuffledSpanish, setShuffledSpanish] = useState<Pair[]>([])

  useEffect(() => {
    if (data?.pairs) {
      const arr = [...data.pairs].sort(() => Math.random() - 0.5)
      setShuffledSpanish(arr)
      setMatched(new Set())
      setErrors(new Set())
      setSelectedDutch(null)
      setSelectedSpanish(null)
    }
  }, [data])

  useEffect(() => {
    if (selectedDutch !== null && selectedSpanish !== null) {
      if (selectedDutch === selectedSpanish) {
        setMatched((m) => new Set([...m, selectedDutch]))
      } else {
        setErrors((e) => new Set([...e, selectedDutch, selectedSpanish]))
        setTimeout(() => setErrors(new Set()), 600)
      }
      setSelectedDutch(null)
      setSelectedSpanish(null)
    }
  }, [selectedDutch, selectedSpanish])

  if (isLoading || !data) return <div className="py-12 text-center text-gray-400">Cargando…</div>

  const pairs: Pair[] = data.pairs
  const allDone = matched.size === pairs.length

  const btnClass = (id: number, selected: boolean) => {
    const base = 'px-3 py-2 rounded-xl border-2 text-sm font-medium transition-all '
    if (matched.has(id))
      return (
        base +
        'border-green-400 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 opacity-60'
      )
    if (errors.has(id))
      return (
        base +
        'border-red-400 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 animate-shake'
      )
    if (selected)
      return (
        base + 'border-brand-400 bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300'
      )
    return (
      base +
      'border-gray-200 dark:border-gray-600 hover:border-brand-400 hover:bg-brand-50 dark:hover:border-brand-400 dark:hover:bg-brand-950 text-gray-800 dark:text-gray-200 cursor-pointer'
    )
  }

  return (
    <div className="space-y-6">
      <p className="text-center text-sm text-gray-500">
        Empareja cada palabra en neerlandés con su traducción
      </p>

      {allDone ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-3 py-8 text-center"
        >
          <div className="text-5xl">🎯</div>
          <div className="text-xl font-bold">¡Todo emparejado!</div>
          <button
            onClick={() => refetch()}
            className="mx-auto flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm text-white transition-colors hover:bg-brand-600"
          >
            <RefreshCw size={16} /> Nuevo juego
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <div className="mb-1 text-xs font-semibold text-gray-400">NEERLANDÉS</div>
            {pairs.map((p) => (
              <button
                key={p.id}
                disabled={matched.has(p.id)}
                onClick={() => !matched.has(p.id) && setSelectedDutch(p.id)}
                className={btnClass(p.id, selectedDutch === p.id) + ' w-full break-words text-left'}
              >
                {p.dutch}
              </button>
            ))}
          </div>
          <div className="space-y-2">
            <div className="mb-1 text-xs font-semibold text-gray-400">ESPAÑOL</div>
            {shuffledSpanish.map((p) => (
              <button
                key={p.id}
                disabled={matched.has(p.id)}
                onClick={() => !matched.has(p.id) && setSelectedSpanish(p.id)}
                className={
                  btnClass(p.id, selectedSpanish === p.id) + ' w-full break-words text-left'
                }
              >
                {p.spanish}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
