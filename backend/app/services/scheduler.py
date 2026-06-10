"""
In-process background scheduler — right-sized for a single-user local app
(no Celery/Redis). An asyncio task wakes up every SCHEDULER_TICK_SECONDS,
runs whatever jobs are due (in a worker thread, so the event loop never
blocks), and records each outcome in the job_runs table.

Jobs can also be triggered on demand through /api/v1/admin/jobs.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import JobRun
from app.services import jobs

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobSpec:
    name: str
    fn: Callable[[Session], str]
    interval: timedelta
    enabled: Callable[[], bool]
    description: str


JOB_REGISTRY: dict[str, JobSpec] = {
    spec.name: spec
    for spec in (
        JobSpec(
            "seed_content",
            jobs.seed_content,
            timedelta(hours=24),
            lambda: settings.AUTO_SEED,
            "Carga el contenido de data/ en la base de datos (idempotente)",
        ),
        JobSpec(
            "backup_progress",
            jobs.backup_progress,
            timedelta(hours=24),
            lambda: settings.AUTO_BACKUP,
            "Copia de seguridad diaria del progreso en data/backups/",
        ),
        JobSpec(
            "audio_gapfill",
            jobs.audio_gapfill,
            timedelta(hours=24),
            lambda: settings.AUTO_AUDIO_GAPFILL,
            "Genera audio (gTTS) para vocabulario que no lo tiene",
        ),
        JobSpec(
            "fsrs_optimize",
            jobs.fsrs_optimize,
            timedelta(days=7),
            lambda: settings.AUTO_FSRS_OPTIMIZE,
            "Optimiza los parámetros FSRS con tu historial de repasos",
        ),
        JobSpec(
            "content_refresh",
            jobs.content_refresh,
            timedelta(days=7),
            lambda: settings.AUTO_CONTENT_REFRESH,
            "Actualiza léxico/frases (ETL) y resiembra el contenido",
        ),
    )
}


def _get_job_run(db: Session, name: str) -> JobRun:
    row = db.query(JobRun).filter_by(job_name=name).first()
    if not row:
        row = JobRun(job_name=name)
        db.add(row)
    return row


def is_due(db: Session, spec: JobSpec, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    row = db.query(JobRun).filter_by(job_name=spec.name).first()
    if not row or not row.last_run_at:
        return True
    last = row.last_run_at if row.last_run_at.tzinfo else row.last_run_at.replace(tzinfo=UTC)
    return now - last >= spec.interval


def run_job(db: Session, name: str, force: bool = False) -> JobRun:
    """Run one job (respecting its enable flag and interval unless forced)."""
    spec = JOB_REGISTRY[name]
    row = _get_job_run(db, name)

    if not force:
        if not spec.enabled():
            return row
        if not is_due(db, spec):
            return row

    started = time.monotonic()
    row.last_run_at = datetime.now(UTC)
    try:
        detail = spec.fn(db)
        row.last_status = "skipped" if detail.startswith("skipped") else "ok"
        row.detail = detail
    except Exception as exc:  # noqa: BLE001 — a failing job must not kill the loop
        db.rollback()
        row = _get_job_run(db, name)
        row.last_run_at = datetime.now(UTC)
        row.last_status = "error"
        row.detail = f"{type(exc).__name__}: {exc}"
        logger.exception("job %s failed", name)
    row.duration_ms = int((time.monotonic() - started) * 1000)
    db.commit()
    return row


def run_pending(db: Session) -> None:
    for name in JOB_REGISTRY:
        run_job(db, name)


async def scheduler_loop() -> None:
    """Wake periodically and run due jobs in a worker thread."""
    from app.db.session import SessionLocal

    def _tick() -> None:
        db = SessionLocal()
        try:
            run_pending(db)
        finally:
            db.close()

    while True:
        try:
            await asyncio.to_thread(_tick)
        except Exception:  # noqa: BLE001
            logger.exception("scheduler tick failed")
        await asyncio.sleep(settings.SCHEDULER_TICK_SECONDS)
