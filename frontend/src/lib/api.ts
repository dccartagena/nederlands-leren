import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export default api

// ── Vocabulary ───────────────────────────────────────────────────────────────
export interface VocabularyItem {
  id: number
  dutch_word: string
  spanish: string
  article?: string
  plural?: string
  word_type?: string
  level: string
  theme: string
  image_url?: string
  notes?: string
  example_nl?: string
  example_es?: string
  audio_files: AudioFile[]
}

export interface AudioFile {
  id: number
  file_path: string
  source?: string
  license?: string
  sentence_text_nl?: string
}

export const fetchVocabulary = (level?: string, theme?: string, limit = 50) =>
  api.get<VocabularyItem[]>('/vocabulary/', { params: { level, theme, limit } }).then(r => r.data)

export const fetchVocabularyItem = (id: number) =>
  api.get<VocabularyItem>(`/vocabulary/${id}`).then(r => r.data)

// ── Progress ─────────────────────────────────────────────────────────────────
export interface UserProgress {
  id: number
  username: string
  xp_total: number
  streak_days: number
  last_activity_date?: string
}

export interface DueCard {
  id: number
  vocab_item: VocabularyItem
  state: number
  reps: number
  lapses: number
}

export interface ReviewResponse {
  card_id: number
  next_due: string
  stability: number
  state: number
  xp_earned: number
}

export const fetchUserProgress = () =>
  api.get<UserProgress>('/progress/user').then(r => r.data)

export const fetchDueCards = (limit = 20) =>
  api.get<DueCard[]>('/progress/due', { params: { limit } }).then(r => r.data)

export const submitReview = (card_id: number, rating: 1 | 2 | 3 | 4) =>
  api.post<ReviewResponse>('/progress/review', { card_id, rating }).then(r => r.data)

export const enrollCard = (vocab_item_id: number) =>
  api.post(`/progress/enroll/${vocab_item_id}`).then(r => r.data)

// ── Grammar ──────────────────────────────────────────────────────────────────
export interface GrammarTopic {
  id: number
  slug: string
  name_nl: string
  name_es: string
  level: string
  description_es?: string
  examples_json?: Array<{ nl: string; es: string; notes?: string }>
}

export const fetchGrammar = (level?: string) =>
  api.get<GrammarTopic[]>('/grammar/', { params: { level } }).then(r => r.data)

// ── Stories ──────────────────────────────────────────────────────────────────
export interface Story {
  id: number
  slug: string
  title_nl: string
  title_es: string
  level: string
  content_nl?: string
  content_es?: string
  audio_path?: string
  questions_json?: Array<{
    question_es: string
    options: string[]
    answer_index: number
    explanation_es?: string
  }>
  theme?: string
}

export const fetchStories = (level?: string) =>
  api.get<Story[]>('/stories/', { params: { level } }).then(r => r.data)

export const fetchStory = (slug: string) =>
  api.get<Story>(`/stories/${slug}`).then(r => r.data)

// ── LLM ──────────────────────────────────────────────────────────────────────
export const explainWord = (word_or_phrase: string, context_sentence?: string) =>
  api.post<{ explanation: string }>('/llm/explain', { word_or_phrase, context_sentence }).then(r => r.data)

export const getFeedback = (question: string, correct_answer: string, user_answer: string) =>
  api.post<{ feedback: string }>('/llm/feedback', { question, correct_answer, user_answer }).then(r => r.data)

export type LLMProvider = 'default' | 'ollama' | 'openai' | 'anthropic' | 'mistral' | 'gemini'

export const sendChat = (
  messages: Array<{ role: string; content: string }>,
  provider: LLMProvider = 'default'
) =>
  api
    .post<{ reply: string }>('/llm/chat', {
      messages,
      provider: provider === 'default' ? undefined : provider,
    })
    .then(r => r.data)

// ── Exercises ────────────────────────────────────────────────────────────────
export const fetchListenChoose = (level = 'a0', theme?: string) =>
  api.get('/exercises/listen-choose', { params: { level, theme } }).then(r => r.data)

export const fetchWordMatch = (level = 'a0', theme?: string, count = 6) =>
  api.get('/exercises/word-match', { params: { level, theme, count } }).then(r => r.data)
