from fastapi import APIRouter

from app.api.v1 import health, vocabulary, progress, llm, grammar, stories, exercises

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["vocabulary"])
api_router.include_router(grammar.router, prefix="/grammar", tags=["grammar"])
api_router.include_router(stories.router, prefix="/stories", tags=["stories"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
