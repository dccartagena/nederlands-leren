"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


# ── Vocabulary ──────────────────────────────────────────────────────────────

class VocabularyItemBase(BaseModel):
    dutch_word: str
    spanish: str
    article: Optional[str] = None
    plural: Optional[str] = None
    word_type: Optional[str] = None
    level: str
    theme: str
    image_url: Optional[str] = None
    notes: Optional[str] = None
    example_nl: Optional[str] = None
    example_es: Optional[str] = None


class VocabularyItemOut(VocabularyItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    audio_files: List["AudioFileOut"] = []


# ── Audio ────────────────────────────────────────────────────────────────────

class AudioFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_path: str
    source: Optional[str] = None
    license: Optional[str] = None
    sentence_text_nl: Optional[str] = None


# ── Grammar ──────────────────────────────────────────────────────────────────

class GrammarTopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name_nl: str
    name_es: str
    level: str
    description_es: Optional[str] = None
    examples_json: Optional[Any] = None


# ── Stories ──────────────────────────────────────────────────────────────────

class StoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title_nl: str
    title_es: str
    level: str
    content_nl: Optional[str] = None
    content_es: Optional[str] = None
    audio_path: Optional[str] = None
    questions_json: Optional[Any] = None
    theme: Optional[str] = None


# ── Progress / FSRS ──────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    card_id: int
    rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy


class ReviewResponse(BaseModel):
    card_id: int
    next_due: datetime
    stability: float
    state: int
    xp_earned: int


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
    last_activity_date: Optional[str] = None


# ── LLM ──────────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    word_or_phrase: str
    context_sentence: Optional[str] = None


class FeedbackRequest(BaseModel):
    question: str
    correct_answer: str
    user_answer: str
    vocab_item_id: Optional[int] = None


class GenerateExerciseRequest(BaseModel):
    theme: str
    level: str
    exercise_type: str  # fill_blank, multiple_choice, unscramble
    word: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
