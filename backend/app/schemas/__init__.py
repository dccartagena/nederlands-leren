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
    # True when the in-session combo is active (≥5 consecutive correct answers);
    # the server applies a ×1.5 XP bonus so xp_total stays authoritative.
    combo: bool = False


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


class MasteryStatsOut(BaseModel):
    """Competence metrics anchored in real ability (not points)."""
    mastered_words: int      # cards with FSRS stability > 21 days
    enrolled_words: int      # total cards in the SRS deck
    review_words: int        # cards that reached the Review state
    stories_completed: int
    streak_freezes: int


class QuestOut(BaseModel):
    """One optional daily quest with server-computed progress."""
    id: str
    title_es: str
    target: int
    progress: int
    done: bool


# ── User ─────────────────────────────────────────────────────────────────────

class UserProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    xp_total: int
    streak_days: int
    last_activity_date: str | None = None
    settings_json: dict[str, Any] | None = None


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


class StoryCompleteRequest(BaseModel):
    story_slug: str = Field(..., max_length=100)
    correct_count: int = Field(..., ge=0)
    total_questions: int = Field(..., ge=0)


class StoryCompleteResponse(BaseModel):
    xp_earned: int
    new_achievements: list[str] = []
