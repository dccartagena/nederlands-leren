"""
FSRS spaced-repetition service wrapper using fsrs 6.x (Scheduler API).
"""
from datetime import UTC, date, datetime

from fsrs import Card, Rating, Scheduler, State
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import ReviewLog, SRCard, User

# Desired retention 0.90 per the spacing-literature recommendation; the
# scheduler becomes optimizable once enough ReviewLog rows accrue (~1,000).
DESIRED_RETENTION = 0.90
# Daily cap on cards introduced from the New state so reviews don't snowball
NEW_CARDS_PER_DAY = 15

_scheduler = Scheduler(desired_retention=DESIRED_RETENTION)


def set_parameters(parameters: list[float] | None) -> None:
    """Apply FSRS parameters (e.g. from the optimizer job)."""
    global _scheduler
    if parameters:
        _scheduler = Scheduler(parameters=parameters, desired_retention=DESIRED_RETENTION)
    else:
        _scheduler = Scheduler(desired_retention=DESIRED_RETENTION)


def _load_persisted_parameters() -> None:
    """Pick up optimizer output from a previous run, if any."""
    import json

    from app.core.config import settings

    params_file = settings.DATA_DIR / "fsrs_params.json"
    try:
        if params_file.exists():
            set_parameters(json.loads(params_file.read_text()).get("parameters"))
    except Exception:  # noqa: BLE001 — bad file must never break scheduling
        pass


_load_persisted_parameters()

_RATING_MAP = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}
_XP_MAP = {1: 2, 2: 5, 3: 10, 4: 15}


def _orm_to_card(sr: SRCard) -> Card:
    card = Card()
    stability = sr.stability or 0.0
    # FSRS raises ZeroDivisionError (stability ** -param) when stability is 0.0
    # for cards that have already been reviewed (state > New). Use minimum of 1.0.
    if stability == 0.0 and (sr.state or 0) > 0:
        stability = 1.0
    card.stability = stability
    card.difficulty = sr.difficulty or 5.0
    card.state = State(sr.state)
    card.due = sr.due_date or datetime.now(UTC)
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


def review_card(db: Session, card_id: int, rating_int: int, user_id: int, xp_multiplier: float = 1.0):
    sr = db.query(SRCard).filter_by(id=card_id, user_id=user_id).first()
    if not sr:
        raise ValueError(f"Card {card_id} not found for user {user_id}")

    state_before = sr.state or 0
    stability_before = sr.stability or 0.0
    last_review = sr.last_review

    card = _orm_to_card(sr)
    rating = _RATING_MAP.get(rating_int, Rating.Good)
    updated_card, _ = _scheduler.review_card(card, rating)
    _card_to_orm(updated_card, sr)

    elapsed = 0
    if last_review:
        last = last_review if last_review.tzinfo else last_review.replace(tzinfo=UTC)
        elapsed = max(0, (datetime.now(UTC) - last).days)
    db.add(
        ReviewLog(
            user_id=user_id,
            card_id=sr.id,
            vocab_item_id=sr.vocab_item_id,
            rating=rating_int,
            state_before=state_before,
            state_after=sr.state,
            stability_before=stability_before,
            stability_after=sr.stability,
            difficulty_after=sr.difficulty,
            elapsed_days=elapsed,
            reviewed_at=datetime.now(UTC),
        )
    )

    xp = round(_XP_MAP.get(rating_int, 10) * xp_multiplier)
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        user.xp_total = (user.xp_total or 0) + xp

    db.commit()
    db.refresh(sr)
    return sr, xp


def new_cards_introduced_today(db: Session, user_id: int) -> int:
    """Distinct cards whose first-ever review happened since local midnight.

    fsrs 6.x has no New state (fresh cards start in Learning), so a card is
    "new" until its first review — i.e. while reps == 0.
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    first_reviews = (
        db.query(
            ReviewLog.card_id,
            func.min(ReviewLog.reviewed_at).label("first_at"),
        )
        .filter(ReviewLog.user_id == user_id)
        .group_by(ReviewLog.card_id)
        .subquery()
    )
    return (
        db.query(func.count())
        .select_from(first_reviews)
        .filter(first_reviews.c.first_at >= today_start)
        .scalar()
        or 0
    )


def get_due_cards(db: Session, user_id: int, limit: int = 20):
    """Due cards ordered by due date, with unseen cards capped per day.

    Already-introduced cards (reps > 0) are always served; never-reviewed
    cards only fill the remaining slots of today's new-card allowance.
    """
    now = datetime.now(UTC)
    due = (
        db.query(SRCard)
        .filter(SRCard.user_id == user_id, SRCard.due_date <= now)
        .order_by(SRCard.due_date)
        .all()
    )
    new_allowance = max(0, NEW_CARDS_PER_DAY - new_cards_introduced_today(db, user_id))
    result = []
    for card in due:
        if (card.reps or 0) == 0:
            if new_allowance <= 0:
                continue
            new_allowance -= 1
        result.append(card)
        if len(result) >= limit:
            break
    return result


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
