from fastapi import APIRouter

from app.api.v1 import admin, content, exercises, grammar, health, llm, progress, stories, vocabulary

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["vocabulary"])
api_router.include_router(grammar.router, prefix="/grammar", tags=["grammar"])
api_router.include_router(stories.router, prefix="/stories", tags=["stories"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
