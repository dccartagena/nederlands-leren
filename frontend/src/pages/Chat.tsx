import { useState, useRef, useEffect } from 'react'
import { sendChat } from '@/lib/api'
import type { LLMProvider } from '@/lib/api'
import { Send, Bot, User } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '¡Hola! Soy tu asistente para aprender neerlandés. ¿Qué quieres practicar hoy?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [provider, setProvider] = useState<LLMProvider>('default')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return
    const newMessages: Message[] = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    try {
      const { reply } = await sendChat(newMessages, provider)
      setMessages((m) => [...m, { role: 'assistant', content: reply }])
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: 'Lo siento, hay un problema de conexión.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-[calc(100dvh-10rem)] flex-col md:h-[calc(100dvh-8rem)]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h1 className="text-xl font-bold">Chat con IA</h1>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value as LLMProvider)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
          disabled={loading}
        >
          <option value="default">Auto</option>
          <option value="gemini">Gemini</option>
          <option value="ollama">Ollama</option>
        </select>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto pb-2">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <Bot size={20} className="mt-1 shrink-0 text-brand-600" />
              )}
              <div
                className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'rounded-br-sm bg-brand-500 text-white'
                    : 'rounded-bl-sm border border-gray-200 bg-white text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200'
                }`}
              >
                {msg.content}
              </div>
              {msg.role === 'user' && <User size={20} className="mt-1 shrink-0 text-gray-400" />}
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <div className="flex gap-2">
            <Bot size={20} className="mt-1 shrink-0 text-brand-600" />
            <div className="animate-pulse rounded-2xl rounded-bl-sm border border-gray-200 bg-white px-4 py-2 text-sm text-gray-400 dark:border-gray-700 dark:bg-gray-800">
              Escribiendo…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 border-t border-gray-200 pt-3 dark:border-gray-700">
        <input
          className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:placeholder-gray-500"
          placeholder="Escribe en neerlandés o español…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="rounded-xl bg-brand-500 p-2 text-white transition-colors hover:bg-brand-600 disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
