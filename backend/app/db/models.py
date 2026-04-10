from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"

    id = Column(Integer, primary_key=True, index=True)
    dutch_word = Column(String(100), nullable=False, index=True)
    english = Column(String(200))
    spanish = Column(String(200), nullable=False)
    article = Column(String(10))          # de / het / None (for verbs, etc.)
    plural = Column(String(100))
    word_type = Column(String(30))        # noun, verb, adjective, adverb, phrase
    level = Column(String(5), index=True) # a0, a1, a2 …
    theme = Column(String(50), index=True)
    image_url = Column(String(500))
    notes = Column(Text)
    example_nl = Column(Text)
    example_es = Column(Text)

    audio_files = relationship("AudioFile", back_populates="vocab_item")
    sr_cards = relationship("SRCard", back_populates="vocab_item")


class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    vocab_item_id = Column(Integer, ForeignKey("vocabulary_items.id"), nullable=True)
    sentence_text_nl = Column(Text)
    file_path = Column(String(500), nullable=False)
    source = Column(String(50))   # tatoeba, common_voice, gtts
    license = Column(String(50))
    speaker = Column(String(100))

    vocab_item = relationship("VocabularyItem", back_populates="audio_files")


class GrammarTopic(Base):
    __tablename__ = "grammar_topics"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True)
    name_nl = Column(String(200))
    name_es = Column(String(200))
    level = Column(String(5), index=True)
    description_es = Column(Text)
    examples_json = Column(JSON)   # list of {nl, es, notes}


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, index=True)
    title_nl = Column(String(200))
    title_es = Column(String(200))
    level = Column(String(5), index=True)
    content_nl = Column(Text)
    content_es = Column(Text)
    audio_path = Column(String(500))
    questions_json = Column(JSON)  # list of {question_es, options, answer_index, explanation_es}
    theme = Column(String(50))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), default="learner")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    settings_json = Column(JSON, default=dict)
    xp_total = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    last_activity_date = Column(String(10))  # ISO date string

    sr_cards = relationship("SRCard", back_populates="user")
    sessions = relationship("LearningSession", back_populates="user")


class SRCard(Base):
    """FSRS spaced-repetition card for a single vocabulary item."""
    __tablename__ = "sr_cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vocab_item_id = Column(Integer, ForeignKey("vocabulary_items.id"), nullable=False)
    # FSRS fields
    stability = Column(Float, default=0.0)
    difficulty = Column(Float, default=5.0)
    elapsed_days = Column(Integer, default=0)
    scheduled_days = Column(Integer, default=0)
    reps = Column(Integer, default=0)
    lapses = Column(Integer, default=0)
    state = Column(Integer, default=0)  # 0=New, 1=Learning, 2=Review, 3=Relearning
    due_date = Column(DateTime, default=lambda: datetime.now(UTC))
    last_review = Column(DateTime)

    user = relationship("User", back_populates="sr_cards")
    vocab_item = relationship("VocabularyItem", back_populates="sr_cards")


class LearningSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    ended_at = Column(DateTime)
    xp_earned = Column(Integer, default=0)
    exercises_completed = Column(Integer, default=0)
    game_type = Column(String(50))

    user = relationship("User", back_populates="sessions")
