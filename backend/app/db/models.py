from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"
    __table_args__ = (UniqueConstraint("dutch_word", "level", name="uq_vocab_word_level"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dutch_word: Mapped[str] = mapped_column(String(100), index=True)
    english: Mapped[str | None] = mapped_column(String(200))
    spanish: Mapped[str] = mapped_column(String(200))
    article: Mapped[str | None] = mapped_column(String(10))     # de / het / None (verbs, etc.)
    plural: Mapped[str | None] = mapped_column(String(100))
    word_type: Mapped[str | None] = mapped_column(String(30))   # noun, verb, adjective, adverb, phrase
    level: Mapped[str | None] = mapped_column(String(5), index=True)  # a0, a1, a2 …
    theme: Mapped[str | None] = mapped_column(String(50), index=True)
    image_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    example_nl: Mapped[str | None] = mapped_column(Text)
    example_es: Mapped[str | None] = mapped_column(Text)
    # Curate-first pipeline fields (handoff Part A/C): authoritative facts come
    # from open data, never from the LLM; every row carries its provenance.
    frequency_zipf: Mapped[float | None] = mapped_column(Float)      # SUBTLEX-NL / wordfreq Zipf
    cefr_level: Mapped[str | None] = mapped_column(String(5))        # NT2Lex-assigned CEFR band
    ipa: Mapped[str | None] = mapped_column(String(100))             # Wiktionary IPA
    contrast_note_es: Mapped[str | None] = mapped_column(Text)       # ES→NL transfer trap note
    cloze_sentences_json: Mapped[dict | list | None] = mapped_column(JSON)
    source: Mapped[str | None] = mapped_column(String(100))         # e.g. tatoeba#123, wiktionary
    source_license: Mapped[str | None] = mapped_column(String(50))
    attribution: Mapped[str | None] = mapped_column(Text)
    validated: Mapped[bool | None] = mapped_column(default=False)

    sr_cards: Mapped[list["SRCard"]] = relationship(back_populates="vocab_item")


class GrammarTopic(Base):
    __tablename__ = "grammar_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    name_nl: Mapped[str | None] = mapped_column(String(200))
    name_es: Mapped[str | None] = mapped_column(String(200))
    level: Mapped[str | None] = mapped_column(String(5), index=True)
    description_es: Mapped[str | None] = mapped_column(Text)
    examples_json: Mapped[dict | list | None] = mapped_column(JSON)  # list of {nl, es, notes}
    source: Mapped[str | None] = mapped_column(String(100))
    source_license: Mapped[str | None] = mapped_column(String(50))
    attribution: Mapped[str | None] = mapped_column(Text)
    validated: Mapped[bool | None] = mapped_column(default=False)


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    title_nl: Mapped[str | None] = mapped_column(String(200))
    title_es: Mapped[str | None] = mapped_column(String(200))
    level: Mapped[str | None] = mapped_column(String(5), index=True)
    content_nl: Mapped[str | None] = mapped_column(Text)
    content_es: Mapped[str | None] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(String(500))
    questions_json: Mapped[dict | list | None] = mapped_column(JSON)
    theme: Mapped[str | None] = mapped_column(String(50))
    new_words_json: Mapped[dict | list | None] = mapped_column(JSON)  # i+1 budget: ≤5 new lemmas
    source: Mapped[str | None] = mapped_column(String(100))
    source_license: Mapped[str | None] = mapped_column(String(50))
    attribution: Mapped[str | None] = mapped_column(Text)
    validated: Mapped[bool | None] = mapped_column(default=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(50), default="learner")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    settings_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    xp_total: Mapped[int | None] = mapped_column(Integer, default=0)
    streak_days: Mapped[int | None] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[str | None] = mapped_column(String(10))  # ISO date string

    sr_cards: Mapped[list["SRCard"]] = relationship(back_populates="user")
    sessions: Mapped[list["LearningSession"]] = relationship(back_populates="user")


class SRCard(Base):
    """FSRS spaced-repetition card for a single vocabulary item."""
    __tablename__ = "sr_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    vocab_item_id: Mapped[int] = mapped_column(ForeignKey("vocabulary_items.id"))
    # FSRS fields
    stability: Mapped[float | None] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float | None] = mapped_column(Float, default=5.0)
    elapsed_days: Mapped[int | None] = mapped_column(Integer, default=0)
    scheduled_days: Mapped[int | None] = mapped_column(Integer, default=0)
    reps: Mapped[int | None] = mapped_column(Integer, default=0)
    lapses: Mapped[int | None] = mapped_column(Integer, default=0)
    state: Mapped[int | None] = mapped_column(Integer, default=0)  # FSRS State value
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    last_review: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="sr_cards")
    vocab_item: Mapped["VocabularyItem"] = relationship(back_populates="sr_cards")


class JobRun(Base):
    """Latest run of each background maintenance job (one row per job)."""
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_status: Mapped[str | None] = mapped_column(String(10))   # ok | error | skipped
    detail: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class ReviewLog(Base):
    """One row per FSRS review — the raw data the FSRS optimizer trains on.

    Created on every review from day one (handoff Part E: every day without
    this table is unrecoverable optimizer data).
    """
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("sr_cards.id"), index=True)
    vocab_item_id: Mapped[int] = mapped_column(ForeignKey("vocabulary_items.id"))
    rating: Mapped[int] = mapped_column(Integer)        # 1=Again, 2=Hard, 3=Good, 4=Easy
    state_before: Mapped[int] = mapped_column(Integer)  # FSRS state at review time
    state_after: Mapped[int] = mapped_column(Integer)
    stability_before: Mapped[float | None] = mapped_column(Float)
    stability_after: Mapped[float | None] = mapped_column(Float)
    difficulty_after: Mapped[float | None] = mapped_column(Float)
    elapsed_days: Mapped[int | None] = mapped_column(Integer, default=0)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), index=True
    )


class LearningSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    xp_earned: Mapped[int | None] = mapped_column(Integer, default=0)
    exercises_completed: Mapped[int | None] = mapped_column(Integer, default=0)
    game_type: Mapped[str | None] = mapped_column(String(50))

    user: Mapped["User"] = relationship(back_populates="sessions")
