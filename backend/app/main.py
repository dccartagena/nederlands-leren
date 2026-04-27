import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models
from app.db.session import engine


def create_application() -> FastAPI:
    app = FastAPI(
        title="Nederlands Leren API",
        version="1.0.0",
        description="Dutch language learning app — Dutch ↔ Spanish",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
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

    return app


app = create_application()
