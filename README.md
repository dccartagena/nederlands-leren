# Nederlands Leren 🇳🇱

A web-based Dutch ↔ Spanish language learning app targeting CEFR levels A0 and A1.  
The interface and all explanations are in **Spanish** — aimed at Spanish speakers learning Dutch.

---

## Features

- **7 game types**: Flashcards (FSRS spaced repetition), Listen & Choose, Word Match, Multiple Choice, Fill in Blank, Sentence Unscramble, Story Mode
- **Spaced repetition** with the [FSRS algorithm](https://github.com/open-spaced-repetition/fsrs4anki) — cards schedule themselves
- **LLM integration**: grammar explanations, wrong-answer feedback, dynamic exercise generation, and Dutch conversation chat
- **Local-first AI**: Ollama (Mistral 7B / Qwen 2.5 7B Q4) as the primary LLM; remote API key (OpenAI / Anthropic / Mistral) as optional fallback
- **Audio**: gTTS synthesis fallback; Tatoeba / Common Voice downloads for native speech
- Single-user — no authentication needed; progress persists in SQLite (dev) or PostgreSQL (prod)

---

## Repository Layout

```
nederlands-leren/
├── backend/                   # FastAPI Python backend
│   ├── app/
│   │   ├── api/v1/            # Route handlers (vocabulary, grammar, stories, progress, exercises, llm)
│   │   ├── core/config.py     # Pydantic settings — all env vars documented here
│   │   ├── db/
│   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   └── session.py     # Engine + get_db dependency
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── spaced_repetition.py   # FSRS Scheduler wrapper
│   │   │   ├── llm_service.py         # Ollama + LiteLLM abstraction
│   │   │   └── audio_service.py       # gTTS synthesis + path helpers
│   │   └── main.py            # FastAPI application factory
│   ├── alembic/               # Database migrations
│   ├── scripts/
│   │   ├── seed_content.py      # Populate DB from data/ JSON files
│   │   ├── download_audio.py    # Generate gTTS audio for all vocab
│   │   └── populate_images.py   # Fetch CC0 images from Pixabay → image_url
│   ├── Dockerfile             # Production image
│   ├── Dockerfile.dev         # Dev image (hot-reload)
│   └── requirements.txt
│
├── frontend/                  # React + Vite + TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── games/         # FlashcardGame, ListenChooseGame, WordMatchGame, MultipleChoiceGame …
│   │   │   └── layout/        # Layout (top nav + mobile bottom nav)
│   │   ├── pages/             # Dashboard, Lesson, Practice, Progress, Chat
│   │   ├── stores/appStore.ts # Zustand global state (level, theme, audio toggle)
│   │   ├── lib/api.ts         # Axios client + all API call functions + TypeScript types
│   │   └── main.tsx           # App entry point
│   ├── Dockerfile             # Multi-stage build → nginx
│   ├── nginx.conf             # Proxies /api and /audio to the backend
│   ├── tailwind.config.js
│   └── vite.config.ts         # Dev proxy: /api → localhost:8000
│
├── data/                      # Content — tracked in git, shared by backend
│   ├── vocabulary/
│   │   ├── a0_words.json      # ~100 A0 Dutch↔Spanish words with examples
│   │   └── a1_words.json      # ~70 A1 words (modals, city, travel, health …)
│   ├── grammar/
│   │   ├── a0_grammar.json    # Present tense, articles, pronouns, negation …
│   │   └── a1_grammar.json    # Past tense, separable verbs, modal verbs …
│   ├── stories/
│   │   └── a0_stories.json    # Short graded stories with comprehension questions
│   └── audio/                 # Generated / downloaded audio files (gitignored)
│
├── docker-compose.yml         # Production: api + frontend/nginx + PostgreSQL + Ollama (GPU)
├── docker-compose.dev.yml     # Dev: hot-reload api + Vite dev server + Ollama
├── .env.example               # All supported environment variables
└── .gitignore
```

---

## Quick Start — Local Dev (no Docker)

### Prerequisites

- Python 3.12+
- Node 20+ (install via [nvm](https://github.com/nvm-sh/nvm): `nvm install 20`)
- Ollama running locally with a model pulled (optional — app falls back gracefully)

### Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed the database (first run)
python scripts/seed_content.py

# (Optional) Generate gTTS audio files
python scripts/download_audio.py

# (Optional) Populate vocabulary images via Pixabay (requires free API key)
# Set PIXABAY_API_KEY in backend/.env first — see .env.example
python scripts/populate_images.py --level a0
python scripts/populate_images.py --level a1

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
# Edit .env as needed

docker compose up --build
```

| Service  | URL                   |
|----------|-----------------------|
| App      | http://localhost:80   |
| API      | http://localhost:8000 |

---

## Configuration

All settings are in `backend/app/core/config.py` and read from environment variables (or a `.env` file in `backend/`).

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///…/data/app.db` | SQLAlchemy connection string |
| `LLM_PROVIDER` | `ollama` | `ollama` \| `openai` \| `anthropic` \| `mistral` |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `mistral:7b-instruct-q4_K_M` | Model to use with Ollama |
| `OPENAI_API_KEY` | _(empty)_ | Used when provider is `openai` |
| `ANTHROPIC_API_KEY` | _(empty)_ | Used when provider is `anthropic` |
| `MISTRAL_API_KEY` | _(empty)_ | Used when provider is `mistral` |
| `REMOTE_MODEL` | `gpt-4o-mini` | Model name for remote providers |
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
| GET | `/api/v1/progress/due` | Due FSRS cards |
| POST | `/api/v1/progress/review` | Submit review rating (1–4) |
| POST | `/api/v1/progress/enroll/{id}` | Add vocab item to SR deck |
| GET | `/api/v1/exercises/listen-choose` | Listen & choose exercise |
| GET | `/api/v1/exercises/word-match` | Word match pairs |
| POST | `/api/v1/llm/explain` | Explain a Dutch word/phrase |
| POST | `/api/v1/llm/feedback` | Wrong-answer feedback |
| POST | `/api/v1/llm/generate-exercise` | Dynamic exercise generation |
| POST | `/api/v1/llm/chat` | Dutch conversation chat |

Full interactive docs at `/docs` when the API is running.

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
- [ ] Fill-in-Blank game component
- [ ] Sentence Unscramble game component
- [ ] Story Mode game component (text + audio + comprehension questions)

### Content
- [ ] Populate vocabulary images: `cd backend && python scripts/populate_images.py` (requires `PIXABAY_API_KEY` in `.env`)
- [ ] Tatoeba audio downloader (native Dutch speech, CC BY 2.0)
- [ ] A1 grammar JSON content

### Frontend
- [ ] User progress dashboard charts
- [ ] Achievement badges (first 10 words, 7-day streak, …)
- [ ] Settings page (LLM provider toggling, audio on/off, dark/light theme)
- [ ] Enroll-all button in Lesson page (add all vocab to SR deck at once)
- [ ] A1 stories JSON content
- [ ] Mobile responsive polish pass
- [ ] PostgreSQL migration for production
- [ ] CI/CD pipeline
