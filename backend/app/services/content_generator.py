"""
Content generator service — uses LLMs to create Dutch learning content.

Generates vocabulary items, grammar topics, stories, and game exercises
based on CEFR language level (A0–C1) and theme.  All prompts ask the
LLM to return strict JSON so that results can be persisted directly.
"""
import json
import logging
from typing import Any

from app.services import llm_service
from app.services.llm_service import _sanitize_for_json_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Level / theme metadata
# ---------------------------------------------------------------------------

LEVEL_DESCRIPTIONS: dict[str, str] = {
    "a0": "absolute beginner (no prior knowledge of Dutch)",
    "a1": "beginner (can understand and use basic everyday expressions)",
    "a2": "elementary (can understand commonly used phrases in everyday situations)",
    "b1": "intermediate (can understand the main points in everyday situations)",
    "b2": "upper-intermediate (can understand complex texts on concrete and abstract topics)",
    "c1": "advanced (can understand long and demanding texts)",
}

THEMES_BY_LEVEL: dict[str, list[str]] = {
    "a0": ["animales", "familia", "colores", "numeros", "comida", "cuerpo"],
    "a1": ["ciudad", "transporte", "trabajo", "tiempo", "ropa", "salud", "educacion"],
    "a2": ["viajes", "naturaleza", "cultura", "medios", "compras", "ocio"],
    "b1": ["politica", "tecnologia", "medio_ambiente", "economia", "literatura"],
    "b2": ["filosofia", "ciencias", "arte", "historia", "sociedad"],
    "c1": ["derecho", "medicina", "ingenieria", "finanzas", "diplomacia"],
}

# Word counts per level for generated stories
_STORY_WORD_COUNTS: dict[str, str] = {
    "a0": "60-80",
    "a1": "100-130",
    "a2": "150-200",
    "b1": "200-300",
    "b2": "300-400",
    "c1": "400-600",
}

# ---------------------------------------------------------------------------
# Public generators
# ---------------------------------------------------------------------------


async def generate_vocabulary(
    level: str,
    theme: str,
    count: int = 10,
) -> list[dict[str, Any]]:
    """Generate vocabulary items using LLM for a given CEFR level and theme.

    Returns a list of dicts compatible with the VocabularyItem DB model.
    """
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    prompt = (
        f"Generate {count} Dutch words for level {level.upper()} ({level_desc}), "
        f"theme '{theme}'.\n"
        "Return ONLY a valid JSON array with this exact schema (no additional text):\n"
        "[\n"
        "  {\n"
        '    "dutch_word": "hond",\n'
        '    "english": "dog",\n'
        '    "spanish": "perro",\n'
        '    "article": "de",\n'
        '    "plural": "honden",\n'
        '    "word_type": "noun",\n'
        f'    "level": "{level.lower()}",\n'
        f'    "theme": "{theme}",\n'
        '    "example_nl": "De hond loopt in het park.",\n'
        '    "example_es": "El perro camina en el parque."\n'
        "  }\n"
        "]\n"
        f'All items must have level="{level.lower()}" and theme="{theme}". '
        "The 'article' field is 'de', 'het', or null for verbs/adverbs. "
        "Examples must be simple sentences appropriate for the level."
    )
    raw = await llm_service.chat_completion(
        [{"role": "user", "content": prompt}],
        inject_system=False,
    )
    return _parse_json_list(raw)


async def generate_grammar_topic(
    level: str,
    topic_name_es: str,
    topic_name_nl: str,
    slug: str,
) -> dict[str, Any]:
    """Generate a grammar topic with description and examples using LLM.

    Returns a dict compatible with the GrammarTopic DB model.
    """
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    safe_topic_es = _sanitize_for_json_prompt(topic_name_es)
    safe_topic_nl = _sanitize_for_json_prompt(topic_name_nl)
    safe_slug = _sanitize_for_json_prompt(slug)
    prompt = (
        f"Create a Dutch grammar topic for Spanish-speaking learners at level {level.upper()} ({level_desc}).\n"
        f"Topic: '{safe_topic_es}' (in Dutch: '{safe_topic_nl}')\n\n"
        "Return ONLY a valid JSON object with this exact schema (no additional text):\n"
        "{\n"
        f'  "slug": "{safe_slug}",\n'
        f'  "name_nl": "{safe_topic_nl}",\n'
        f'  "name_es": "{safe_topic_es}",\n'
        f'  "level": "{level.lower()}",\n'
        '  "description_es": "Detailed explanation in Spanish, 3-5 sentences...",\n'
        '  "examples_json": [\n'
        '    {"nl": "example in Dutch", "es": "note or translation in Spanish"}\n'
        '  ]\n'
        "}\n"
        "Include 4-6 concrete and useful examples."
    )
    raw = await llm_service.chat_completion(
        [{"role": "user", "content": prompt}],
        inject_system=False,
    )
    return _parse_json_object(raw)


async def generate_story(
    level: str,
    theme: str,
    title_nl: str | None = None,
    title_es: str | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Generate a reading story with comprehension questions using LLM.

    Returns a dict compatible with the Story DB model.
    """
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    safe_title_nl = _sanitize_for_json_prompt(title_nl) if title_nl else None
    safe_title_es = _sanitize_for_json_prompt(title_es) if title_es else None
    title_hint = f"Título sugerido: '{safe_title_nl}' / '{safe_title_es}'." if safe_title_nl else ""
    word_count = _STORY_WORD_COUNTS.get(level.lower(), "100-150")

    prompt = (
        f"Create a short story in Dutch for learners at level {level.upper()} ({level_desc}), "
        f"theme '{theme}'. {title_hint}\n"
        f"The story must be {word_count} words in Dutch, using vocabulary appropriate for the level.\n\n"
        "Return ONLY a valid JSON object with this schema (no additional text):\n"
        "{\n"
        '  "slug": "...",\n'
        '  "title_nl": "...",\n'
        '  "title_es": "...",\n'
        f'  "level": "{level.lower()}",\n'
        f'  "theme": "{theme}",\n'
        '  "content_nl": "Full story in Dutch...",\n'
        '  "content_es": "Full Spanish translation...",\n'
        '  "questions_json": [\n'
        '    {\n'
        '      "question_es": "Comprehension question in Spanish?",\n'
        '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '      "answer_index": 0,\n'
        '      "explanation_es": "Explanation of the correct answer in Spanish."\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Include 3 comprehension questions. Use the 'slug' field based on the Dutch title "
        "(lowercase, hyphens instead of spaces)."
    )
    raw = await llm_service.chat_completion(
        [{"role": "user", "content": prompt}],
        inject_system=False,
    )
    result = _parse_json_object(raw)
    if slug and result:
        result["slug"] = slug
    return result


async def generate_lesson(
    level: str,
    theme: str,
    vocab_count: int = 5,
) -> dict[str, Any]:
    """Generate a complete lesson: vocabulary + grammar tip + story.

    Calls the individual generators and assembles the result.
    """
    vocab = await generate_vocabulary(level, theme, vocab_count)
    story = await generate_story(level, theme)

    grammar_tip_prompt = (
        f"Give a brief grammar tip (2-3 sentences) in Spanish for a Dutch learner "
        f"at level {level.upper()}, relevant to the theme '{theme}'. "
        "Include a short Dutch example sentence with its Spanish translation."
    )
    grammar_tip = await llm_service.chat_completion(
        [{"role": "user", "content": grammar_tip_prompt}],
        inject_system=False,
    )

    return {
        "level": level.lower(),
        "theme": theme.lower(),
        "vocabulary": vocab,
        "grammar_tip": grammar_tip,
        "story": story,
    }


async def generate_game_exercise(
    level: str,
    theme: str,
    game_type: str,
    vocabulary: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a specific game exercise using LLM.

    game_type: fill_blank | multiple_choice | unscramble | word_match
    Returns a plain dict whose shape matches the relevant exercises API response.
    """
    safe_vocab = [_sanitize_for_json_prompt(w) for w in vocabulary] if vocabulary else []
    vocab_hint = f" using some of these words: {', '.join(safe_vocab)}" if safe_vocab else ""

    if game_type == "fill_blank":
        prompt = (
            f"Create a fill-in-the-blank exercise in Dutch for level {level.upper()}"
            f", theme '{theme}'{vocab_hint}.\n"
            "Return ONLY JSON (no additional text):\n"
            "{\n"
            '  "sentence_with_blank": "De ___ loopt in het park.",\n'
            '  "sentence_es": "El ___ camina en el parque.",\n'
            '  "correct_word": "hond",\n'
            '  "options": ["hond", "kat", "vis", "vogel"],\n'
            '  "correct_index": 0,\n'
            '  "explanation_es": "Short explanation in Spanish."\n'
            "}"
        )
    elif game_type == "multiple_choice":
        prompt = (
            f"Create a multiple-choice question in Dutch for level {level.upper()}"
            f", theme '{theme}'{vocab_hint}.\n"
            "Return ONLY JSON (no additional text):\n"
            "{\n"
            '  "question_nl": "Question in Dutch",\n'
            '  "question_es": "Question in Spanish",\n'
            '  "options": ["Option A", "Option B", "Option C", "Option D"],\n'
            '  "correct_index": 0,\n'
            '  "explanation_es": "Explanation of the correct answer in Spanish."\n'
            "}"
        )
    elif game_type == "unscramble":
        prompt = (
            f"Create a word-order exercise in Dutch for level {level.upper()}"
            f", theme '{theme}'{vocab_hint}.\n"
            "Return ONLY JSON (no additional text):\n"
            "{\n"
            '  "correct_sentence": "De hond loopt in het park.",\n'
            '  "sentence_es": "El perro camina en el parque.",\n'
            '  "shuffled_words": ["in", "park.", "het", "hond", "De", "loopt"],\n'
            '  "explanation_es": "Optional grammar hint in Spanish."\n'
            "}"
        )
    elif game_type == "word_match":
        prompt = (
            f"Create 5 Dutch–Spanish word pairs for a matching game, "
            f"level {level.upper()}, theme '{theme}'{vocab_hint}.\n"
            "Return ONLY JSON (no additional text):\n"
            "{\n"
            '  "pairs": [\n'
            '    {"dutch": "hond", "spanish": "perro"}\n'
            '  ]\n'
            "}"
        )
    else:
        prompt = (
            f"Create a Dutch exercise of type '{game_type}' for level {level.upper()}, "
            f"theme '{theme}'{vocab_hint}.\n"
            "Return ONLY JSON (no additional text) with the relevant fields for this exercise type."
        )

    raw = await llm_service.chat_completion(
        [{"role": "user", "content": prompt}],
        inject_system=False,
    )
    return _parse_json_object(raw)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json … ``` fences that LLMs often add around JSON output."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[: text.rfind("```")]
    return text.strip()


def _parse_json_list(raw: str) -> list[dict[str, Any]]:
    """Extract a JSON array from raw LLM output."""
    text = _strip_markdown_fences(raw)
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        # Handle {"items": [...]} wrapper
        for v in result.values():
            if isinstance(v, list):
                return v
    except (json.JSONDecodeError, AttributeError):
        pass
    # Last resort: find the outermost array
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    logger.warning("Could not parse JSON list from LLM output: %.200s", raw)
    return []


def _parse_json_object(raw: str) -> dict[str, Any]:
    """Extract a JSON object from raw LLM output."""
    text = _strip_markdown_fences(raw)
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, AttributeError):
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    logger.warning("Could not parse JSON object from LLM output: %.200s", raw)
    return {}
