from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import LearningSession, SRCard, User, VocabularyItem
from app.db.session import get_db
from app.schemas import (
    DueCardOut,
    MasteryStatsOut,
    QuestOut,
    ReviewRequest,
    ReviewResponse,
    StoryCompleteRequest,
    StoryCompleteResponse,
    UserProgressOut,
)
from app.services import spaced_repetition

router = APIRouter()

DEFAULT_USER_ID = 1  # Single-user app

# A card counts as "mastered" once its FSRS stability exceeds 21 days
MASTERY_STABILITY_DAYS = 21.0
COMBO_XP_MULTIPLIER = 1.5
MAX_BANKED_FREEZES = 1

# ── Achievement definitions ──────────────────────────────────────────────────
# Each condition receives (user, enrolled_card_count, settings_context_dict).
# settings_context = user.settings_json merged with any transient extra flags
# plus "mastered_count" (cards with stability > MASTERY_STABILITY_DAYS).

ACHIEVEMENTS = [
    {"slug": "first_word",      "condition": lambda u, n, ctx: n >= 1},
    {"slug": "ten_words",       "condition": lambda u, n, ctx: n >= 10},
    {"slug": "streak_3",        "condition": lambda u, n, ctx: u.streak_days >= 3},
    {"slug": "streak_7",        "condition": lambda u, n, ctx: u.streak_days >= 7},
    {"slug": "streak_30",       "condition": lambda u, n, ctx: u.streak_days >= 30},
    {"slug": "streak_100",      "condition": lambda u, n, ctx: u.streak_days >= 100},
    {"slug": "hundred_xp",      "condition": lambda u, n, ctx: u.xp_total >= 100},
    # Mastery tiers: cards whose FSRS stability passed 21 days
    {"slug": "mastered_10",     "condition": lambda u, n, ctx: ctx.get("mastered_count", 0) >= 10},
    {"slug": "mastered_50",     "condition": lambda u, n, ctx: ctx.get("mastered_count", 0) >= 50},
    {"slug": "mastered_150",    "condition": lambda u, n, ctx: ctx.get("mastered_count", 0) >= 150},
    {"slug": "mastered_300",    "condition": lambda u, n, ctx: ctx.get("mastered_count", 0) >= 300},
    # Triggered when a story quiz is answered perfectly (passed via extra context)
    {"slug": "perfect_session", "condition": lambda u, n, ctx: ctx.get("perfect_quiz", False)},
    # Story completion milestones (tracked in settings_json["completed_stories"])
    {"slug": "first_story",     "condition": lambda u, n, ctx: len(ctx.get("completed_stories", [])) >= 1},
    {"slug": "story_streak",    "condition": lambda u, n, ctx: len(ctx.get("completed_stories", [])) >= 5},
    {"slug": "stories_15",      "condition": lambda u, n, ctx: len(ctx.get("completed_stories", [])) >= 15},
    {"slug": "stories_40",      "condition": lambda u, n, ctx: len(ctx.get("completed_stories", [])) >= 40},
]


def _ensure_user(db: Session) -> User:
    user = db.query(User).filter_by(id=DEFAULT_USER_ID).first()
    if not user:
        user = User(id=DEFAULT_USER_ID, username="learner")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _update_streak(user: User) -> None:
    """Advance the streak, consuming a banked freeze to bridge a single missed day.

    Freezes are earned (1 banked max) every time the streak crosses a multiple
    of 7 — loss-aversion guard from the SDT gamification spec.
    """
    settings = dict(user.settings_json or {})
    freezes = int(settings.get("streak_freezes", 0))

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    day_before = (date.today() - timedelta(days=2)).isoformat()

    if user.last_activity_date == today:
        return
    if user.last_activity_date == yesterday:
        user.streak_days = (user.streak_days or 0) + 1
    elif user.last_activity_date == day_before and freezes > 0:
        # One missed day bridged by a freeze: streak survives
        freezes -= 1
        settings["last_freeze_used"] = yesterday
        user.streak_days = (user.streak_days or 0) + 1
    else:
        user.streak_days = 1
    user.last_activity_date = today

    if user.streak_days % 7 == 0 and freezes < MAX_BANKED_FREEZES:
        freezes += 1

    settings["streak_freezes"] = freezes
    user.settings_json = settings


def _mastered_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(SRCard.id))
        .filter(SRCard.user_id == user_id, SRCard.stability > MASTERY_STABILITY_DAYS)
        .scalar()
        or 0
    )


def _check_achievements(db: Session, user: User, extra: dict | None = None) -> list[str]:
    settings = user.settings_json or {}
    earned: list[dict] = settings.get("achievements", [])
    earned_slugs = {a["slug"] for a in earned}

    enrolled_count = db.query(func.count(SRCard.id)).filter_by(user_id=user.id).scalar() or 0

    # Build context: persisted settings merged with any transient extra flags
    ctx: dict[str, Any] = dict(settings)
    ctx["mastered_count"] = _mastered_count(db, user.id)
    if extra:
        ctx.update(extra)

    newly_earned: list[str] = []
    for achievement in ACHIEVEMENTS:
        slug = achievement["slug"]
        if slug not in earned_slugs and achievement["condition"](user, enrolled_count, ctx):
            earned.append({"slug": slug, "earned_at": datetime.now(UTC).isoformat()})
            newly_earned.append(slug)

    if newly_earned:
        updated = dict(user.settings_json or {})
        updated["achievements"] = earned
        user.settings_json = updated

    return newly_earned


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/user", response_model=UserProgressOut)
def get_user_progress(db: Session = Depends(get_db)):
    return _ensure_user(db)


@router.get("/due", response_model=list[DueCardOut])
def get_due_cards(limit: int = Query(20, le=50), db: Session = Depends(get_db)):
    _ensure_user(db)
    cards = spaced_repetition.get_due_cards(db, DEFAULT_USER_ID, limit)
    result = []
    for card in cards:
        vocab = db.query(VocabularyItem).filter_by(id=card.vocab_item_id).first()
        if vocab:
            result.append(card)
    return result


@router.post("/review", response_model=ReviewResponse)
def record_review(req: ReviewRequest, db: Session = Depends(get_db)):
    user = _ensure_user(db)
    if req.rating not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Rating must be 1–4")
    multiplier = COMBO_XP_MULTIPLIER if req.combo else 1.0
    try:
        sr, xp = spaced_repetition.review_card(
            db, req.card_id, req.rating, DEFAULT_USER_ID, xp_multiplier=multiplier
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _update_streak(user)

    session = LearningSession(
        user_id=DEFAULT_USER_ID,
        started_at=datetime.now(UTC),
        xp_earned=xp,
        exercises_completed=1,
        game_type="review",
    )
    db.add(session)

    new_achievements = _check_achievements(db, user)
    db.commit()

    return ReviewResponse(
        card_id=sr.id,
        next_due=sr.due_date,
        stability=sr.stability,
        state=sr.state,
        xp_earned=xp,
        new_achievements=new_achievements,
    )


@router.post("/enroll/{vocab_item_id}")
def enroll_card(vocab_item_id: int, db: Session = Depends(get_db)):
    user = _ensure_user(db)
    item = db.query(VocabularyItem).filter_by(id=vocab_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Vocabulary item not found")
    card = spaced_repetition.get_or_create_card(db, DEFAULT_USER_ID, vocab_item_id)

    new_achievements = _check_achievements(db, user)
    db.commit()

    return {"card_id": card.id, "message": "enrolled", "new_achievements": new_achievements}


@router.post("/story-complete", response_model=StoryCompleteResponse)
def story_complete(req: StoryCompleteRequest, db: Session = Depends(get_db)):
    user = _ensure_user(db)

    is_perfect = req.total_questions > 0 and req.correct_count == req.total_questions
    xp = 5 + (req.correct_count * 10) + (20 if is_perfect else 0)
    user.xp_total = (user.xp_total or 0) + xp

    _update_streak(user)

    # Persist completed story slug
    settings = dict(user.settings_json or {})
    completed: list[str] = list(set(settings.get("completed_stories", [])) | {req.story_slug})
    settings["completed_stories"] = completed
    user.settings_json = settings

    session = LearningSession(
        user_id=DEFAULT_USER_ID,
        started_at=datetime.now(UTC),
        xp_earned=xp,
        exercises_completed=req.total_questions,
        game_type="story",
    )
    db.add(session)

    new_achievements = _check_achievements(
        db, user, extra={"perfect_quiz": is_perfect, "completed_stories": completed}
    )
    db.commit()

    return StoryCompleteResponse(xp_earned=xp, new_achievements=new_achievements)


@router.get("/history")
def get_xp_history(days: int = Query(7, ge=1, le=365), db: Session = Depends(get_db)):
    _ensure_user(db)
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(
            func.date(LearningSession.started_at).label("day"),
            func.sum(LearningSession.xp_earned).label("xp"),
        )
        .filter(LearningSession.user_id == DEFAULT_USER_ID)
        .filter(LearningSession.started_at >= since)
        .group_by(func.date(LearningSession.started_at))
        .all()
    )
    result_map = {str(row.day): int(row.xp or 0) for row in rows}
    history = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        history.append({"date": d, "xp": result_map.get(d, 0)})
    return history


@router.get("/stats", response_model=MasteryStatsOut)
def get_mastery_stats(db: Session = Depends(get_db)):
    """Competence metrics anchored in real ability (mastered words), not XP."""
    user = _ensure_user(db)
    settings = user.settings_json or {}
    enrolled = db.query(func.count(SRCard.id)).filter_by(user_id=DEFAULT_USER_ID).scalar() or 0
    review_state = (
        db.query(func.count(SRCard.id))
        .filter(SRCard.user_id == DEFAULT_USER_ID, SRCard.state == 2)
        .scalar()
        or 0
    )
    return MasteryStatsOut(
        mastered_words=_mastered_count(db, DEFAULT_USER_ID),
        enrolled_words=enrolled,
        review_words=review_state,
        stories_completed=len(settings.get("completed_stories", [])),
        streak_freezes=int(settings.get("streak_freezes", 0)),
    )


# ── Daily quests ─────────────────────────────────────────────────────────────
# Three optional quests per day: one review quest, one input quest, one XP
# quest. Variants rotate deterministically with the date; progress is computed
# from today's LearningSession rows. Quests are offered, never forced — there
# is no penalty for skipping (the client can hide them).

QUEST_VARIANTS = {
    "review": [
        {"id": "review_10", "title_es": "Repasa 10 tarjetas", "target": 10},
        {"id": "review_20", "title_es": "Repasa 20 tarjetas", "target": 20},
    ],
    "input": [
        {"id": "story_1", "title_es": "Completa 1 historia", "target": 1},
        {"id": "story_2", "title_es": "Completa 2 historias", "target": 2},
    ],
    "xp": [
        {"id": "xp_40", "title_es": "Gana 40 XP", "target": 40},
        {"id": "xp_70", "title_es": "Gana 70 XP", "target": 70},
    ],
}


@router.get("/quests", response_model=list[QuestOut])
def get_daily_quests(db: Session = Depends(get_db)):
    _ensure_user(db)
    today_start = datetime.combine(date.today(), datetime.min.time())
    sessions = (
        db.query(LearningSession)
        .filter(
            LearningSession.user_id == DEFAULT_USER_ID,
            LearningSession.started_at >= today_start,
        )
        .all()
    )
    reviews_today = sum(1 for s in sessions if s.game_type == "review")
    stories_today = sum(1 for s in sessions if s.game_type == "story")
    xp_today = sum(s.xp_earned or 0 for s in sessions)

    seed = date.today().toordinal()
    quests = []
    for i, (category, variants) in enumerate(QUEST_VARIANTS.items()):
        variant = variants[(seed + i) % len(variants)]
        progress = {"review": reviews_today, "input": stories_today, "xp": xp_today}[category]
        progress = min(progress, variant["target"])
        quests.append(
            QuestOut(
                id=variant["id"],
                title_es=variant["title_es"],
                target=variant["target"],
                progress=progress,
                done=progress >= variant["target"],
            )
        )
    return quests


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)) -> Any:
    user = _ensure_user(db)
    return user.settings_json or {}


class SettingsUpdate(BaseModel):
    data: dict[str, Any]


@router.put("/settings")
def update_settings(req: SettingsUpdate, db: Session = Depends(get_db)) -> Any:
    user = _ensure_user(db)
    current = dict(user.settings_json or {})
    current.update(req.data)
    user.settings_json = current
    db.commit()
    return current


# ── Export / Import ──────────────────────────────────────────────────────────

@router.get("/export")
def export_progress(db: Session = Depends(get_db)):
    user = _ensure_user(db)
    cards = db.query(SRCard).filter_by(user_id=DEFAULT_USER_ID).all()
    sessions = db.query(LearningSession).filter_by(user_id=DEFAULT_USER_ID).all()

    payload: dict[str, Any] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "user": {
            "xp_total": user.xp_total,
            "streak_days": user.streak_days,
            "last_activity_date": user.last_activity_date,
            "settings_json": user.settings_json or {},
        },
        "sr_cards": [
            {
                "vocab_item_id": c.vocab_item_id,
                "stability": c.stability,
                "difficulty": c.difficulty,
                "elapsed_days": c.elapsed_days,
                "scheduled_days": c.scheduled_days,
                "reps": c.reps,
                "lapses": c.lapses,
                "state": c.state,
                "due_date": c.due_date.isoformat() if c.due_date else None,
                "last_review": c.last_review.isoformat() if c.last_review else None,
            }
            for c in cards
        ],
        "sessions": [
            {
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "xp_earned": s.xp_earned,
                "game_type": s.game_type,
            }
            for s in sessions
        ],
    }

    today = date.today().isoformat()
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="progress-{today}.json"'},
    )


@router.post("/import")
async def import_progress(db: Session = Depends(get_db)):
    raise HTTPException(status_code=405, detail="Use POST with JSON body")


class ProgressImport(BaseModel):
    exported_at: str | None = None
    user: dict[str, Any] | None = None
    sr_cards: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []


@router.post("/import/json")
def import_progress_json(payload: ProgressImport, db: Session = Depends(get_db)):
    user = _ensure_user(db)

    if payload.user:
        user.xp_total = (user.xp_total or 0) + (payload.user.get("xp_total") or 0)
        imported_streak = payload.user.get("streak_days") or 0
        if imported_streak > (user.streak_days or 0):
            user.streak_days = imported_streak
        if payload.user.get("last_activity_date"):
            user.last_activity_date = payload.user["last_activity_date"]
        if payload.user.get("settings_json"):
            merged = dict(user.settings_json or {})
            merged.update(payload.user["settings_json"])
            user.settings_json = merged

    imported = 0
    for card_data in payload.sr_cards:
        vid = card_data.get("vocab_item_id")
        if not vid:
            continue
        existing = (
            db.query(SRCard)
            .filter_by(user_id=DEFAULT_USER_ID, vocab_item_id=vid)
            .first()
        )
        if existing:
            for field in ("stability", "difficulty", "elapsed_days", "scheduled_days",
                          "reps", "lapses", "state"):
                if field in card_data:
                    setattr(existing, field, card_data[field])
        else:
            db.add(SRCard(user_id=DEFAULT_USER_ID, **{
                k: v for k, v in card_data.items()
                if k in ("vocab_item_id", "stability", "difficulty", "elapsed_days",
                          "scheduled_days", "reps", "lapses", "state")
            }))
            imported += 1

    db.commit()
    return {"imported_cards": imported}
