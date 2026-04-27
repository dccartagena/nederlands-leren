import logging
from contextlib import contextmanager
from typing import Generator

from fastapi import APIRouter, HTTPException, Request

from app.core.limiter import limiter
from app.schemas import ChatRequest, ExplainRequest, FeedbackRequest, GenerateExerciseRequest
from app.services import llm_service

router = APIRouter()
logger = logging.getLogger(__name__)


@contextmanager
def _llm_error_handler() -> Generator[None, None, None]:
    try:
        yield
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("LLM call failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@router.post("/explain")
@limiter.limit("20/minute")
async def explain_word(request: Request, req: ExplainRequest):
    with _llm_error_handler():
        result = await llm_service.explain(req.word_or_phrase, req.context_sentence)
        return {"explanation": result}


@router.post("/feedback")
@limiter.limit("20/minute")
async def get_feedback(request: Request, req: FeedbackRequest):
    with _llm_error_handler():
        result = await llm_service.feedback(req.question, req.correct_answer, req.user_answer)
        return {"feedback": result}


@router.post("/generate-exercise")
@limiter.limit("10/minute")
async def generate_exercise(request: Request, req: GenerateExerciseRequest):
    with _llm_error_handler():
        result = await llm_service.generate_exercise(
            req.theme, req.level, req.exercise_type, req.word
        )
        return {"exercise": result}


@router.post("/chat")
@limiter.limit("15/minute")
async def chat(request: Request, req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    with _llm_error_handler():
        reply = await llm_service.chat_completion(messages, provider_override=req.provider)
        return {"reply": reply}
