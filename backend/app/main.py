import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db import models
from app.db.session import engine


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'none'; object-src 'none'"
        )
        return response


def create_application() -> FastAPI:
    app = FastAPI(
        title="Nederlands Leren API",
        version="1.0.0",
        description="Dutch language learning app — Dutch ↔ Spanish",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
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
