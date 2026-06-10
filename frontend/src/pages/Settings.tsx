import { useRef, useState } from 'react'
import { useAppStore } from '@/stores/appStore'
import { exportProgress } from '@/lib/api'
import { Download, Upload, Sun, Moon, Volume2, VolumeX, Leaf } from 'lucide-react'

export default function Settings() {
  const {
    level,
    setLevel,
    theme,
    setTheme,
    audioEnabled,
    setAudioEnabled,
    llmProvider,
    setLlmProvider,
    sereneMode,
    setSereneMode,
  } = useAppStore()
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const isDark = theme !== 'light'

  const handleExport = async () => {
    const blob = await exportProgress()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `progress-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setImportMsg(null)
    try {
      const text = await file.text()
      const payload = JSON.parse(text)
      const res = await fetch('/api/v1/progress/import/json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      setImportMsg(`✓ ${data.imported_cards} tarjetas importadas`)
    } catch {
      setImportMsg('Error al importar. Comprueba el archivo.')
    }
    setImporting(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-bold">Ajustes</h1>

      {/* Level */}
      <Section title="Nivel actual">
        <div className="flex gap-3">
          {(['a0', 'a1'] as const).map((l) => (
            <button
              key={l}
              onClick={() => setLevel(l)}
              className={`flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all ${
                level === l
                  ? 'bg-brand-500 text-white shadow-md shadow-brand-200 dark:shadow-none'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </Section>

      {/* Audio */}
      <Section title="Audio">
        <button
          onClick={() => setAudioEnabled(!audioEnabled)}
          className={`flex w-full items-center justify-between rounded-xl border p-4 transition-all ${
            audioEnabled
              ? 'border-brand-200 bg-brand-50 dark:border-brand-800 dark:bg-brand-950/50'
              : 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800'
          }`}
        >
          <div className="flex items-center gap-3">
            {audioEnabled ? (
              <Volume2 size={18} className="text-brand-600 dark:text-brand-400" />
            ) : (
              <VolumeX size={18} className="text-gray-400" />
            )}
            <span className="text-sm font-medium">
              {audioEnabled ? 'Sonido activado' : 'Sonido desactivado'}
            </span>
          </div>
          <Toggle on={audioEnabled} />
        </button>
      </Section>

      {/* Serene mode */}
      <Section title="Modo sereno">
        <button
          onClick={() => setSereneMode(!sereneMode)}
          className={`flex w-full items-center justify-between rounded-xl border p-4 transition-all ${
            sereneMode
              ? 'border-teal-200 bg-teal-50 dark:border-teal-800 dark:bg-teal-950/50'
              : 'border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800'
          }`}
        >
          <div className="flex items-center gap-3">
            <Leaf
              size={18}
              className={sereneMode ? 'text-teal-600 dark:text-teal-400' : 'text-gray-400'}
            />
            <span className="text-left text-sm font-medium">
              {sereneMode ? 'Modo sereno activado' : 'Modo sereno desactivado'}
              <span className="mt-0.5 block text-xs font-normal text-gray-500 dark:text-gray-400">
                Oculta XP y combos para estudiar sin puntuaciones
              </span>
            </span>
          </div>
          <Toggle on={sereneMode} />
        </button>
      </Section>

      {/* LLM Provider */}
      <Section title="Proveedor de IA">
        <div className="flex gap-3">
          {(['default', 'gemini', 'ollama'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setLlmProvider(p)}
              className={`flex-1 rounded-xl py-2.5 text-sm font-medium capitalize transition-all ${
                llmProvider === p
                  ? 'bg-sky-500 text-white shadow-md shadow-sky-200 dark:shadow-none'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {p === 'default' ? 'Auto' : p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </Section>

      {/* Appearance */}
      <Section title="Apariencia">
        <button
          onClick={() => setTheme(isDark ? 'light' : 'dark')}
          className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-gray-50 p-4 transition-all hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700"
        >
          <div className="flex items-center gap-3">
            {isDark ? (
              <Moon size={18} className="text-sky-400" />
            ) : (
              <Sun size={18} className="text-yellow-500" />
            )}
            <span className="text-sm font-medium">{isDark ? 'Modo oscuro' : 'Modo claro'}</span>
          </div>
          <Toggle on={isDark} color="sky" />
        </button>
      </Section>

      {/* Progress backup */}
      <Section title="Copia de seguridad">
        <div className="space-y-3">
          <button
            onClick={handleExport}
            className="flex w-full items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium transition-all hover:border-brand-400 dark:border-gray-700 dark:bg-gray-800"
          >
            <Download size={16} className="text-brand-600 dark:text-brand-400" />
            Exportar progreso
          </button>

          <label className="flex w-full cursor-pointer items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium transition-all hover:border-brand-400 dark:border-gray-700 dark:bg-gray-800">
            {importing ? (
              <span className="text-sm text-gray-400">Importando…</span>
            ) : (
              <>
                <Upload size={16} className="text-sky-600 dark:text-sky-400" />
                Importar progreso
              </>
            )}
            <input
              ref={fileRef}
              type="file"
              accept=".json"
              className="sr-only"
              onChange={handleImport}
            />
          </label>

          {importMsg && (
            <p
              className={`px-1 text-sm ${importMsg.startsWith('✓') ? 'text-brand-600 dark:text-brand-400' : 'text-red-500'}`}
            >
              {importMsg}
            </p>
          )}
        </div>
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
        {title}
      </h2>
      {children}
    </div>
  )
}

function Toggle({ on, color = 'brand' }: { on: boolean; color?: 'brand' | 'sky' }) {
  const track = on
    ? color === 'sky'
      ? 'bg-sky-500'
      : 'bg-brand-500'
    : 'bg-gray-300 dark:bg-gray-600'
  return (
    <div className={`relative h-6 w-10 rounded-full transition-colors ${track}`}>
      <div
        className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-transform ${
          on ? 'translate-x-5' : 'translate-x-1'
        }`}
      />
    </div>
  )
}
