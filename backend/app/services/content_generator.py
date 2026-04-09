"""
Content generator service — uses LLMs to create Dutch learning content.

Generates vocabulary items, grammar topics, stories, and game exercises
based on CEFR language level (A0–C1) and theme.  All prompts ask the
LLM to return strict JSON so that results can be persisted directly.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from app.services import llm_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Level / theme metadata
# ---------------------------------------------------------------------------

LEVEL_DESCRIPTIONS: Dict[str, str] = {
    "a0": "principiante absoluto (sin conocimiento previo de neerlandés)",
    "a1": "principiante (puede entender y usar expresiones básicas cotidianas)",
    "a2": "elemental (puede entender frases de uso habitual en situaciones cotidianas)",
    "b1": "intermedio (puede entender los puntos principales en situaciones cotidianas)",
    "b2": "intermedio-alto (puede entender textos complejos sobre temas concretos y abstractos)",
    "c1": "avanzado (puede entender textos largos y exigentes)",
}

THEMES_BY_LEVEL: Dict[str, List[str]] = {
    "a0": ["animales", "familia", "colores", "numeros", "comida", "cuerpo"],
    "a1": ["ciudad", "transporte", "trabajo", "tiempo", "ropa", "salud", "educacion"],
    "a2": ["viajes", "naturaleza", "cultura", "medios", "compras", "ocio"],
    "b1": ["politica", "tecnologia", "medio_ambiente", "economia", "literatura"],
    "b2": ["filosofia", "ciencias", "arte", "historia", "sociedad"],
    "c1": ["derecho", "medicina", "ingenieria", "finanzas", "diplomacia"],
}

# Word counts per level for generated stories
_STORY_WORD_COUNTS: Dict[str, str] = {
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
) -> List[Dict[str, Any]]:
    """Generate vocabulary items using LLM for a given CEFR level and theme.

    Returns a list of dicts compatible with the VocabularyItem DB model.
    """
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    prompt = (
        f"Genera {count} palabras en neerlandés para nivel {level.upper()} ({level_desc}), "
        f"tema '{theme}'.\n"
        "Devuelve ÚNICAMENTE un array JSON válido con este esquema exacto (sin texto adicional):\n"
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
        f'Todos los items deben tener level="{level.lower()}" y theme="{theme}". '
        "El campo 'article' es 'de', 'het' o null para verbos/adverbios. "
        "Los ejemplos deben ser frases simples apropiadas para el nivel."
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
) -> Dict[str, Any]:
    """Generate a grammar topic with description and examples using LLM.

    Returns a dict compatible with the GrammarTopic DB model.
    """
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    prompt = (
        f"Crea un tema de gramática neerlandesa para hispanohablantes de nivel {level.upper()} ({level_desc}).\n"
        f"Tema: '{topic_name_es}' (en neerlandés: '{topic_name_nl}')\n\n"
        "Devuelve ÚNICAMENTE un objeto JSON válido con este esquema exacto (sin texto adicional):\n"
        "{\n"
        f'  "slug": "{slug}",\n'
        f'  "name_nl": "{topic_name_nl}",\n'
        f'  "name_es": "{topic_name_es}",\n'
        f'  "level": "{level.lower()}",\n'
        '  "description_es": "Explicación detallada en español de 3-5 oraciones...",\n'
        '  "examples_json": [\n'
        '    {"nl": "ejemplo en neerlandés", "es": "nota o traducción en español"}\n'
        '  ]\n'
        "}\n"
        "Incluye 4-6 ejemplos concretos y útiles."
    )
    raw = await llm_service.chat_completion(
        [{"role": "user", "content": prompt}],
        inject_system=False,
    )
    return _parse_json_object(raw)


async def generate_story(
    level: str,
    theme: str,
    title_nl: Optional[str] = None,
    title_es: Optional[str] = None,
    slug: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a reading story with comprehension questions using LLM.

    Returns a dict compatible with the Story DB model.
    """
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    title_hint = f"Título sugerido: '{title_nl}' / '{title_es}'." if title_nl else ""
    word_count = _STORY_WORD_COUNTS.get(level.lower(), "100-150")

    prompt = (
        f"Crea una historia corta en neerlandés para aprendices de nivel {level.upper()} ({level_desc}), "
        f"tema '{theme}'. {title_hint}\n"
        f"La historia debe tener {word_count} palabras en neerlandés, usando vocabulario apropiado para el nivel.\n\n"
        "Devuelve ÚNICAMENTE un objeto JSON válido con este esquema (sin texto adicional):\n"
        "{\n"
        '  "slug": "...",\n'
        '  "title_nl": "...",\n'
        '  "title_es": "...",\n'
        f'  "level": "{level.lower()}",\n'
        f'  "theme": "{theme}",\n'
        '  "content_nl": "Historia completa en neerlandés...",\n'
        '  "content_es": "Traducción completa al español...",\n'
        '  "questions_json": [\n'
        '    {\n'
        '      "question_es": "¿Pregunta de comprensión en español?",\n'
        '      "options": ["Opción A", "Opción B", "Opción C", "Opción D"],\n'
        '      "answer_index": 0,\n'
        '      "explanation_es": "Explicación de la respuesta correcta."\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Incluye 3 preguntas de comprensión. Usa el campo 'slug' basado en el título en neerlandés "
        "(minúsculas, guiones en lugar de espacios)."
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
) -> Dict[str, Any]:
    """Generate a complete lesson: vocabulary + grammar tip + story.

    Calls the individual generators and assembles the result.
    """
    vocab = await generate_vocabulary(level, theme, vocab_count)
    story = await generate_story(level, theme)

    grammar_tip_prompt = (
        f"Da un consejo gramatical breve (2-3 oraciones) en español para un aprendiz de neerlandés "
        f"de nivel {level.upper()}, relevante para el tema '{theme}'. "
        "Incluye un ejemplo corto en neerlandés con traducción al español."
    )
    grammar_tip = await llm_service.chat_completion(
        [{"role": "user", "content": grammar_tip_prompt}],
        inject_system=False,
    )

    return {
        "level": level,
        "theme": theme,
        "vocabulary": vocab,
        "grammar_tip": grammar_tip,
        "story": story,
    }


async def generate_game_exercise(
    level: str,
    theme: str,
    game_type: str,
    vocabulary: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate a specific game exercise using LLM.

    game_type: fill_blank | multiple_choice | unscramble | word_match
    Returns a plain dict whose shape matches the relevant exercises API response.
    """
    vocab_hint = f" usando algunas de estas palabras: {', '.join(vocabulary)}" if vocabulary else ""

    if game_type == "fill_blank":
        prompt = (
            f"Crea un ejercicio de completar-el-espacio-en-blanco en neerlandés para nivel {level.upper()}"
            f", tema '{theme}'{vocab_hint}.\n"
            "Devuelve ÚNICAMENTE JSON (sin texto adicional):\n"
            "{\n"
            '  "sentence_with_blank": "De ___ loopt in het park.",\n'
            '  "sentence_es": "El ___ camina en el parque.",\n'
            '  "correct_word": "hond",\n'
            '  "options": ["hond", "kat", "vis", "vogel"],\n'
            '  "correct_index": 0,\n'
            '  "explanation_es": "Explicación corta en español."\n'
            "}"
        )
    elif game_type == "multiple_choice":
        prompt = (
            f"Crea una pregunta de opción múltiple en neerlandés para nivel {level.upper()}"
            f", tema '{theme}'{vocab_hint}.\n"
            "Devuelve ÚNICAMENTE JSON (sin texto adicional):\n"
            "{\n"
            '  "question_nl": "Pregunta en neerlandés",\n'
            '  "question_es": "Pregunta en español",\n'
            '  "options": ["Opción A", "Opción B", "Opción C", "Opción D"],\n'
            '  "correct_index": 0,\n'
            '  "explanation_es": "Explicación de la respuesta correcta."\n'
            "}"
        )
    elif game_type == "unscramble":
        prompt = (
            f"Crea un ejercicio de ordenar-palabras en neerlandés para nivel {level.upper()}"
            f", tema '{theme}'{vocab_hint}.\n"
            "Devuelve ÚNICAMENTE JSON (sin texto adicional):\n"
            "{\n"
            '  "correct_sentence": "De hond loopt in het park.",\n'
            '  "sentence_es": "El perro camina en el parque.",\n'
            '  "shuffled_words": ["in", "park.", "het", "hond", "De", "loopt"],\n'
            '  "explanation_es": "Pista gramatical opcional."\n'
            "}"
        )
    elif game_type == "word_match":
        prompt = (
            f"Crea 5 pares de palabras neerlandés–español para un juego de emparejamiento, "
            f"nivel {level.upper()}, tema '{theme}'{vocab_hint}.\n"
            "Devuelve ÚNICAMENTE JSON (sin texto adicional):\n"
            "{\n"
            '  "pairs": [\n'
            '    {"dutch": "hond", "spanish": "perro"}\n'
            '  ]\n'
            "}"
        )
    else:
        prompt = (
            f"Crea un ejercicio de neerlandés de tipo '{game_type}' para nivel {level.upper()}, "
            f"tema '{theme}'{vocab_hint}.\n"
            "Devuelve ÚNICAMENTE JSON (sin texto adicional) con los campos relevantes para este tipo de ejercicio."
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


def _parse_json_list(raw: str) -> List[Dict[str, Any]]:
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


def _parse_json_object(raw: str) -> Dict[str, Any]:
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
