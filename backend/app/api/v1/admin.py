"""Maintenance endpoints: inspect and trigger background jobs from the UI."""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import JobRun
from app.db.session import get_db
from app.services.scheduler import JOB_REGISTRY, run_job

router = APIRouter()

# Jobs that can run for a long time get dispatched to the background
LONG_RUNNING = {"content_refresh"}


class JobOut(BaseModel):
    name: str
    description: str
    enabled: bool
    interval_hours: float
    last_run_at: datetime | None = None
    last_status: str | None = None
    detail: str | None = None
    duration_ms: int | None = None


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    runs = {r.job_name: r for r in db.query(JobRun).all()}
    return [
        JobOut(
            name=spec.name,
            description=spec.description,
            enabled=spec.enabled(),
            interval_hours=spec.interval.total_seconds() / 3600,
            last_run_at=runs[spec.name].last_run_at if spec.name in runs else None,
            last_status=runs[spec.name].last_status if spec.name in runs else None,
            detail=runs[spec.name].detail if spec.name in runs else None,
            duration_ms=runs[spec.name].duration_ms if spec.name in runs else None,
        )
        for spec in JOB_REGISTRY.values()
    ]


def _run_in_background(name: str) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        run_job(db, name, force=True)
    finally:
        db.close()


@router.post("/jobs/{name}/run")
def trigger_job(name: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    if name not in JOB_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown job '{name}'")
    if name in LONG_RUNNING:
        background.add_task(_run_in_background, name)
        return {"name": name, "started": True, "background": True}
    row = run_job(db, name, force=True)
    return {
        "name": name,
        "started": True,
        "background": False,
        "status": row.last_status,
        "detail": row.detail,
    }
