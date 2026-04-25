"""
Content generation API endpoints (LLM-powered).

POST /content/generate/vocabulary  — Generate vocabulary items
POST /content/generate/grammar     — Generate a grammar topic
POST /content/generate/story       — Generate a reading story
POST /content/generate/exercise    — Generate a game exercise

GET  /content/levels               — Available CEFR levels
GET  /content/themes/{level}       — Suggested themes for a level
"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import content_generator

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class GenerateVocabularyRequest(BaseModel):
    level: str = Field(..., description="CEFR level: a0, a1, a2, b1, b2, c1")
    theme: str = Field(..., description="Thematic category, e.g. 'animales', 'ciudad'")
    count: int = Field(10, ge=1, le=30)


class GenerateGrammarRequest(BaseModel):
    level: str
    topic_name_es: str
    topic_name_nl: str
    slug: str


class GenerateStoryRequest(BaseModel):
    level: str
    theme: str
    title_nl: str | None = None
    title_es: str | None = None
    slug: str | None = None


class GenerateExerciseRequest(BaseModel):
    level: str
    theme: str
    game_type: str = Field(
        ...,
        description="fill_blank | multiple_choice | unscramble | word_match",
    )
    vocabulary: list[str] | None = None


# ---------------------------------------------------------------------------
# Generate endpoints
# ---------------------------------------------------------------------------


@router.post("/generate/vocabulary")
async def generate_vocabulary(req: GenerateVocabularyRequest) -> dict[str, Any]:
    try:
        items = await content_generator.generate_vocabulary(req.level, req.theme, req.count)
        return {"items": items, "count": len(items)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/generate/grammar")
async def generate_grammar(req: GenerateGrammarRequest) -> dict[str, Any]:
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


@router.post("/generate/story")
async def generate_story(req: GenerateStoryRequest) -> dict[str, Any]:
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


@router.post("/generate/exercise")
async def generate_exercise(req: GenerateExerciseRequest) -> dict[str, Any]:
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
