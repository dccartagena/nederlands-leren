import { useState } from 'react'
import { getFeedback } from '@/lib/api'

export function useFeedback() {
  const [feedback, setFeedback] = useState<string | null>(null)
  const [fbLoading, setFbLoading] = useState(false)

  const loadFeedback = async (question: string, correct: string, given: string) => {
    setFbLoading(true)
    setFeedback(null)
    try {
      const { feedback: fb } = await getFeedback(question, correct, given)
      setFeedback(fb)
    } catch {
      /* ignore */
    } finally {
      setFbLoading(false)
    }
  }

  const reset = () => setFeedback(null)

  return { feedback, fbLoading, loadFeedback, reset }
}
