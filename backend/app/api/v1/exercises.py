from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import random

from app.db.session import get_db
from app.db.models import VocabularyItem

router = APIRouter()


@router.get("/listen-choose")
def listen_choose_exercise(
    level: str = Query("a0"),
    theme: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return a listen-and-choose exercise: one correct item + 3 distractors."""
    q = db.query(VocabularyItem).filter(VocabularyItem.level == level)
    if theme:
        q = q.filter(VocabularyItem.theme == theme)
    items = q.all()
    if len(items) < 4:
        return {"error": "Not enough vocabulary items for this level/theme"}

    correct = random.choice(items)
    distractors = random.sample([i for i in items if i.id != correct.id], 3)
    options = distractors + [correct]
    random.shuffle(options)

    return {
        "correct_id": correct.id,
        "correct_dutch": correct.dutch_word,
        "audio_files": [af.file_path for af in correct.audio_files],
        "options": [
            {"id": o.id, "spanish": o.spanish, "image_url": o.image_url}
            for o in options
        ],
    }


@router.get("/word-match")
def word_match_exercise(
    level: str = Query("a0"),
    theme: Optional[str] = None,
    count: int = Query(6, le=10),
    db: Session = Depends(get_db),
):
    """Return Dutch/Spanish word pairs for word-match game."""
    q = db.query(VocabularyItem).filter(VocabularyItem.level == level)
    if theme:
        q = q.filter(VocabularyItem.theme == theme)
    items = q.all()
    if not items:
        return {"error": "No vocabulary items found"}

    selected = random.sample(items, min(count, len(items)))
    return {
        "pairs": [
            {"id": i.id, "dutch": i.dutch_word, "spanish": i.spanish}
            for i in selected
        ]
    }
