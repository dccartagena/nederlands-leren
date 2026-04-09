"""
LLM service — Ollama local primary, remote API fallback.
All prompts are in Spanish (app language for explanations).
"""
import logging
from typing import List, Dict, Any, Optional

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Eres un profesor de neerlandés para hispanohablantes. "
    "Explicas conceptos usando analogías con el español. "
    "Sé conciso y usa ejemplos prácticos. "
    "Cuando des ejemplos en neerlandés, incluye también la traducción al español."
)


async def _call_ollama(messages: List[Dict[str, str]], model: str) -> str:
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


def _remote_model_for(provider: str) -> str:
    if provider == "gemini":
        return settings.GEMINI_MODEL
    return settings.REMOTE_MODEL


async def _call_litellm(messages: List[Dict[str, str]], provider_override: Optional[str] = None) -> str:
    import litellm  # lazy import so missing key doesn't crash at startup

    provider = provider_override or settings.LLM_PROVIDER
    model = _remote_model_for(provider)

    # Set appropriate API key
    kwargs: Dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.7}
    if provider == "openai" and settings.OPENAI_API_KEY:
        kwargs["api_key"] = settings.OPENAI_API_KEY
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        kwargs["api_key"] = settings.ANTHROPIC_API_KEY
    elif provider == "mistral" and settings.MISTRAL_API_KEY:
        kwargs["api_key"] = settings.MISTRAL_API_KEY
    elif provider == "gemini" and settings.GEMINI_API_KEY:
        kwargs["api_key"] = settings.GEMINI_API_KEY

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content


async def chat_completion(
    messages: List[Dict[str, str]],
    inject_system: bool = True,
    provider_override: Optional[str] = None,
) -> str:
    if inject_system:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    provider = provider_override or settings.LLM_PROVIDER
    try:
        if provider == "ollama":
            return await _call_ollama(messages, settings.OLLAMA_MODEL)
        else:
            return await _call_litellm(messages, provider_override=provider)
    except Exception as primary_err:
        logger.warning("Primary LLM failed (%s), trying fallback: %s", provider, primary_err)
        # If Ollama fails, try remote; if remote fails, try Ollama
        try:
            if provider == "ollama":
                return await _call_litellm(messages)
            else:
                return await _call_ollama(messages, settings.OLLAMA_MODEL)
        except Exception as fallback_err:
            logger.error("Fallback LLM also failed: %s", fallback_err)
            raise RuntimeError("Todos los proveedores de LLM fallaron.") from fallback_err


async def explain(word_or_phrase: str, context_sentence: Optional[str] = None) -> str:
    ctx = f' en la oración: "{context_sentence}"' if context_sentence else ""
    prompt = f'Explica la palabra o frase neerlandesa "{word_or_phrase}"{ctx}. Incluye: significado, uso gramatical, y un ejemplo adicional.'
    return await chat_completion([{"role": "user", "content": prompt}])


async def feedback(question: str, correct_answer: str, user_answer: str) -> str:
    prompt = (
        f"El estudiante respondió incorrectamente.\n"
        f"Pregunta: {question}\n"
        f"Respuesta correcta: {correct_answer}\n"
        f"Respuesta del estudiante: {user_answer}\n\n"
        "Explica por qué la respuesta correcta es correcta y da un truco para recordarla."
    )
    return await chat_completion([{"role": "user", "content": prompt}])


async def generate_exercise(theme: str, level: str, exercise_type: str, word: Optional[str] = None) -> str:
    word_hint = f" usando la palabra '{word}'" if word else ""
    prompt = (
        f"Crea un ejercicio de tipo '{exercise_type}' en neerlandés para nivel {level.upper()}, "
        f"tema '{theme}'{word_hint}. "
        "Devuelve JSON con campos: sentence_nl, sentence_es, blank_word (si aplica), options (lista de 4 si es multiple choice), correct_index."
    )
    return await chat_completion([{"role": "user", "content": prompt}])
