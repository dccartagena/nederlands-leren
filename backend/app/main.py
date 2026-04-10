import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.db import models
from app.db.session import engine

limiter = Limiter(key_func=get_remote_address)


def create_application() -> FastAPI:
    app = FastAPI(
        title="Nederlands Leren API",
        version="1.0.0",
        description="Dutch language learning app — Dutch ↔ Spanish",
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    # Serve audio files
    audio_dir = str(settings.AUDIO_DIR)
    os.makedirs(audio_dir, exist_ok=True)
    app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")

    @app.on_event("startup")
    async def startup():
        models.Base.metadata.create_all(bind=engine)

    return app


app = create_application()
