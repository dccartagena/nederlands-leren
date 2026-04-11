# Nederlands Leren 🇳🇱

A web-based Dutch ↔ Spanish language learning app targeting CEFR levels A0 and A1.  
The interface and all explanations are in **Spanish** — aimed at Spanish speakers learning Dutch.

---

## Features

- **7 game types**: Flashcards (FSRS spaced repetition), Listen & Choose, Word Match, Multiple Choice, Fill in Blank, Sentence Unscramble, Story Mode
- **Spaced repetition** with the [FSRS algorithm](https://github.com/open-spaced-repetition/fsrs4anki) — cards schedule themselves
- **LLM integration**: grammar explanations, real-time wrong-answer feedback (Multiple Choice), dynamic exercise generation, and Dutch conversation chat
- **Multi-provider AI**: Ollama (local, primary), OpenAI, Anthropic, Mistral, and Gemini — switchable per chat session; app falls back gracefully when no LLM is available
- **Audio**: gTTS synthesis fallback; Tatoeba / Common Voice downloads for native speech; **Gemini 2.5 Flash TTS** for high-quality Dutch audio with a Northern Dutch regional accent
- **Dark mode** support throughout the UI
- **Rate limiting** on all LLM and content-generation endpoints (slowapi)
- Single-user — no authentication needed; progress persists in SQLite (dev) or PostgreSQL (prod)

---

## Repository Layout

```
nederlands-leren/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml     # Python 3.12 — ruff, mypy, bandit, pytest (runs on main / PRs)
│       └── frontend-ci.yml    # Node LTS — ESLint, tsc, vitest (runs on main / PRs)
│
├── backend/                   # FastAPI Python backend
│   ├── app/
│   │   ├── api/v1/            # Route handlers (vocabulary, grammar, stories, progress, exercises, llm, content)
│   │   ├── core/config.py     # Pydantic settings — all env vars documented here
│   │   ├── db/
│   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   └── session.py     # Engine + get_db dependency
│   │   ├── schemas/           # Pydantic request/response schemas (with Field validation)
│   │   ├── services/
│   │   │   ├── spaced_repetition.py   # FSRS Scheduler wrapper
│   │   │   ├── llm_service.py         # Ollama + LiteLLM abstraction
│   │   │   ├── audio_service.py       # gTTS synthesis + path helpers
│   │   │   ├── content_generator.py   # LLM-powered vocab / story / grammar generation
│   │   │   └── content_scraper.py     # Tatoeba (CC BY 2.0) + Wiktionary (CC BY-SA 3.0)
│   │   └── main.py            # FastAPI application factory + rate limiter setup
│   ├── tests/
│   │   ├── conftest.py        # In-memory SQLite fixtures, TestClient, rollback-per-test
│   │   ├── unit/              # spaced_repetition, content_generator, llm_service, audio_service
│   │   └── integration/       # exercises, progress, content, llm endpoints
│   ├── alembic/               # Database migrations
│   ├── scripts/
│   │   ├── seed_content.py        # Populate DB from data/ JSON files
│   │   ├── download_audio.py      # Generate gTTS audio for all vocab
│   │   ├── gemini_tts.py          # Generate high-quality audio via Gemini 2.5 Flash TTS
│   │   ├── populate_content.py    # LLM batch content generation (vocab + stories + grammar)
│   │   ├── populate_config.json   # Themes / counts / levels config for populate_content.py
│   │   └── populate_images.py     # Fetch CC0 images from Pixabay → image_url
│   ├── pyproject.toml         # ruff, mypy, bandit, pytest, coverage config
│   ├── requirements.txt
│   ├── requirements-dev.txt   # Dev/test tools (ruff, mypy, bandit, pytest, respx …)
│   ├── Dockerfile             # Production image
│   └── Dockerfile.dev         # Dev image (hot-reload)
│
├── frontend/                  # React + Vite + TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── games/         # FlashcardGame, ListenChooseGame, WordMatchGame, MultipleChoiceGame, FillBlankGame, UnscrambleGame, StoryModeGame …
│   │   │   └── layout/        # Layout (top nav + mobile bottom nav)
│   │   ├── pages/             # Dashboard, Lesson, Practice, Progress, Chat
│   │   ├── stores/appStore.ts # Zustand global state (level, theme, audio toggle)
│   │   ├── lib/api.ts         # Axios client + all API call functions + TypeScript types
│   │   ├── test/
│   │   │   ├── mocks/         # MSW handlers + fixtures for all API endpoints
│   │   │   ├── setup.ts       # jest-dom + MSW server lifecycle
│   │   │   └── utils.tsx      # renderWithProviders (QueryClient + MemoryRouter)
│   │   └── main.tsx           # App entry point
│   ├── eslint.config.js       # ESLint 9 flat config with strict TypeScript rules
│   ├── vitest.config.ts       # jsdom, v8 coverage, path aliases
│   ├── .prettierrc            # Prettier config with prettier-plugin-tailwindcss
│   ├── Dockerfile             # Multi-stage build → nginx
│   ├── nginx.conf             # Proxies /api and /audio to the backend
│   ├── tailwind.config.js
│   └── vite.config.ts         # Dev proxy: /api → localhost:8000
│
├── data/                      # Content — tracked in git, shared by backend
│   ├── vocabulary/
│   │   ├── a0_words.json      # A0 Dutch↔Spanish words with examples
│   │   └── a1_words.json      # A1 words (modals, city, travel, health …)
│   ├── grammar/
│   │   ├── a0_grammar.json    # Present tense, articles, pronouns, negation …
│   │   └── a1_grammar.json    # A1 grammar topics
│   ├── stories/
│   │   ├── a0_stories.json    # A0 graded stories with comprehension questions
│   │   ├── a1_stories.json    # A1 graded stories
│   │   └── a2_stories.json    # A2 graded stories
│   ├── grammar_topics.json    # Grammar topic list used by populate_content.py
│   ├── story_titles.json      # Suggested story titles per level/theme
│   └── audio/                 # Generated / downloaded audio files (gitignored)
│
├── .pre-commit-config.yaml    # ruff, mypy, bandit, trailing-whitespace hooks
├── docker-compose.yml         # Production: api + frontend/nginx + PostgreSQL + Ollama (GPU)
├── docker-compose.dev.yml     # Dev: hot-reload api + Vite dev server + Ollama
├── .env.example               # All supported environment variables
└── .gitignore
```

---

## Quick Start — Local Dev (no Docker)

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node 20+ (install via [nvm](https://github.com/nvm-sh/nvm): `nvm install 20`)
- Ollama running locally with a model pulled (optional — app falls back gracefully)

### Backend

```bash
cd backend

# Create and activate virtual environment
uv venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Seed the database (first run)
python scripts/seed_content.py

# Generate gTTS audio files (fallback, no API key required)
python scripts/download_audio.py

# Generate high-quality audio via Gemini TTS (Northern Dutch accent)
# Requires GEMINI_API_KEY and GEMINI_TTS_MODEL in .env — see Configuration
# Skips items already generated; resume-safe across runs
python scripts/gemini_tts.py --type vocabulary
python scripts/gemini_tts.py --type stories
# Filter by level or smoke-test with --max-items
python scripts/gemini_tts.py --type vocabulary --level a0 --max-items 5

# Populate vocabulary images via Pixabay (requires free API key)
# Set PIXABAY_API_KEY in backend/.env first — see .env.example
python scripts/populate_images.py --level a0
python scripts/populate_images.py --level a1

# Generate LLM content (vocab + stories) via the Gemini Batch API
# Requires GEMINI_API_KEY and GEMINI_MODEL in .env
# Reads themes/counts from scripts/populate_config.json; resume-safe

# Dry-run — preview without writing files or touching the DB
python scripts/populate_content.py --levels a0 --types vocab --dry-run

# Generate A0 vocabulary (20 words per theme)
python scripts/populate_content.py --levels a0 --types vocab --vocab-count 20

# Generate A0 + A1 stories
python scripts/populate_content.py --levels a0 a1 --types stories

# Use Gemini Batch API (cheaper, async) instead of the default live API
python scripts/populate_content.py --levels a0 a1 --types vocab stories --batch

# Start the API
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

The Vite dev server proxies `/api` and `/audio` to `localhost:8000` automatically.

---

## Gemini TTS Audio Generation

`backend/scripts/gemini_tts.py` generates Dutch audio using `gemini-2.5-flash-preview-tts` with a **Northern Dutch regional accent**, replacing the gTTS fallback entries in the database.

### Prerequisites

- `GEMINI_API_KEY` set in `backend/.env`
- `GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts` set in `backend/.env` (default)
- `google-genai>=1.10.0` — already in `requirements.txt`

### Usage

```bash
# Dry-run — preview what would be generated without writing files or touching the DB
python scripts/gemini_tts.py --type vocabulary --dry-run

# Generate vocabulary audio for all levels
python scripts/gemini_tts.py --type vocabulary

# Generate story audio for A0 only
python scripts/gemini_tts.py --type stories --level a0

# Limit to 5 items (useful for smoke-testing)
python scripts/gemini_tts.py --type vocabulary --level a0 --max-items 5

# Re-generate even if audio already exists (overwrite)
python scripts/gemini_tts.py --type vocabulary --force

# Write files but do not update the database
python scripts/gemini_tts.py --type stories --no-db
```

### Voices & Prompts

| Content type | Voice | Style |
|---|---|---|
| Vocabulary | `Charon` | Clear, steady; 0.85× speed; 1.5 s pause between entries; Northern Dutch G/ch articulation |
| Stories | `Aoede` | Expressive; variable pacing; natural pauses after commas (0.5 s) and paragraphs (1.2 s) |

Output files are saved as WAV (`gemini_<word>_<level>.wav` / `gemini_<slug>.wav`) in `AUDIO_DIR` and the database is updated to point to the new files.

---

## Quick Start — Docker Compose (dev)

```bash
# Starts: api (hot-reload) + Vite dev server + Ollama (GPU if available)
docker compose -f docker-compose.dev.yml up
```

| Service  | URL                        |
|----------|---------------------------|
| Frontend | http://localhost:5173      |
| API      | http://localhost:8000      |
| API docs | http://localhost:8000/docs |
| Ollama   | http://localhost:11434     |

## Quick Start — Docker Compose (production)

```bash
cp .env.example .env
# Edit .env — SECRET_KEY must be changed from the default or the app will refuse to start

docker compose up --build
```

| Service  | URL                   |
|----------|-----------------------|
| App      | http://localhost:80   |
| API      | http://localhost:8000 |

---

## Configuration

All settings are in `backend/app/core/config.py` and read from environment variables (or a `.env` file at the repo root).

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | _(required)_ | **Must be set** — app refuses to start with the default value |
| `DATABASE_URL` | `sqlite:///…/data/app.db` | SQLAlchemy connection string |
| `LLM_PROVIDER` | `ollama` | `ollama` \| `openai` \| `anthropic` \| `mistral` \| `gemini` |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `mistral:7b-instruct-q4_K_M` | Model to use with Ollama |
| `OPENAI_API_KEY` | _(empty)_ | Used when provider is `openai` |
| `ANTHROPIC_API_KEY` | _(empty)_ | Used when provider is `anthropic` |
| `MISTRAL_API_KEY` | _(empty)_ | Used when provider is `mistral` |
| `GEMINI_API_KEY` | _(empty)_ | Used when LLM provider is `gemini`; also authenticates `gemini_tts.py` |
| `GEMINI_TTS_MODEL` | `gemini-2.5-flash-preview-tts` | TTS model used by `gemini_tts.py` |
| `REMOTE_MODEL` | `gpt-4o-mini` | Model name for remote providers |
| `GEMINI_MODEL` | `gemini/gemini-2.0-flash` | Model name used when provider is `gemini` |
| `PIXABAY_API_KEY` | _(empty)_ | Free key from [pixabay.com/api/docs](https://pixabay.com/api/docs/) — used by `populate_images.py` |
| `AUDIO_DIR` | `…/data/audio` | Where audio files are stored/served |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/vocabulary/` | List vocabulary (`?level=a0&theme=animales`) |
| GET | `/api/v1/vocabulary/{id}` | Single item |
| GET | `/api/v1/grammar/` | Grammar topics (`?level=a0`) |
| GET | `/api/v1/grammar/{slug}` | Single topic |
| GET | `/api/v1/stories/` | Story list (`?level=a0`) |
| GET | `/api/v1/stories/{slug}` | Story detail |
| GET | `/api/v1/progress/user` | User stats (XP, streak) |
| GET | `/api/v1/progress/due` | Due FSRS cards (`?limit`, default 20, max 50) |
| POST | `/api/v1/progress/review` | Submit review rating (1–4) |
| POST | `/api/v1/progress/enroll/{id}` | Add vocab item to SR deck |
| GET | `/api/v1/exercises/listen-choose` | Listen & choose exercise |
| GET | `/api/v1/exercises/word-match` | Word match pairs (`?count`, default 6, max 10) |
| GET | `/api/v1/exercises/fill-blank` | Fill-in-blank exercise |
| GET | `/api/v1/exercises/unscramble` | Sentence unscramble exercise |
| POST | `/api/v1/llm/explain` | Explain a Dutch word/phrase (30 req/min) |
| POST | `/api/v1/llm/feedback` | Wrong-answer feedback (30 req/min) |
| POST | `/api/v1/llm/generate-exercise` | Dynamic exercise generation (20 req/min) |
| POST | `/api/v1/llm/chat` | Dutch conversation chat — optional `provider` override (20 req/min) |
| GET | `/api/v1/content/levels` | Available CEFR levels with descriptions |
| GET | `/api/v1/content/themes/{level}` | Suggested themes for a CEFR level |
| POST | `/api/v1/content/generate/vocabulary` | LLM-generate vocabulary items |
| POST | `/api/v1/content/generate/grammar` | LLM-generate one grammar topic |
| POST | `/api/v1/content/generate/story` | LLM-generate one reading story |
| POST | `/api/v1/content/generate/lesson` | LLM-generate a full lesson bundle |
| POST | `/api/v1/content/generate/exercise` | LLM-generate one game exercise |
| GET | `/api/v1/content/scrape/tatoeba/{word}` | Tatoeba examples for one Dutch word |
| POST | `/api/v1/content/scrape/tatoeba` | Bulk Tatoeba enrichment for a word list |
| GET | `/api/v1/content/scrape/wiktionary/{word}` | Wiktionary lexical info for one word |
| GET | `/api/v1/content/scrape/word/{word}` | Combined Wiktionary + Tatoeba result |

Full interactive docs at `http://localhost:8000/docs` when the API is running.

---

## Development

### Running tests

**Backend** (pytest + coverage):

```bash
cd backend
source .venv/bin/activate
uv pip install -r requirements-dev.txt

SECRET_KEY=any-non-default-value pytest --cov=app --cov-report=term-missing
```

**Frontend** (Vitest + React Testing Library):

```bash
cd frontend
npm install
npm run test           # run once
npm run test:watch     # watch mode
npm run test:coverage  # with v8 coverage report
```

### Linting & formatting

**Backend:**

```bash
cd backend && source .venv/bin/activate
ruff check app/        # lint
ruff check app/ --fix  # lint + auto-fix
mypy app/              # type checking
bandit -r app/ -c pyproject.toml  # security scan
```

**Frontend:**

```bash
cd frontend
npm run lint           # ESLint (strict TypeScript rules, 0 warnings allowed)
npm run type-check     # tsc --noEmit
npm run format         # Prettier
```

### Pre-commit hooks

```bash
uv pip install pre-commit
pre-commit install
```

Runs on every commit: ruff (with auto-fix), mypy, bandit, trailing-whitespace, YAML validation.  
Frontend staged files also run ESLint + Prettier via husky/lint-staged.

### CI

GitHub Actions runs on every push/PR to `main`:

| Workflow | Triggers when | Steps |
|---|---|---|
| `backend-ci.yml` | `backend/**` changes | ruff → mypy → bandit → pytest (coverage ≥ 70%) |
| `frontend-ci.yml` | `frontend/**` changes | ESLint → tsc → vitest (coverage enforced) |

---

## Adding Content

All content is plain JSON in `data/` — no code changes needed.

**Add vocabulary** — append objects to `data/vocabulary/a0_words.json` (or `a1_words.json`):

```json
{
  "dutch_word": "bibliotheek",
  "english": "library",
  "spanish": "biblioteca",
  "article": "de",
  "plural": "bibliotheken",
  "word_type": "noun",
  "level": "a1",
  "theme": "educacion",
  "example_nl": "Ik lees in de bibliotheek.",
  "example_es": "Leo en la biblioteca."
}
```

**Add grammar topics** — append to `data/grammar/a0_grammar.json`:

```json
{
  "slug": "present-tense",
  "name_nl": "Tegenwoordige tijd",
  "name_es": "Presente de indicativo",
  "level": "a0",
  "description_es": "El presente se forma con la raíz del verbo + terminaciones.",
  "examples_json": [
    { "nl": "Ik werk.", "es": "Yo trabajo.", "notes": "raíz: werk" }
  ]
}
```

**Re-seed** after adding content:

```bash
cd backend && python scripts/seed_content.py
```

---

## TODO

### Games
- [ ] Story Mode advanced UX pass (progressive reveal, checkpoints, scoring polish)

### Content
- [ ] Populate vocabulary images: `cd backend && python scripts/populate_images.py` (requires `PIXABAY_API_KEY` in `.env`)
- [ ] Expand B-level vocabulary/story coverage

### Frontend
- [ ] User progress dashboard charts
- [ ] Achievement badges (first 10 words, 7-day streak, …)
- [ ] Settings page (audio on/off; LLM provider default)
- [ ] Enroll-all button in Lesson page (add all vocab to SR deck at once)
- [ ] Mobile responsive polish pass

### Infrastructure
- [ ] PostgreSQL migration for production
- [ ] Coverage badges in README
