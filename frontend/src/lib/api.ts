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
}

export const fetchVocabulary = (level?: string, theme?: string, limit = 50) =>
  api.get<VocabularyItem[]>('/vocabulary/', { params: { level, theme, limit } }).then((r) => r.data)

export const fetchVocabularyItem = (id: number) =>
  api.get<VocabularyItem>(`/vocabulary/${id}`).then((r) => r.data)

// ── Progress ─────────────────────────────────────────────────────────────────
export interface UserProgress {
  id: number
  username: string
  xp_total: number
  streak_days: number
  last_activity_date?: string
  settings_json?: {
    achievements?: Array<{ slug: string; earned_at: string }>
    completed_stories?: string[]
  }
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
  new_achievements: string[]
}

export interface XpHistoryEntry {
  date: string
  xp: number
}

export interface Achievement {
  slug: string
  earned_at: string
}

export const fetchUserProgress = () => api.get<UserProgress>('/progress/user').then((r) => r.data)

export const fetchDueCards = (limit = 20) =>
  api.get<DueCard[]>('/progress/due', { params: { limit } }).then((r) => r.data)

export const submitReview = (card_id: number, rating: 1 | 2 | 3 | 4, combo = false) =>
  api.post<ReviewResponse>('/progress/review', { card_id, rating, combo }).then((r) => r.data)

export const enrollCard = (vocab_item_id: number) =>
  api.post(`/progress/enroll/${vocab_item_id}`).then((r) => r.data)

export const enrollAll = (ids: number[]) => Promise.all(ids.map((id) => enrollCard(id)))

export const fetchXpHistory = (days = 7) =>
  api.get<XpHistoryEntry[]>('/progress/history', { params: { days } }).then((r) => r.data)

export interface MasteryStats {
  mastered_words: number
  enrolled_words: number
  review_words: number
  stories_completed: number
  streak_freezes: number
}

export const fetchMasteryStats = () => api.get<MasteryStats>('/progress/stats').then((r) => r.data)

export interface Quest {
  id: string
  title_es: string
  target: number
  progress: number
  done: boolean
}

export const fetchQuests = () => api.get<Quest[]>('/progress/quests').then((r) => r.data)

export const fetchSettings = () =>
  api.get<Record<string, unknown>>('/progress/settings').then((r) => r.data)

export const updateSettings = (data: Record<string, unknown>) =>
  api.put<Record<string, unknown>>('/progress/settings', data).then((r) => r.data)

export const submitStoryComplete = (
  story_slug: string,
  correct_count: number,
  total_questions: number
) =>
  api
    .post<{ xp_earned: number; new_achievements: string[] }>('/progress/story-complete', {
      story_slug,
      correct_count,
      total_questions,
    })
    .then((r) => r.data)

export const exportProgress = () =>
  api.get('/progress/export', { responseType: 'blob' }).then((r) => r.data)

export const importProgress = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api
    .post<{ imported_cards: number }>('/progress/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

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
  api.get<GrammarTopic[]>('/grammar/', { params: { level } }).then((r) => r.data)

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
  api.get<Story[]>('/stories/', { params: { level } }).then((r) => r.data)

export const fetchStory = (slug: string) => api.get<Story>(`/stories/${slug}`).then((r) => r.data)

// ── LLM ──────────────────────────────────────────────────────────────────────
export const explainWord = (word_or_phrase: string, context_sentence?: string) =>
  api
    .post<{ explanation: string }>('/llm/explain', { word_or_phrase, context_sentence })
    .then((r) => r.data)

export const getFeedback = (question: string, correct_answer: string, user_answer: string) =>
  api
    .post<{ feedback: string }>('/llm/feedback', { question, correct_answer, user_answer })
    .then((r) => r.data)

export type LLMProvider = 'default' | 'ollama' | 'gemini'

export const sendChat = (
  messages: Array<{ role: string; content: string }>,
  provider: LLMProvider = 'default'
) =>
  api
    .post<{ reply: string }>('/llm/chat', {
      messages,
      provider: provider === 'default' ? undefined : provider,
    })
    .then((r) => r.data)

// ── Exercises ────────────────────────────────────────────────────────────────
export const fetchListenChoose = (level = 'a0', theme?: string) =>
  api.get('/exercises/listen-choose', { params: { level, theme } }).then((r) => r.data)

export const fetchWordMatch = (level = 'a0', theme?: string, count = 6) =>
  api.get('/exercises/word-match', { params: { level, theme, count } }).then((r) => r.data)

export interface FillBlankExercise {
  sentence_with_blank: string
  sentence_es: string
  correct_id: number
  correct_word: string
  options: Array<{ id: number; dutch_word: string; article?: string }>
}

export const fetchFillBlank = (level = 'a0', theme?: string) =>
  api
    .get<FillBlankExercise>('/exercises/fill-blank', { params: { level, theme } })
    .then((r) => r.data)

export interface UnscrambleExercise {
  vocab_id: number
  shuffled_words: string[]
  correct_sentence: string
  sentence_es: string
  trailing_punct: string
}

export const fetchUnscramble = (level = 'a0', theme?: string) =>
  api
    .get<UnscrambleExercise>('/exercises/unscramble', { params: { level, theme } })
    .then((r) => r.data)
