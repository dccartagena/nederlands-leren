import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models
from app.db.session import engine

logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    app = FastAPI(
        title="Nederlands Leren API",
        version="1.0.0",
        description="Dutch language learning app — Dutch ↔ Spanish",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    audio_dir = str(settings.AUDIO_DIR)
    os.makedirs(audio_dir, exist_ok=True)
    app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")

    @app.on_event("startup")
    async def startup():
        models.Base.metadata.create_all(bind=engine)

        if not settings.SCHEDULER_ENABLED:
            return

        # Seed content immediately so a fresh install works without manual
        # steps, then start the background scheduler for recurring jobs.
        if settings.AUTO_SEED:
            from app.db.session import SessionLocal
            from app.services.scheduler import run_job

            def _seed() -> None:
                db = SessionLocal()
                try:
                    run_job(db, "seed_content", force=True)
                except Exception:  # noqa: BLE001 — startup must not fail on seed
                    logger.exception("startup seed failed")
                finally:
                    db.close()

            await asyncio.to_thread(_seed)

        from app.services.scheduler import scheduler_loop

        app.state.scheduler_task = asyncio.create_task(scheduler_loop())

    @app.on_event("shutdown")
    async def shutdown():
        task = getattr(app.state, "scheduler_task", None)
        if task:
            task.cancel()

    return app


app = create_application()
