import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  fetchVocabulary,
  fetchVocabularyItem,
  fetchUserProgress,
  fetchDueCards,
  submitReview,
  enrollCard,
  fetchGrammar,
  fetchStories,
  fetchStory,
  explainWord,
  getFeedback,
  sendChat,
  fetchFillBlank,
  fetchUnscramble,
  fetchListenChoose,
  fetchWordMatch,
} from '@/lib/api'
import { mockVocabList, mockVocabItem } from '@/test/mocks/handlers'

const BASE = '/api/v1'

describe('fetchVocabulary', () => {
  it('returns vocabulary list', async () => {
    const data = await fetchVocabulary('a0')
    expect(data).toEqual(mockVocabList)
  })

  it('handles server error', async () => {
    server.use(
      http.get(`${BASE}/vocabulary/`, () => HttpResponse.json({ detail: 'error' }, { status: 500 }))
    )
    await expect(fetchVocabulary()).rejects.toThrow()
  })
})

describe('fetchVocabularyItem', () => {
  it('returns a single item', async () => {
    const data = await fetchVocabularyItem(1)
    expect(data).toEqual(mockVocabItem)
  })
})

describe('fetchUserProgress', () => {
  it('returns user progress', async () => {
    const data = await fetchUserProgress()
    expect(data.xp_total).toBe(120)
    expect(data.username).toBe('learner')
  })
})

describe('fetchDueCards', () => {
  it('returns due cards list', async () => {
    const data = await fetchDueCards(5)
    expect(Array.isArray(data)).toBe(true)
    expect(data[0].vocab_item.dutch_word).toBe('hond')
  })
})

describe('submitReview', () => {
  it('returns review response', async () => {
    const data = await submitReview(1, 3)
    expect(data.card_id).toBe(1)
    expect(data.xp_earned).toBe(10)
  })
})

describe('enrollCard', () => {
  it('returns enrollment data', async () => {
    const data = await enrollCard(1)
    expect(data.vocab_item_id).toBe(1)
  })
})

describe('fetchGrammar', () => {
  it('returns grammar topics', async () => {
    const data = await fetchGrammar('a0')
    expect(data[0].slug).toBe('de-het')
  })
})

describe('fetchStories', () => {
  it('returns stories list', async () => {
    const data = await fetchStories('a0')
    expect(data[0].slug).toBe('het-huis')
  })
})

describe('fetchStory', () => {
  it('returns a single story', async () => {
    const data = await fetchStory('het-huis')
    expect(data.title_nl).toBe('Het huis')
  })
})

describe('explainWord', () => {
  it('returns explanation', async () => {
    const data = await explainWord('hond')
    expect(data.explanation).toContain('perro')
  })
})

describe('getFeedback', () => {
  it('returns feedback text', async () => {
    const data = await getFeedback('¿Cómo se dice perro?', 'hond', 'kat')
    expect(data.feedback).toBeTruthy()
  })
})

describe('sendChat', () => {
  it('returns reply', async () => {
    const data = await sendChat([{ role: 'user', content: 'Hallo' }])
    expect(data.reply).toBeTruthy()
  })
})

describe('fetchFillBlank', () => {
  it('returns fill-blank exercise', async () => {
    const data = await fetchFillBlank('a0')
    expect(data.sentence_with_blank).toContain('___')
    expect(data.options.length).toBeGreaterThan(0)
  })
})

describe('fetchUnscramble', () => {
  it('returns unscramble exercise', async () => {
    const data = await fetchUnscramble('a0')
    expect(Array.isArray(data.shuffled_words)).toBe(true)
    expect(data.correct_sentence).toBeTruthy()
  })
})

describe('fetchListenChoose', () => {
  it('returns listen-choose exercise', async () => {
    const data = await fetchListenChoose('a0')
    expect(data.correct_id).toBe(1)
    expect(data.options.length).toBe(4)
  })
})

describe('fetchWordMatch', () => {
  it('returns word-match pairs', async () => {
    const data = await fetchWordMatch('a0')
    expect(data.pairs.length).toBeGreaterThan(0)
  })
})
