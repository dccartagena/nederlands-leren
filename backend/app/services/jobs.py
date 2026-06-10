"""
Background maintenance jobs. Each job is a plain function taking a DB session
and returning a one-line summary; the scheduler records the outcome in the
job_runs table. Raising marks the run as "error"; returning a string starting
with "skipped" marks it "skipped".
"""
import json
import logging
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import LearningSession, ReviewLog, SRCard, User, VocabularyItem
from app.services import audio_service, content_seeder, spaced_repetition

logger = logging.getLogger(__name__)

OPTIMIZER_MIN_LOGS = 1000


# ── Shared export payload (used by the API route and the backup job) ─────────

def build_export_payload(db: Session, user: User) -> dict[str, Any]:
    cards = db.query(SRCard).filter_by(user_id=user.id).all()
    sessions = db.query(LearningSession).filter_by(user_id=user.id).all()
    review_logs = db.query(ReviewLog).filter_by(user_id=user.id).all()
    return {
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
        # Raw FSRS review history — the optimizer's training data
        "review_logs": [
            {
                "vocab_item_id": r.vocab_item_id,
                "rating": r.rating,
                "state_before": r.state_before,
                "state_after": r.state_after,
                "stability_before": r.stability_before,
                "stability_after": r.stability_after,
                "difficulty_after": r.difficulty_after,
                "elapsed_days": r.elapsed_days,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            }
            for r in review_logs
        ],
    }


# ── Jobs ─────────────────────────────────────────────────────────────────────

def seed_content(db: Session) -> str:
    """Idempotent seed of data/ JSON into the DB + ATTRIBUTIONS.md refresh."""
    return content_seeder.seed_all(db)


def backup_progress(db: Session) -> str:
    """Write a dated progress export to data/backups/ and prune old ones."""
    user = db.query(User).filter_by(id=1).first()
    if not user:
        return "skipped: no user yet"

    backups_dir = settings.DATA_DIR / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    payload = build_export_payload(db, user)
    path = backups_dir / f"progress-{date.today().isoformat()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False))

    backups = sorted(backups_dir.glob("progress-*.json"))
    pruned = 0
    for old in backups[: -settings.BACKUP_RETENTION]:
        old.unlink()
        pruned += 1
    return f"backup written → {path.name} ({pruned} old pruned)"


def audio_gapfill(db: Session) -> str:
    """Pre-warm audio for vocabulary items that have none, batch-capped."""
    items = db.query(VocabularyItem).all()
    missing = [
        i for i in items
        if audio_service.resolve_vocab_audio(i.dutch_word, i.level, i.article) is None
    ]
    if not missing:
        return f"all {len(items)} items have audio"

    generated, failed = 0, 0
    for item in missing[: settings.AUDIO_GAPFILL_BATCH]:
        try:
            audio_service.ensure_vocab_audio(item.dutch_word, item.level, item.article)
            generated += 1
        except Exception:  # noqa: BLE001 — offline/gTTS quota: keep going
            failed += 1
    remaining = len(missing) - generated
    return f"{generated} generated, {failed} failed, {remaining} still missing"


def fsrs_optimize(db: Session) -> str:
    """Compute optimal FSRS parameters once enough review history exists."""
    log_count = db.query(func.count(ReviewLog.id)).scalar() or 0
    if log_count < OPTIMIZER_MIN_LOGS:
        return f"skipped: {log_count}/{OPTIMIZER_MIN_LOGS} review logs"

    try:
        from fsrs import Optimizer, Rating
        from fsrs import ReviewLog as FSRSReviewLog

        rows = db.query(ReviewLog).order_by(ReviewLog.reviewed_at).all()
        fsrs_logs = [
            FSRSReviewLog(
                card_id=r.card_id,
                rating=Rating(r.rating),
                review_datetime=(
                    r.reviewed_at.replace(tzinfo=UTC)
                    if r.reviewed_at and r.reviewed_at.tzinfo is None
                    else r.reviewed_at
                ),
                review_duration=None,
            )
            for r in rows
        ]
        optimizer = Optimizer(fsrs_logs)
        parameters = list(optimizer.compute_optimal_parameters())
    except ImportError:
        return 'skipped: install the optimizer extra — pip install "fsrs[optimizer]"'

    params_file = settings.DATA_DIR / "fsrs_params.json"
    params_file.write_text(json.dumps({
        "parameters": parameters,
        "computed_at": datetime.now(UTC).isoformat(),
        "review_logs_used": log_count,
    }))
    spaced_repetition.set_parameters(parameters)
    return f"parameters optimized from {log_count} logs → {params_file.name}"


# ETL steps run as subprocesses so a crash can't take the app down with it.
_ETL_STEPS: list[tuple[str, list[str], int]] = [
    ("fetch_sources", ["scripts/etl/fetch_sources.py"], 7200),
    ("build_lexicon", ["scripts/etl/build_lexicon.py"], 3600),
    ("build_sentences", ["scripts/etl/build_sentences.py"], 3600),
    ("validate", ["scripts/etl/validate.py", "--stamp"], 1800),
    ("coverage_report", ["scripts/etl/coverage_report.py"], 600),
]


def content_refresh(db: Session) -> str:
    """Monthly-style content refresh: ETL pipeline + reseed, end to end."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    results = []
    for name, args, timeout in _ETL_STEPS:
        proc = subprocess.run(  # noqa: S603
            [sys.executable, *args],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # validate exits 1 when items land in the review queue — that's a
        # normal outcome, not a pipeline failure
        ok = proc.returncode == 0 or name == "validate"
        results.append(f"{name}:{'ok' if proc.returncode == 0 else f'rc={proc.returncode}'}")
        if not ok:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            raise RuntimeError(f"{name} failed (rc={proc.returncode}): {' / '.join(tail)}")

    seed_summary = content_seeder.seed_all(db)
    return f"{', '.join(results)}; {seed_summary}"
