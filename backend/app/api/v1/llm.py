from fastapi import APIRouter, HTTPException
from app.schemas import ExplainRequest, FeedbackRequest, GenerateExerciseRequest, ChatRequest
from app.services import llm_service

router = APIRouter()


@router.post("/explain")
async def explain_word(req: ExplainRequest):
    try:
        result = await llm_service.explain(req.word_or_phrase, req.context_sentence)
        return {"explanation": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/feedback")
async def get_feedback(req: FeedbackRequest):
    try:
        result = await llm_service.feedback(req.question, req.correct_answer, req.user_answer)
        return {"feedback": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/generate-exercise")
async def generate_exercise(req: GenerateExerciseRequest):
    try:
        result = await llm_service.generate_exercise(
            req.theme, req.level, req.exercise_type, req.word
        )
        return {"exercise": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/chat")
async def chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        reply = await llm_service.chat_completion(messages, provider_override=req.provider)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
