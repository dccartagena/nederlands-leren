import { http, HttpResponse } from 'msw'

const BASE = '/api/v1'

// ── Fixtures ─────────────────────────────────────────────────────────────────

export const mockVocabItem = {
  id: 1,
  dutch_word: 'hond',
  spanish: 'perro',
  article: 'de',
  level: 'a0',
  theme: 'animales',
}

export const mockVocabList = [
  mockVocabItem,
  { ...mockVocabItem, id: 2, dutch_word: 'kat', spanish: 'gato' },
  { ...mockVocabItem, id: 3, dutch_word: 'vis', spanish: 'pez' },
  { ...mockVocabItem, id: 4, dutch_word: 'vogel', spanish: 'pájaro' },
  { ...mockVocabItem, id: 5, dutch_word: 'paard', spanish: 'caballo', article: 'het' },
]

export const mockUserProgress = {
  id: 1,
  username: 'learner',
  xp_total: 120,
  streak_days: 3,
  last_activity_date: '2026-04-10',
}

export const mockDueCards = [
  {
    id: 1,
    vocab_item: mockVocabItem,
    state: 0,
    reps: 0,
    lapses: 0,
  },
]

export const mockMasteryStats = {
  mastered_words: 12,
  enrolled_words: 40,
  review_words: 20,
  stories_completed: 2,
  streak_freezes: 1,
}

export const mockQuests = [
  { id: 'review_10', title_es: 'Repasa 10 tarjetas', target: 10, progress: 3, done: false },
  { id: 'story_1', title_es: 'Completa 1 historia', target: 1, progress: 0, done: false },
  { id: 'xp_40', title_es: 'Gana 40 XP', target: 40, progress: 40, done: true },
]

export const mockStrands = [
  { strand: 'input', sessions: 2, exercises: 6, xp: 60 },
  { strand: 'output', sessions: 1, exercises: 5, xp: 25 },
  { strand: 'study', sessions: 4, exercises: 4, xp: 40 },
  { strand: 'fluency', sessions: 0, exercises: 0, xp: 0 },
]

export const mockJobs = [
  {
    name: 'seed_content',
    description: 'Carga el contenido de data/ en la base de datos (idempotente)',
    enabled: true,
    interval_hours: 24,
    last_run_at: '2026-04-10T08:00:00Z',
    last_status: 'ok',
    detail: '0 vocab, 0 grammar, 0 stories seeded; 0 attribution entries',
    duration_ms: 120,
  },
  {
    name: 'backup_progress',
    description: 'Copia de seguridad diaria del progreso en data/backups/',
    enabled: true,
    interval_hours: 24,
    last_run_at: null,
    last_status: null,
    detail: null,
    duration_ms: null,
  },
]

export const mockReviewResponse = {
  card_id: 1,
  next_due: '2026-04-11T10:00:00Z',
  stability: 1.5,
  state: 1,
  xp_earned: 10,
  new_achievements: [],
}

export const mockGrammarTopics = [
  { id: 1, slug: 'de-het', name_nl: 'De en het', name_es: 'Los artículos', level: 'a0' },
]

export const mockStories = [
  {
    id: 1,
    slug: 'het-huis',
    title_nl: 'Het huis',
    title_es: 'La casa',
    level: 'a0',
    content_nl: 'Er was een huis.',
    content_es: 'Había una casa.',
    questions_json: [
      {
        question_es: '¿Qué había?',
        options: ['een huis', 'een auto', 'een kat'],
        answer_index: 0,
      },
    ],
  },
]

export const mockFillBlank = {
  sentence_with_blank: 'De ___ loopt in het park.',
  sentence_es: 'El ___ pasea en el parque.',
  correct_id: 1,
  correct_word: 'hond',
  options: [
    { id: 1, dutch_word: 'hond', article: 'de' },
    { id: 2, dutch_word: 'kat', article: 'de' },
    { id: 3, dutch_word: 'vis', article: 'de' },
    { id: 4, dutch_word: 'vogel', article: 'de' },
  ],
}

export const mockUnscramble = {
  vocab_id: 1,
  shuffled_words: ['park', 'De', 'in', 'het', 'loopt', 'hond'],
  correct_sentence: 'De hond loopt in het park.',
  sentence_es: 'El perro camina en el parque.',
  trailing_punct: '.',
}

export const mockListenChoose = {
  correct_id: 1,
  correct_dutch: 'hond',
  audio_files: ['gtts_abc123.mp3'],
  options: [
    { id: 1, spanish: 'perro', image_url: null },
    { id: 2, spanish: 'gato', image_url: null },
    { id: 3, spanish: 'pez', image_url: null },
    { id: 4, spanish: 'pájaro', image_url: null },
  ],
}

export const mockWordMatch = {
  pairs: [
    { id: 1, dutch: 'hond', spanish: 'perro' },
    { id: 2, dutch: 'kat', spanish: 'gato' },
    { id: 3, dutch: 'vis', spanish: 'pez' },
  ],
}

// ── Handlers ─────────────────────────────────────────────────────────────────

export const handlers = [
  // Vocabulary
  http.get(`${BASE}/vocabulary/`, () => HttpResponse.json(mockVocabList)),
  http.get(`${BASE}/vocabulary/:id`, () => HttpResponse.json(mockVocabItem)),

  // Progress
  http.get(`${BASE}/progress/user`, () => HttpResponse.json(mockUserProgress)),
  http.get(`${BASE}/progress/due`, () => HttpResponse.json(mockDueCards)),
  http.get(`${BASE}/progress/history`, () => HttpResponse.json([])),
  http.get(`${BASE}/progress/stats`, () => HttpResponse.json(mockMasteryStats)),
  http.get(`${BASE}/progress/quests`, () => HttpResponse.json(mockQuests)),
  http.get(`${BASE}/progress/strands`, () => HttpResponse.json(mockStrands)),

  // Admin / maintenance
  http.get(`${BASE}/admin/jobs`, () => HttpResponse.json(mockJobs)),
  http.post(`${BASE}/admin/jobs/:name/run`, ({ params }) =>
    HttpResponse.json({
      name: params.name,
      started: true,
      background: false,
      status: 'ok',
      detail: 'done',
    })
  ),
  http.post(`${BASE}/progress/session-complete`, () =>
    HttpResponse.json({ xp_earned: 25, new_achievements: [] })
  ),
  http.post(`${BASE}/progress/review`, () => HttpResponse.json(mockReviewResponse)),
  http.post(`${BASE}/progress/enroll/:id`, () => HttpResponse.json({ id: 1, vocab_item_id: 1 })),

  // Grammar
  http.get(`${BASE}/grammar/`, () => HttpResponse.json(mockGrammarTopics)),
  http.get(`${BASE}/grammar/:slug`, () => HttpResponse.json(mockGrammarTopics[0])),

  // Stories
  http.get(`${BASE}/stories/`, () => HttpResponse.json(mockStories)),
  http.get(`${BASE}/stories/:slug`, () => HttpResponse.json(mockStories[0])),

  // LLM
  http.post(`${BASE}/llm/explain`, () =>
    HttpResponse.json({ explanation: 'Hond significa perro.' })
  ),
  http.post(`${BASE}/llm/feedback`, () =>
    HttpResponse.json({ feedback: 'La respuesta correcta es hond.' })
  ),
  http.post(`${BASE}/llm/chat`, () => HttpResponse.json({ reply: 'Hallo! Hoe gaat het?' })),

  // Exercises
  http.get(`${BASE}/exercises/listen-choose`, () => HttpResponse.json(mockListenChoose)),
  http.get(`${BASE}/exercises/word-match`, () => HttpResponse.json(mockWordMatch)),
  http.get(`${BASE}/exercises/fill-blank`, () => HttpResponse.json(mockFillBlank)),
  http.get(`${BASE}/exercises/unscramble`, () => HttpResponse.json(mockUnscramble)),
]
