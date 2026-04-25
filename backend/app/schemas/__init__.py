"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Vocabulary ──────────────────────────────────────────────────────────────

class VocabularyItemBase(BaseModel):
    dutch_word: str
    spanish: str
    article: str | None = None
    plural: str | None = None
    word_type: str | None = None
    level: str
    theme: str
    image_url: str | None = None
    notes: str | None = None
    example_nl: str | None = None
    example_es: str | None = None


class VocabularyItemOut(VocabularyItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── Grammar ──────────────────────────────────────────────────────────────────

class GrammarTopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name_nl: str
    name_es: str
    level: str
    description_es: str | None = None
    examples_json: Any | None = None


# ── Stories ──────────────────────────────────────────────────────────────────

class StoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title_nl: str
    title_es: str
    level: str
    content_nl: str | None = None
    content_es: str | None = None
    audio_path: str | None = None
    questions_json: Any | None = None
    theme: str | None = None


# ── Progress / FSRS ──────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    card_id: int
    rating: int = Field(..., ge=1, le=4, description="1=Again, 2=Hard, 3=Good, 4=Easy")


class ReviewResponse(BaseModel):
    card_id: int
    next_due: datetime
    stability: float
    state: int
    xp_earned: int
    new_achievements: list[str] = []


class DueCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vocab_item: VocabularyItemOut
    state: int
    reps: int
    lapses: int


# ── User ─────────────────────────────────────────────────────────────────────

class UserProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    xp_total: int
    streak_days: int
    last_activity_date: str | None = None


# ── LLM ──────────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    word_or_phrase: str = Field(..., max_length=200)
    context_sentence: str | None = Field(None, max_length=500)


class FeedbackRequest(BaseModel):
    question: str = Field(..., max_length=500)
    correct_answer: str = Field(..., max_length=200)
    user_answer: str = Field(..., max_length=200)
    vocab_item_id: int | None = None


class GenerateExerciseRequest(BaseModel):
    theme: str = Field(..., max_length=100)
    level: str = Field(..., max_length=10)
    exercise_type: str = Field(..., max_length=50)  # fill_blank, multiple_choice, unscramble
    word: str | None = Field(None, max_length=200)


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., max_length=50)
    provider: str | None = Field(None, pattern=r"^(ollama|gemini)$")
