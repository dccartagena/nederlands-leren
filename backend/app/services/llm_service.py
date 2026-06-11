"""
LLM service — Gemini primary, Ollama local fallback.
System instructions are in English; Dutch and Spanish are used for content details.
"""
import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a Dutch language teacher for Spanish-speaking learners. "
    "Explain concepts using analogies with Spanish where helpful. "
    "Be concise and use practical examples. "
    "When giving examples in Dutch, always include the Spanish translation."
)


async def _call_ollama(messages: list[dict[str, str]], model: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


async def _call_gemini(messages: list[dict[str, str]]) -> str:
    """Call Gemini via google-genai SDK (async wrapper around the sync client)."""
    from google import genai
    from google.genai import types as gt

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model = settings.GEMINI_MODEL

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Convert OpenAI-style message list to a single prompt string.
    # System messages are prepended; user/assistant turns are joined.
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.insert(0, content)
        else:
            parts.append(content)
    prompt = "\n\n".join(parts)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=prompt,
        config=gt.GenerateContentConfig(temperature=0.7),
    )
    candidates = response.candidates
    if not candidates or not candidates[0].content or not candidates[0].content.parts:
        raise RuntimeError("Gemini returned an empty response")
    return candidates[0].content.parts[0].text or ""


async def chat_completion(
    messages: list[dict[str, str]],
    inject_system: bool = True,
    provider_override: str | None = None,
) -> str:
    if inject_system:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    provider = provider_override or settings.LLM_PROVIDER
    try:
        if provider == "ollama":
            return await _call_ollama(messages, settings.OLLAMA_MODEL)
        return await _call_gemini(messages)
    except Exception as primary_err:
        logger.warning("Primary LLM failed (%s), trying fallback: %s", provider, primary_err)
        try:
            if provider == "ollama":
                return await _call_gemini(messages)
            return await _call_ollama(messages, settings.OLLAMA_MODEL)
        except Exception as fallback_err:
            logger.error("Fallback LLM also failed: %s", fallback_err)
            raise RuntimeError("All LLM providers failed.") from fallback_err


async def explain(word_or_phrase: str, context_sentence: str | None = None) -> str:
    ctx = f' in the sentence: "{context_sentence}"' if context_sentence else ""
    prompt = f'Explain the Dutch word or phrase "{word_or_phrase}"{ctx}. Include: meaning, grammatical usage, and an additional example with its Spanish translation.'
    return await chat_completion([{"role": "user", "content": prompt}])


async def feedback(question: str, correct_answer: str, user_answer: str) -> str:
    prompt = (
        f"The student answered incorrectly.\n"
        f"Question: {question}\n"
        f"Correct answer: {correct_answer}\n"
        f"Student's answer: {user_answer}\n\n"
        "Explain in Spanish why the correct answer is right and give a memory tip."
    )
    return await chat_completion([{"role": "user", "content": prompt}])


async def generate_exercise(theme: str, level: str, exercise_type: str, word: str | None = None) -> str:
    word_hint = f" using the word '{word}'" if word else ""
    prompt = (
        f"Create a '{exercise_type}' exercise in Dutch for level {level.upper()}, "
        f"theme '{theme}'{word_hint}. "
        "Return JSON with fields: sentence_nl, sentence_es, blank_word (if applicable), options (list of 4 for multiple choice), correct_index."
    )
    return await chat_completion([{"role": "user", "content": prompt}])
