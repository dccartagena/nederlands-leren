from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import random
import re

from app.db.session import get_db
from app.db.models import VocabularyItem, AudioFile
from app.services.audio_service import synthesize_if_missing

router = APIRouter()


def _get_audio_filename(item: VocabularyItem, db: Session) -> Optional[str]:
    """Return a filename (relative to AUDIO_DIR) for the item, synthesizing if needed."""
    if item.audio_files:
        return item.audio_files[0].file_path

    text = f"{item.article} {item.dutch_word}" if item.article else item.dutch_word
    try:
        path = synthesize_if_missing(text)
        filename = path.name
        af = AudioFile(
            vocab_item_id=item.id,
            sentence_text_nl=text,
            file_path=filename,
            source="gtts",
            license="CC0",
        )
        db.add(af)
        db.commit()
        db.refresh(af)
        return filename
    except Exception:
        return None


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

    audio_filename = _get_audio_filename(correct, db)

    return {
        "correct_id": correct.id,
        "correct_dutch": correct.dutch_word,
        "audio_files": [audio_filename] if audio_filename else [],
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


@router.get("/fill-blank")
def fill_blank_exercise(
    level: str = Query("a0"),
    theme: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return a fill-in-the-blank exercise using a vocabulary example sentence.

    The target word is replaced by ___ in the Dutch sentence. Three distractor
    words (same level) are included to form a 4-option multiple-choice question.
    """
    q = db.query(VocabularyItem).filter(VocabularyItem.level == level)
    if theme:
        q = q.filter(VocabularyItem.theme == theme)
    items = q.all()

    # Only items whose example sentence contains the dutch_word
    candidates = [
        i for i in items
        if i.example_nl and re.search(r'\b' + re.escape(i.dutch_word) + r'\b', i.example_nl, re.IGNORECASE)
    ]
    if not candidates or len(items) < 4:
        return {"error": "Not enough vocabulary items with example sentences for this level/theme"}

    correct = random.choice(candidates)
    # Replace the first occurrence of the target word in the sentence (case-preserving)
    sentence_with_blank = re.sub(
        r'\b' + re.escape(correct.dutch_word) + r'\b',
        '___',
        correct.example_nl,
        count=1,
        flags=re.IGNORECASE,
    )
    distractors = random.sample([i for i in items if i.id != correct.id], min(3, len(items) - 1))
    options = distractors + [correct]
    random.shuffle(options)

    return {
        "sentence_with_blank": sentence_with_blank,
        "sentence_es": correct.example_es or "",
        "correct_id": correct.id,
        "correct_word": correct.dutch_word,
        "options": [
            {"id": o.id, "dutch_word": o.dutch_word, "article": o.article}
            for o in options
        ],
    }


@router.get("/unscramble")
def unscramble_exercise(
    level: str = Query("a0"),
    theme: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return a sentence-unscramble exercise.

    Words from a Dutch example sentence are shuffled; the learner must put them
    back in the correct order.
    """
    q = db.query(VocabularyItem).filter(VocabularyItem.level == level)
    if theme:
        q = q.filter(VocabularyItem.theme == theme)
    items = q.all()

    # Need sentences with at least 3 words
    candidates = [
        i for i in items
        if i.example_nl and len(i.example_nl.split()) >= 3
    ]
    if not candidates:
        return {"error": "Not enough vocabulary items with example sentences for this level/theme"}

    item = random.choice(candidates)
    # Strip a single trailing period for cleaner token display, keep it to re-attach
    sentence = item.example_nl.removesuffix('.')
    trailing_punct = '.' if item.example_nl.endswith('.') else ''
    words = sentence.split()

    # Shuffle until order differs from original
    shuffled = words[:]
    for _ in range(10):
        random.shuffle(shuffled)
        if shuffled != words:
            break

    return {
        "vocab_id": item.id,
        "shuffled_words": shuffled,
        "correct_sentence": item.example_nl,
        "sentence_es": item.example_es or "",
        "trailing_punct": trailing_punct,
    }
