import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchVocabulary, fetchGrammar } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'

export default function Lesson() {
  const { level: paramLevel } = useParams()
  const storeLevel = useAppStore(s => s.level)
  const level = (paramLevel as 'a0' | 'a1') || storeLevel

  const { data: vocab, isLoading: loadingVocab } = useQuery({
    queryKey: ['vocabulary', level],
    queryFn: () => fetchVocabulary(level),
  })
  const { data: grammar, isLoading: loadingGrammar } = useQuery({
    queryKey: ['grammar', level],
    queryFn: () => fetchGrammar(level),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Lección — Nivel {level.toUpperCase()}</h1>

      {/* Vocabulary section */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Vocabulario ({vocab?.length ?? '…'})</h2>
        {loadingVocab ? (
          <p className="text-gray-500 dark:text-gray-400">Cargando…</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {vocab?.map(item => (
              <div key={item.id} className="p-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                <div className="font-semibold text-dutch-700 dark:text-dutch-400">
                  {item.article ? `${item.article} ` : ''}{item.dutch_word}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">{item.spanish}</div>
                {item.example_nl && (
                  <div className="text-xs text-gray-400 dark:text-gray-500 mt-1 italic">{item.example_nl}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Grammar section */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Gramática</h2>
        {loadingGrammar ? (
          <p className="text-gray-500 dark:text-gray-400">Cargando…</p>
        ) : (
          <div className="space-y-3">
            {grammar?.map(topic => (
              <div key={topic.id} className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                <div className="font-semibold">{topic.name_es}</div>
                {topic.description_es && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{topic.description_es}</p>
                )}
              </div>
            ))}
            {grammar?.length === 0 && <p className="text-gray-400 dark:text-gray-500 text-sm">No hay temas de gramática aún.</p>}
          </div>
        )}
      </section>
    </div>
  )
}
