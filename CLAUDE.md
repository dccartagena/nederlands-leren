# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Nederlands Leren** is a Dutch ↔ Spanish language learning web app for Spanish speakers targeting CEFR levels A0–A2. It combines spaced repetition (FSRS algorithm), LLM-powered content generation, and 7 interactive game types.

Stack: FastAPI backend + React/Vite frontend + SQLite (dev) / PostgreSQL (prod) + multi-provider LLM (Ollama/Gemini/OpenAI/Anthropic).

## Commands

### Frontend (run from `frontend/`)
```bash
npm run dev          # Vite dev server at localhost:5173 (proxies /api and /audio to :8000)
npm run build        # tsc + Vite production build
npm run lint         # ESLint (0 warnings allowed)
npm run type-check   # tsc --noEmit
npm run test         # Vitest single run
npm run test:watch   # Vitest watch mode
npm run test:coverage
npm run format       # Prettier
```

### Backend (run from `backend/`)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # Dev server
pytest                                                        # Run tests (≥70% coverage required)
ruff check app/          # Lint
ruff check app/ --fix    # Auto-fix lint
mypy app/                # Type check
bandit -r app/ -c pyproject.toml  # Security scan
```

### Content & Data Scripts (run from `backend/`)
```bash
python scripts/seed_content.py                                         # Seed JSON → DB (idempotent)
python scripts/populate_content.py --levels a0 a1 --types vocab stories --batch  # LLM batch generation
python scripts/gemini_tts.py --type vocabulary --level a0 --dry-run   # Generate audio (Gemini TTS)
python scripts/download_audio.py                                       # Generate audio (gTTS fallback)
python scripts/populate_images.py --level a0                          # Fetch Pixabay CC0 images
```

### Docker
```bash
docker compose -f docker-compose.dev.yml up   # Dev stack (hot-reload + Ollama)
docker compose up --build                      # Production stack
```

## Architecture

### Data Flow
1. JSON content files in `data/{vocabulary,grammar,stories}/` (per CEFR level)
2. `seed_content.py` loads JSON → SQLite/PostgreSQL via SQLAlchemy models
3. FastAPI backend (`backend/app/`) serves REST API at `/api/v1/`
4. React frontend (`frontend/src/`) fetches via Axios, caches with TanStack Query

### Backend (`backend/app/`)
- `main.py` — FastAPI app entry point; creates DB tables on startup, mounts `/audio` static files, applies CORS + rate limiting (slowapi)
- `core/config.py` — Pydantic Settings singleton (`settings`); reads all env vars from `.env`
- `db/models.py` — SQLAlchemy models: `VocabularyItem`, `GrammarTopic`, `Story`, `User`, `SRCard`, `LearningSession`, `AudioFile`
- `db/session.py` — `get_db()` dependency injection
- `api/v1/` — 8 routers: health, vocabulary, grammar, stories, progress, exercises, llm, content
- `services/llm_service.py` — Multi-provider LLM client with Ollama→Gemini fallback; `chat_completion()`, `explain()`, `feedback()`, `generate_exercise()`
- `services/content_generator.py` — Generates vocabulary/grammar/stories via LLM; returns JSON matching DB model schemas
- `services/spaced_repetition.py` — FSRS algorithm integration for `SRCard` scheduling

### Frontend (`frontend/src/`)
- `main.tsx` — React 18 entry; wraps app in `QueryClientProvider` + `MemoryRouter`
- `pages/` — Dashboard, Lesson, Practice, Progress, Chat
- `components/games/` — 7 game types: FlashcardGame, ListenChooseGame, WordMatchGame, MultipleChoiceGame, FillBlankGame, UnscrambleGame, StoryModeGame
- `stores/appStore.ts` — Zustand global state (selected level, theme, audio toggle, language preference)
- `lib/api.ts` — Axios client + typed helpers for all API endpoints
- `test/` — Vitest setup; `mocks/` contains MSW handlers; `utils.tsx` exports `renderWithProviders()`
- `public/icons/` — PWA app icons (icon.svg source, icon-192x192.png, icon-512x512.png, apple-touch-icon.png)

### PWA Configuration
`vite-plugin-pwa` is registered in `vite.config.ts` and generates a Workbox service worker on every production build:
- **Manifest**: name, icons, `display: standalone`, `theme_color: #2563eb`
- **Precache**: all JS/CSS/HTML/font/icon build assets
- **Runtime cache strategies**: vocabulary + grammar → stale-while-revalidate (24 h); exercises + progress → network-first (10 s timeout); audio → cache-first (30 days)

The service worker requires HTTPS in production. Use `tailscale serve` (see README) to get free HTTPS on your private Tailscale network.

### LLM Provider Configuration
Set `LLM_PROVIDER` in `.env` to: `ollama` (default), `gemini`, `openai`, `anthropic`, or `mistral`. The service automatically falls back to the other provider if the primary fails.

## Environment Setup

Copy `.env.example` to `.env`. Required for full functionality:
- `SECRET_KEY` — must be changed from default
- `GEMINI_API_KEY` — for Gemini LLM or high-quality TTS
- `PIXABAY_API_KEY` — for vocabulary images
- `CORS_ORIGINS` — comma-separated allowed frontend origins; add your Tailscale HTTPS URL for mobile PWA access (e.g. `http://localhost,https://mymachine.tail1234.ts.net`)

`DATABASE_URL` defaults to SQLite at `data/app.db`. Table creation is automatic on backend startup.

## Testing Patterns

**Backend:** Tests live in `backend/tests/` with `unit/` and `integration/` subdirectories. `conftest.py` provides an in-memory SQLite fixture with transactional rollback per test. Run a single test: `pytest tests/unit/test_foo.py::test_bar`.

**Frontend:** MSW intercepts API calls at the network layer. Use `renderWithProviders()` from `test/utils.tsx` for components that need QueryClient or Router context.

## Data Schemas

Vocabulary JSON fields: `dutch_word`, `english`, `spanish`, `article` (de/het/null), `plural`, `word_type`, `level`, `theme`, `example_nl`, `example_es`, `image_url`.

Story JSON fields: `slug`, `title_nl`, `title_es`, `level`, `theme`, `content_nl`, `content_es`, `audio_path`, `questions_json` (array of `{question_es, options, answer_index, explanation_es}`).
