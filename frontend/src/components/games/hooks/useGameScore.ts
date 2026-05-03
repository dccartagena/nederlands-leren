import { useState } from 'react'

export function useGameScore() {
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const recordAnswer = (isCorrect: boolean) =>
    setScore((s) => ({ correct: s.correct + (isCorrect ? 1 : 0), total: s.total + 1 }))
  const reset = () => setScore({ correct: 0, total: 0 })
  return { score, recordAnswer, reset }
}
