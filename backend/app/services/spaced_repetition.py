"""
FSRS spaced-repetition service wrapper using fsrs 6.x (Scheduler API).
"""
from datetime import datetime, timezone
from fsrs import Scheduler, Card, Rating, State
from sqlalchemy.orm import Session

from app.db.models import SRCard, VocabularyItem, User


_scheduler = Scheduler()

_RATING_MAP = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}
_XP_MAP = {1: 2, 2: 5, 3: 10, 4: 15}


def _orm_to_card(sr: SRCard) -> Card:
    card = Card()
    card.stability = sr.stability or 0.0
    card.difficulty = sr.difficulty or 5.0
    card.state = State(sr.state)
    card.due = sr.due_date or datetime.now(timezone.utc)
    card.last_review = sr.last_review
    return card


def _card_to_orm(card: Card, sr: SRCard) -> SRCard:
    sr.stability = card.stability
    sr.difficulty = card.difficulty
    sr.state = card.state.value
    sr.due_date = card.due
    sr.last_review = card.last_review
    sr.reps = (sr.reps or 0) + 1
    return sr


def review_card(db: Session, card_id: int, rating_int: int, user_id: int):
    sr = db.query(SRCard).filter_by(id=card_id, user_id=user_id).first()
    if not sr:
        raise ValueError(f"Card {card_id} not found for user {user_id}")

    card = _orm_to_card(sr)
    rating = _RATING_MAP.get(rating_int, Rating.Good)
    updated_card, _ = _scheduler.review_card(card, rating)
    _card_to_orm(updated_card, sr)

    xp = _XP_MAP.get(rating_int, 10)
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        user.xp_total = (user.xp_total or 0) + xp

    db.commit()
    db.refresh(sr)
    return sr, xp


def get_due_cards(db: Session, user_id: int, limit: int = 20):
    now = datetime.now(timezone.utc)
    return (
        db.query(SRCard)
        .filter(SRCard.user_id == user_id, SRCard.due_date <= now)
        .order_by(SRCard.due_date)
        .limit(limit)
        .all()
    )


def get_or_create_card(db: Session, user_id: int, vocab_item_id: int) -> SRCard:
    sr = db.query(SRCard).filter_by(user_id=user_id, vocab_item_id=vocab_item_id).first()
    if not sr:
        card = Card()
        sr = SRCard(
            user_id=user_id,
            vocab_item_id=vocab_item_id,
            stability=card.stability,
            difficulty=card.difficulty,
            state=card.state.value,
            due_date=card.due,
        )
        db.add(sr)
        db.commit()
        db.refresh(sr)
    return sr
