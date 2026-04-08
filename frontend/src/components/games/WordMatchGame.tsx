import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchWordMatch } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

interface Pair { id: number; dutch: string; spanish: string }

export default function WordMatchGame() {
  const level = useAppStore(s => s.level)
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
        setMatched(m => new Set([...m, selectedDutch]))
      } else {
        setErrors(e => new Set([...e, selectedDutch, selectedSpanish]))
        setTimeout(() => setErrors(new Set()), 600)
      }
      setSelectedDutch(null)
      setSelectedSpanish(null)
    }
  }, [selectedDutch, selectedSpanish])

  if (isLoading || !data) return <div className="text-gray-400 text-center py-12">Cargando…</div>

  const pairs: Pair[] = data.pairs
  const allDone = matched.size === pairs.length

  const btnClass = (id: number, selected: boolean) => {
    const base = 'px-3 py-2 rounded-xl border-2 text-sm font-medium transition-all '
    if (matched.has(id)) return base + 'border-green-400 bg-green-50 text-green-700 opacity-60'
    if (errors.has(id)) return base + 'border-red-400 bg-red-50 text-red-700 animate-shake'
    if (selected) return base + 'border-dutch-500 bg-dutch-100 text-dutch-700'
    return base + 'border-gray-200 hover:border-dutch-400 hover:bg-dutch-50 text-gray-800 cursor-pointer'
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500 text-center">Empareja cada palabra en neerlandés con su traducción</p>

      {allDone ? (
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center space-y-3 py-8">
          <div className="text-5xl">🎯</div>
          <div className="font-bold text-xl">¡Todo emparejado!</div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 mx-auto px-5 py-2 rounded-xl bg-dutch-700 text-white hover:bg-dutch-600 transition-colors text-sm"
          >
            <RefreshCw size={16} /> Nuevo juego
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <div className="text-xs font-semibold text-gray-400 mb-1">NEERLANDÉS</div>
            {pairs.map(p => (
              <button
                key={p.id}
                disabled={matched.has(p.id)}
                onClick={() => !matched.has(p.id) && setSelectedDutch(p.id)}
                className={btnClass(p.id, selectedDutch === p.id)}
              >
                {p.dutch}
              </button>
            ))}
          </div>
          <div className="space-y-2">
            <div className="text-xs font-semibold text-gray-400 mb-1">ESPAÑOL</div>
            {shuffledSpanish.map(p => (
              <button
                key={p.id}
                disabled={matched.has(p.id)}
                onClick={() => !matched.has(p.id) && setSelectedSpanish(p.id)}
                className={btnClass(p.id, selectedSpanish === p.id)}
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
