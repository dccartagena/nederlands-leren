"""
Content generation & scraping API endpoints.

POST /content/generate/vocabulary  — LLM-generated vocabulary items
POST /content/generate/grammar     — LLM-generated grammar topic
POST /content/generate/story       — LLM-generated reading story
POST /content/generate/lesson      — Complete lesson (vocab + grammar tip + story)
POST /content/generate/exercise    — LLM-generated game exercise

GET  /content/scrape/tatoeba/{word}  — Tatoeba sentences (CC BY 2.0)
POST /content/scrape/tatoeba         — Bulk Tatoeba enrichment for a word list
GET  /content/scrape/wiktionary/{word} — Wiktionary entry (CC BY-SA 3.0)
GET  /content/scrape/word/{word}     — Combined Wiktionary + Tatoeba for one word

GET  /content/levels                — Available CEFR levels with descriptions
GET  /content/themes/{level}        — Suggested themes for a level
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import content_generator, content_scraper

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class GenerateVocabularyRequest(BaseModel):
    level: str = Field(..., description="CEFR level: a0, a1, a2, b1, b2, c1")
    theme: str = Field(..., description="Thematic category, e.g. 'animales', 'ciudad'")
    count: int = Field(10, ge=1, le=30, description="Number of words to generate")


class GenerateGrammarRequest(BaseModel):
    level: str
    topic_name_es: str = Field(..., description="Grammar topic name in Spanish")
    topic_name_nl: str = Field(..., description="Grammar topic name in Dutch")
    slug: str = Field(..., description="URL-friendly identifier, e.g. 'comparativos'")


class GenerateStoryRequest(BaseModel):
    level: str
    theme: str
    title_nl: Optional[str] = None
    title_es: Optional[str] = None
    slug: Optional[str] = None


class GenerateLessonRequest(BaseModel):
    level: str
    theme: str
    vocab_count: int = Field(5, ge=1, le=20)


class GenerateExerciseRequest(BaseModel):
    level: str
    theme: str
    game_type: str = Field(
        ...,
        description="Exercise type: fill_blank | multiple_choice | unscramble | word_match",
    )
    vocabulary: Optional[List[str]] = Field(
        None, description="Optional Dutch words to use as hints"
    )


class ScrapeTatoebaRequest(BaseModel):
    words: List[str] = Field(..., description="Dutch words to look up")
    level: str
    theme: str


# ---------------------------------------------------------------------------
# Generate endpoints
# ---------------------------------------------------------------------------


@router.post("/generate/vocabulary", summary="Generate vocabulary with LLM")
async def generate_vocabulary(req: GenerateVocabularyRequest) -> Dict[str, Any]:
    """Use the configured LLM to generate *count* vocabulary items for the
    given CEFR level and thematic category.

    Returned items are compatible with the VocabularyItem DB model and can be
    persisted via the seed script.
    """
    try:
        items = await content_generator.generate_vocabulary(req.level, req.theme, req.count)
        return {"items": items, "count": len(items)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/generate/grammar", summary="Generate grammar topic with LLM")
async def generate_grammar(req: GenerateGrammarRequest) -> Dict[str, Any]:
    """Generate a GrammarTopic — including description and worked examples —
    using the configured LLM.
    """
    try:
        topic = await content_generator.generate_grammar_topic(
            req.level, req.topic_name_es, req.topic_name_nl, req.slug
        )
        if not topic:
            raise HTTPException(status_code=502, detail="LLM returned empty response")
        return topic
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/generate/story", summary="Generate reading story with LLM")
async def generate_story(req: GenerateStoryRequest) -> Dict[str, Any]:
    """Generate a Story — Dutch text, Spanish translation, and comprehension
    questions — using the configured LLM.
    """
    try:
        story = await content_generator.generate_story(
            req.level, req.theme, req.title_nl, req.title_es, req.slug
        )
        if not story:
            raise HTTPException(status_code=502, detail="LLM returned empty response")
        return story
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/generate/lesson", summary="Generate complete lesson with LLM")
async def generate_lesson(req: GenerateLessonRequest) -> Dict[str, Any]:
    """Generate a full lesson bundle: vocabulary list, a grammar tip, and a
    short story — all tailored to the requested CEFR level and theme.
    """
    try:
        lesson = await content_generator.generate_lesson(
            req.level, req.theme, req.vocab_count
        )
        return lesson
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/generate/exercise", summary="Generate game exercise with LLM")
async def generate_exercise(req: GenerateExerciseRequest) -> Dict[str, Any]:
    """Generate a single game exercise (fill_blank, multiple_choice, unscramble,
    or word_match) using the configured LLM.
    """
    try:
        exercise = await content_generator.generate_game_exercise(
            req.level, req.theme, req.game_type, req.vocabulary
        )
        if not exercise:
            raise HTTPException(status_code=502, detail="LLM returned empty response")
        return exercise
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ---------------------------------------------------------------------------
# Scrape endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/scrape/tatoeba/{word}",
    summary="Fetch Tatoeba sentences for a Dutch word (CC BY 2.0)",
)
async def scrape_tatoeba_word(
    word: str,
    limit: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    """Return up to *limit* Dutch example sentences from Tatoeba.org that
    contain the given word, together with their Spanish translations.

    Licence: CC BY 2.0 — attribution to Tatoeba.org contributors required.
    """
    try:
        sentences = await content_scraper.fetch_tatoeba_sentences(word, limit=limit)
        return {"word": word, "sentences": sentences, "count": len(sentences)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post(
    "/scrape/tatoeba",
    summary="Bulk-enrich a word list with Tatoeba examples (CC BY 2.0)",
)
async def scrape_tatoeba_bulk(req: ScrapeTatoebaRequest) -> Dict[str, Any]:
    """For each word in *words*, fetch example sentences from Tatoeba and
    return partial VocabularyItem dicts enriched with the first matching sentence.
    """
    try:
        items = await content_scraper.scrape_vocabulary_from_tatoeba(
            req.words, req.level, req.theme
        )
        return {"items": items, "count": len(items)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/scrape/wiktionary/{word}",
    summary="Fetch Dutch Wiktionary entry (CC BY-SA 3.0)",
)
async def scrape_wiktionary(word: str) -> Dict[str, Any]:
    """Fetch article, plural form, word type, and an example sentence for a
    Dutch word from the Dutch Wiktionary.

    Licence: CC BY-SA 3.0 — attribution to Wiktionary contributors required.
    """
    try:
        entry = await content_scraper.fetch_wiktionary_entry(word)
        if not entry:
            raise HTTPException(status_code=404, detail=f"'{word}' not found in Wiktionary")
        return entry
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get(
    "/scrape/word/{word}",
    summary="Combined Wiktionary + Tatoeba lookup for a single Dutch word",
)
async def scrape_word(
    word: str,
    level: str = Query("a1"),
    theme: str = Query("general"),
    sentence_limit: int = Query(3, ge=1, le=10),
) -> Dict[str, Any]:
    """Return all available open-source data for a Dutch word: Wiktionary
    metadata (article, plural, word_type) merged with Tatoeba example sentences.

    The result is a partial VocabularyItem that can be merged with
    LLM-generated translations before seeding the database.
    """
    try:
        data = await content_scraper.scrape_word(word, level, theme, sentence_limit)
        return data
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ---------------------------------------------------------------------------
# Metadata endpoints
# ---------------------------------------------------------------------------


@router.get("/levels", summary="List available CEFR levels")
def get_levels() -> Dict[str, Any]:
    """Return the supported CEFR levels together with human-readable descriptions."""
    return {
        "levels": [
            {"code": code, "description": desc}
            for code, desc in content_generator.LEVEL_DESCRIPTIONS.items()
        ]
    }


@router.get("/themes/{level}", summary="Get suggested themes for a CEFR level")
def get_themes_for_level(level: str) -> Dict[str, Any]:
    """Return a list of suggested thematic categories for the given CEFR level."""
    themes = content_generator.THEMES_BY_LEVEL.get(level.lower(), [])
    return {"level": level.lower(), "themes": themes}
