import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchVocabulary, fetchGrammar, enrollAll } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { BookOpen, Check } from 'lucide-react'

export default function Lesson() {
  const { level: paramLevel } = useParams()
  const storeLevel = useAppStore((s) => s.level)
  const level = (paramLevel as 'a0' | 'a1') || storeLevel
  const [enrolling, setEnrolling] = useState(false)
  const [enrolled, setEnrolled] = useState(false)

  const { data: vocab, isLoading: loadingVocab } = useQuery({
    queryKey: ['vocabulary', level],
    queryFn: () => fetchVocabulary(level),
  })
  const { data: grammar, isLoading: loadingGrammar } = useQuery({
    queryKey: ['grammar', level],
    queryFn: () => fetchGrammar(level),
  })

  const handleEnrollAll = async () => {
    if (!vocab?.length || enrolling) return
    setEnrolling(true)
    try {
      await enrollAll(vocab.map((v) => v.id))
      setEnrolled(true)
    } catch {
      /* ignore individual errors */
    }
    setEnrolling(false)
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Nivel {level.toUpperCase()}</h1>
        <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-brand-700 dark:bg-brand-950 dark:text-brand-300">
          CEFR {level.toUpperCase()}
        </span>
      </div>

      {/* Vocabulary section */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-gray-700 dark:text-gray-300">
            Vocabulario{vocab ? ` (${vocab.length})` : ''}
          </h2>
          {vocab && vocab.length > 0 && (
            <button
              onClick={handleEnrollAll}
              disabled={enrolling || enrolled}
              className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-50"
            >
              {enrolled ? <Check size={14} /> : <BookOpen size={14} />}
              {enrolled ? 'Añadidas al repaso' : enrolling ? 'Añadiendo…' : 'Añadir todo al repaso'}
            </button>
          )}
        </div>

        {loadingVocab ? (
          <p className="text-sm text-gray-400">Cargando…</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {vocab?.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-gray-200 bg-white p-4 transition-colors hover:border-brand-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-brand-700"
              >
                <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">
                  {item.article ? `${item.article} ` : ''}
                  {item.dutch_word}
                </div>
                <div className="mt-0.5 text-sm text-gray-600 dark:text-gray-400">
                  {item.spanish}
                </div>
                {item.example_nl && (
                  <div className="mt-2 text-xs italic leading-snug text-gray-400 dark:text-gray-500">
                    {item.example_nl}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Grammar section */}
      <section>
        <h2 className="mb-4 font-semibold text-gray-700 dark:text-gray-300">Gramática</h2>
        {loadingGrammar ? (
          <p className="text-sm text-gray-400">Cargando…</p>
        ) : (
          <div className="space-y-3">
            {grammar?.map((topic) => (
              <div
                key={topic.id}
                className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="text-sm font-semibold">{topic.name_es}</div>
                {topic.description_es && (
                  <p className="mt-1 text-sm leading-relaxed text-gray-600 dark:text-gray-400">
                    {topic.description_es}
                  </p>
                )}
                {topic.examples_json && topic.examples_json.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {topic.examples_json.map((ex, i) => (
                      <div
                        key={i}
                        className="flex gap-3 rounded-lg bg-gray-50 px-3 py-2 text-xs dark:bg-gray-700/50"
                      >
                        <span className="min-w-0 font-medium text-sky-700 dark:text-sky-300">
                          {ex.nl}
                        </span>
                        <span className="text-gray-400">→</span>
                        <span className="min-w-0 text-gray-600 dark:text-gray-400">{ex.es}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {grammar?.length === 0 && (
              <p className="text-sm text-gray-400 dark:text-gray-500">
                No hay temas de gramática aún.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
