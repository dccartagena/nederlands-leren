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
    { role: 'assistant', content: '¡Hola! Soy tu asistente para aprender neerlandés. ¿Qué quieres practicar hoy?' },
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
      setMessages(m => [...m, { role: 'assistant', content: reply }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: 'Lo siento, hay un problema de conexión.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100dvh-10rem)] md:h-[calc(100dvh-8rem)]">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h1 className="text-xl font-bold">Chat con IA</h1>
        <select
          value={provider}
          onChange={e => setProvider(e.target.value as LLMProvider)}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm"
          disabled={loading}
        >
          <option value="default">Proveedor por defecto</option>
          <option value="gemini">Gemini API</option>
          <option value="ollama">Ollama local</option>
          <option value="openai">OpenAI API</option>
          <option value="anthropic">Anthropic API</option>
          <option value="mistral">Mistral API</option>
        </select>
      </div>
      <div className="flex-1 overflow-y-auto space-y-3 pb-2">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && <Bot size={20} className="mt-1 text-dutch-600 shrink-0" />}
              <div
                className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-dutch-700 text-white rounded-br-sm'
                    : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-sm'
                }`}
              >
                {msg.content}
              </div>
              {msg.role === 'user' && <User size={20} className="mt-1 text-gray-400 shrink-0" />}
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <div className="flex gap-2">
            <Bot size={20} className="mt-1 text-dutch-600 shrink-0" />
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-2 rounded-2xl rounded-bl-sm text-sm text-gray-400 animate-pulse">
              Escribiendo…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-2 pt-3 border-t border-gray-200 dark:border-gray-700">
        <input
          className="flex-1 px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-dutch-500 text-sm"
          placeholder="Escribe en neerlandés o español…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="p-2 rounded-xl bg-dutch-700 text-white disabled:opacity-40 hover:bg-dutch-600 transition-colors"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
