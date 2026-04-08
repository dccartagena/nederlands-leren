from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import User, SRCard, VocabularyItem
from app.schemas import ReviewRequest, ReviewResponse, DueCardOut, UserProgressOut
from app.services import spaced_repetition

router = APIRouter()

DEFAULT_USER_ID = 1  # Single-user app


def _ensure_user(db: Session) -> User:
    user = db.query(User).filter_by(id=DEFAULT_USER_ID).first()
    if not user:
        user = User(id=DEFAULT_USER_ID, username="learner")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/user", response_model=UserProgressOut)
def get_user_progress(db: Session = Depends(get_db)):
    return _ensure_user(db)


@router.get("/due", response_model=List[DueCardOut])
def get_due_cards(limit: int = Query(20, le=50), db: Session = Depends(get_db)):
    _ensure_user(db)
    cards = spaced_repetition.get_due_cards(db, DEFAULT_USER_ID, limit)
    # Eagerly load vocab items
    result = []
    for card in cards:
        vocab = db.query(VocabularyItem).filter_by(id=card.vocab_item_id).first()
        if vocab:
            result.append(card)
    return result


@router.post("/review", response_model=ReviewResponse)
def record_review(req: ReviewRequest, db: Session = Depends(get_db)):
    _ensure_user(db)
    if req.rating not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Rating must be 1–4")
    sr, xp = spaced_repetition.review_card(db, req.card_id, req.rating, DEFAULT_USER_ID)
    return ReviewResponse(
        card_id=sr.id,
        next_due=sr.due_date,
        stability=sr.stability,
        state=sr.state,
        xp_earned=xp,
    )


@router.post("/enroll/{vocab_item_id}")
def enroll_card(vocab_item_id: int, db: Session = Depends(get_db)):
    _ensure_user(db)
    item = db.query(VocabularyItem).filter_by(id=vocab_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")
    card = spaced_repetition.get_or_create_card(db, DEFAULT_USER_ID, vocab_item_id)
    return {"card_id": card.id, "message": "enrolled"}
