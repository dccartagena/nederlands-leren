from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas import ChatRequest, ExplainRequest, FeedbackRequest, GenerateExerciseRequest
from app.services import llm_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/explain")
@limiter.limit("30/minute")
async def explain_word(request: Request, req: ExplainRequest):
    try:
        result = await llm_service.explain(req.word_or_phrase, req.context_sentence)
        return {"explanation": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/feedback")
@limiter.limit("30/minute")
async def get_feedback(request: Request, req: FeedbackRequest):
    try:
        result = await llm_service.feedback(req.question, req.correct_answer, req.user_answer)
        return {"feedback": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/generate-exercise")
@limiter.limit("20/minute")
async def generate_exercise(request: Request, req: GenerateExerciseRequest):
    try:
        result = await llm_service.generate_exercise(
            req.theme, req.level, req.exercise_type, req.word
        )
        return {"exercise": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        reply = await llm_service.chat_completion(messages, provider_override=req.provider)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
