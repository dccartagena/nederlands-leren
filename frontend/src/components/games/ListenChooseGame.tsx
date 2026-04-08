import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchListenChoose } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { Volume2, RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

export default function ListenChooseGame() {
  const level = useAppStore(s => s.level)
  const [selected, setSelected] = useState<number | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['listen-choose', level],
    queryFn: () => fetchListenChoose(level),
  })

  const playAudio = () => {
    if (!data?.audio_files?.length) return
    const audio = new Audio(`/${data.audio_files[0]}`)
    audio.play().catch(() => {})
  }

  const next = () => {
    setSelected(null)
    refetch()
  }

  if (isLoading || !data) return <div className="text-gray-400 text-center py-12">Cargando…</div>

  const correct = data.correct_id
  const options: Array<{ id: number; spanish: string; image_url?: string }> = data.options

  return (
    <div className="flex flex-col items-center gap-6">
      <p className="text-gray-600 dark:text-gray-400 text-sm text-center">Escucha y elige la palabra correcta</p>

      <button
        onClick={playAudio}
        className="w-24 h-24 rounded-full bg-dutch-100 hover:bg-dutch-200 dark:bg-dutch-900 dark:hover:bg-dutch-800 text-dutch-700 dark:text-dutch-300 flex flex-col items-center justify-center gap-1 transition-colors text-sm font-medium"
      >
        <Volume2 size={32} />
        Escuchar
      </button>

      <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
        {options.map(opt => {
          const isCorrect = opt.id === correct
          const isSelected = selected === opt.id
          let cls = 'p-4 rounded-xl border-2 text-center font-medium transition-colors cursor-pointer '
          if (selected !== null) {
            cls += isCorrect ? 'border-green-500 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300' :
              isSelected ? 'border-red-400 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300' : 'border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-600'
          } else {
            cls += 'border-gray-200 dark:border-gray-600 hover:border-dutch-400 hover:bg-dutch-50 dark:hover:border-dutch-500 dark:hover:bg-dutch-950 text-gray-800 dark:text-gray-200'
          }
          return (
            <motion.button
              key={opt.id}
              whileTap={{ scale: 0.97 }}
              className={cls}
              onClick={() => selected === null && setSelected(opt.id)}
            >
              {opt.image_url && (
                <img src={opt.image_url} alt="" className="w-12 h-12 object-cover rounded mx-auto mb-2" />
              )}
              {opt.spanish}
            </motion.button>
          )
        })}
      </div>

      {selected !== null && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center space-y-3">
          <div className={`text-lg font-semibold ${selected === correct ? 'text-green-600' : 'text-red-600'}`}>
            {selected === correct ? '¡Correcto! 🎉' : `Incorrecto. Respuesta: ${options.find(o => o.id === correct)?.spanish}`}
          </div>
          <button
            onClick={next}
            className="flex items-center gap-2 mx-auto px-5 py-2 rounded-xl bg-dutch-700 text-white hover:bg-dutch-600 transition-colors text-sm"
          >
            <RefreshCw size={16} /> Siguiente
          </button>
        </motion.div>
      )}
    </div>
  )
}
