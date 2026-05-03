"""
Content generation API endpoints (LLM-powered).

POST /content/generate/vocabulary  — Generate vocabulary items
POST /content/generate/grammar     — Generate a grammar topic
POST /content/generate/story       — Generate a reading story
POST /content/generate/exercise    — Generate a game exercise

GET  /content/levels               — Available CEFR levels
GET  /content/themes/{level}       — Suggested themes for a level
"""
import logging
from contextlib import contextmanager
from typing import Annotated, Any, Generator

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.core.limiter import limiter
from app.services import content_generator

logger = logging.getLogger(__name__)


@contextmanager
def _llm_error_handler() -> Generator[None, None, None]:
    try:
        yield
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("LLM call failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

router = APIRouter()

_ALL_THEMES: frozenset[str] = frozenset(
    theme for themes in content_generator.THEMES_BY_LEVEL.values() for theme in themes
)

_VALID_GAME_TYPES: frozenset[str] = frozenset(
    {"fill_blank", "multiple_choice", "unscramble", "word_match"}
)

_VALID_LEVELS: frozenset[str] = frozenset({"a0", "a1", "a2", "b1", "b2", "c1"})

_SlugStr = Annotated[str, Field(pattern=r"^[a-z0-9-]{1,100}$")]
_LevelStr = Annotated[str, Field(pattern=r"^(a0|a1|a2|b1|b2|c1)$")]
_ShortStr = Annotated[str, Field(max_length=200)]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class GenerateVocabularyRequest(BaseModel):
    level: _LevelStr = Field(..., description="CEFR level: a0, a1, a2, b1, b2, c1")
    theme: str = Field(..., description="Thematic category, e.g. 'animales', 'ciudad'", max_length=100)
    count: int = Field(10, ge=1, le=30)

    @field_validator("theme")
    @classmethod
    def theme_must_be_known(cls, v: str) -> str:
        if v not in _ALL_THEMES:
            raise ValueError(f"Unknown theme '{v}'. Valid themes: {sorted(_ALL_THEMES)}")
        return v


class GenerateGrammarRequest(BaseModel):
    level: _LevelStr
    topic_name_es: _ShortStr
    topic_name_nl: _ShortStr
    slug: _SlugStr

    @field_validator("level")
    @classmethod
    def level_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_LEVELS:
            raise ValueError(f"Invalid level '{v}'")
        return v


class GenerateStoryRequest(BaseModel):
    level: _LevelStr
    theme: str = Field(..., max_length=100)
    title_nl: _ShortStr | None = None
    title_es: _ShortStr | None = None
    slug: _SlugStr | None = None

    @field_validator("theme")
    @classmethod
    def theme_must_be_known(cls, v: str) -> str:
        if v not in _ALL_THEMES:
            raise ValueError(f"Unknown theme '{v}'. Valid themes: {sorted(_ALL_THEMES)}")
        return v


class GenerateExerciseRequest(BaseModel):
    level: _LevelStr
    theme: str = Field(..., max_length=100)
    game_type: str = Field(
        ...,
        description="fill_blank | multiple_choice | unscramble | word_match",
    )
    vocabulary: list[_ShortStr] | None = None

    @field_validator("theme")
    @classmethod
    def theme_must_be_known(cls, v: str) -> str:
        if v not in _ALL_THEMES:
            raise ValueError(f"Unknown theme '{v}'. Valid themes: {sorted(_ALL_THEMES)}")
        return v

    @field_validator("game_type")
    @classmethod
    def game_type_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_GAME_TYPES:
            raise ValueError(f"Invalid game_type '{v}'. Valid: {sorted(_VALID_GAME_TYPES)}")
        return v


# ---------------------------------------------------------------------------
# Generate endpoints
# ---------------------------------------------------------------------------


@router.post("/generate/vocabulary")
@limiter.limit("5/minute")
async def generate_vocabulary(request: Request, req: GenerateVocabularyRequest) -> dict[str, Any]:
    with _llm_error_handler():
        items = await content_generator.generate_vocabulary(req.level, req.theme, req.count)
        return {"items": items, "count": len(items)}


@router.post("/generate/grammar")
@limiter.limit("5/minute")
async def generate_grammar(request: Request, req: GenerateGrammarRequest) -> dict[str, Any]:
    with _llm_error_handler():
        topic = await content_generator.generate_grammar_topic(
            req.level, req.topic_name_es, req.topic_name_nl, req.slug
        )
        if not topic:
            raise HTTPException(status_code=502, detail="LLM returned empty response")
        return topic


@router.post("/generate/story")
@limiter.limit("5/minute")
async def generate_story(request: Request, req: GenerateStoryRequest) -> dict[str, Any]:
    with _llm_error_handler():
        story = await content_generator.generate_story(
            req.level, req.theme, req.title_nl, req.title_es, req.slug
        )
        if not story:
            raise HTTPException(status_code=502, detail="LLM returned empty response")
        return story


@router.post("/generate/exercise")
@limiter.limit("10/minute")
async def generate_exercise(request: Request, req: GenerateExerciseRequest) -> dict[str, Any]:
    with _llm_error_handler():
        exercise = await content_generator.generate_game_exercise(
            req.level, req.theme, req.game_type, req.vocabulary
        )
        if not exercise:
            raise HTTPException(status_code=502, detail="LLM returned empty response")
        return exercise


# ---------------------------------------------------------------------------
# Metadata endpoints
# ---------------------------------------------------------------------------


@router.get("/levels")
def get_levels() -> dict[str, Any]:
    return {
        "levels": [
            {"code": code, "description": desc}
            for code, desc in content_generator.LEVEL_DESCRIPTIONS.items()
        ]
    }


@router.get("/themes/{level}")
def get_themes_for_level(level: str) -> dict[str, Any]:
    themes = content_generator.THEMES_BY_LEVEL.get(level.lower(), [])
    return {"level": level.lower(), "themes": themes}
