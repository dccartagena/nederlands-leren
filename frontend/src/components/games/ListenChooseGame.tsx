import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchListenChoose } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { Volume2, RefreshCw } from 'lucide-react'
import { motion } from 'framer-motion'

export default function ListenChooseGame() {
  const level = useAppStore((s) => s.level)
  const [selected, setSelected] = useState<number | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['listen-choose', level],
    queryFn: () => fetchListenChoose(level),
  })

  const playAudio = () => {
    if (!data?.audio_files?.length) return
    const audio = new Audio(`/audio/${data.audio_files[0]}`)
    audio.play().catch(() => {})
  }

  const next = () => {
    setSelected(null)
    refetch()
  }

  if (isLoading || !data) return <div className="py-12 text-center text-gray-400">Cargando…</div>

  const correct = data.correct_id
  const options: Array<{ id: number; spanish: string; image_url?: string }> = data.options

  return (
    <div className="flex flex-col items-center gap-6">
      <p className="text-center text-sm text-gray-600 dark:text-gray-400">
        Escucha y elige la palabra correcta
      </p>

      <button
        onClick={playAudio}
        className="flex h-24 w-24 flex-col items-center justify-center gap-1 rounded-full bg-brand-100 text-sm font-medium text-brand-700 transition-colors hover:bg-brand-200 dark:bg-brand-900 dark:text-brand-300 dark:hover:bg-brand-600"
      >
        <Volume2 size={32} />
        Escuchar
      </button>

      <div className="grid w-full max-w-sm grid-cols-2 gap-3">
        {options.map((opt) => {
          const isCorrect = opt.id === correct
          const isSelected = selected === opt.id
          let cls =
            'p-4 rounded-xl border-2 text-center font-medium transition-colors cursor-pointer '
          if (selected !== null) {
            cls += isCorrect
              ? 'border-green-500 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300'
              : isSelected
                ? 'border-red-400 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300'
                : 'border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-600'
          } else {
            cls +=
              'border-gray-200 dark:border-gray-600 hover:border-brand-400 hover:bg-brand-50 dark:hover:border-brand-400 dark:hover:bg-brand-950 text-gray-800 dark:text-gray-200'
          }
          return (
            <motion.button
              key={opt.id}
              whileTap={{ scale: 0.97 }}
              className={cls}
              onClick={() => selected === null && setSelected(opt.id)}
            >
              {opt.image_url && (
                <img
                  src={opt.image_url}
                  alt=""
                  className="mx-auto mb-2 h-12 w-12 rounded object-cover"
                />
              )}
              {opt.spanish}
            </motion.button>
          )
        })}
      </div>

      {selected !== null && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-3 text-center"
        >
          <div
            className={`text-lg font-semibold ${selected === correct ? 'text-green-600' : 'text-red-600'}`}
          >
            {selected === correct
              ? '¡Correcto! 🎉'
              : `Incorrecto. Respuesta: ${options.find((o) => o.id === correct)?.spanish}`}
          </div>
          <button
            onClick={next}
            className="mx-auto flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2 text-sm text-white transition-colors hover:bg-brand-600"
          >
            <RefreshCw size={16} /> Siguiente
          </button>
        </motion.div>
      )}
    </div>
  )
}
