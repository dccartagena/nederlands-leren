#!/usr/bin/env python3
"""
Batch content population script for Nederlands Leren.

Generates vocabulary and stories for one or more CEFR levels using the
configured LLM, validates each item for required fields, appends new content
to the JSON data files, and upserts into the database.

Prerequisites:
  Set the following in the project-root .env before running:
    LLM_PROVIDER=gemini
    GEMINI_API_KEY=<your key>
    GEMINI_MODEL=gemini/...   (or the model of your choice)

Run from the backend/ directory with the venv activated:

    # Populate A0 vocabulary (dry-run — no file writes or DB changes)
    .venv/bin/python scripts/populate_content.py \\
        --levels a0 --types vocab --dry-run

    # Populate A0 and A1 vocabulary (10 words per theme)
    .venv/bin/python scripts/populate_content.py \\
        --levels a0 a1 --types vocab --count 10

    # Populate everything for all levels (write JSON only, skip DB upsert)
    .venv/bin/python scripts/populate_content.py \\
        --levels a0 a1 a2 b1 b2 --types vocab stories --no-seed
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.db import models  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.services import content_generator  # noqa: E402
from app.services.content_generator import THEMES_BY_LEVEL  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

VALID_LEVELS = ["a0", "a1", "a2", "b1", "b2"]

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "populate_config.json"

# Gemini Batch API terminal states (same set as gemini_tts.py)
_TERMINAL_JOB_STATES = {
    "JOB_STATE_SUCCEEDED",
    "JOB_STATE_FAILED",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_PARTIALLY_SUCCEEDED",
    "JOB_STATE_EXPIRED",
}


# ---------------------------------------------------------------------------
# Gemini Batch API helpers
# ---------------------------------------------------------------------------

def _build_gemini_client():
    """Return a configured google-genai client. Fails fast if key is missing."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.error("GEMINI_API_KEY is not set — batch mode requires the Gemini provider")
        sys.exit(1)
    try:
        from google import genai
        from google.genai import types as gt
    except ImportError:
        logger.error("google-genai is not installed. Run: pip install google-genai>=1.10.0")
        sys.exit(1)
    # Strip litellm prefix (e.g. 'gemini/gemini-2.0-flash' → 'gemini-2.0-flash')
    raw_model = settings.GEMINI_MODEL
    model = raw_model.split("/", 1)[-1] if "/" in raw_model else raw_model
    return genai.Client(api_key=api_key), gt, model


def _build_vocab_prompt(level: str, theme: str, count: int) -> str:
    """Build the vocabulary generation prompt (mirrors content_generator.generate_vocabulary)."""
    from app.services.content_generator import LEVEL_DESCRIPTIONS
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    return (
        f"Act as a Dutch linguistic expert for Spanish speakers. Generate {count} vocabulary items "
        f"for level {level.upper()} ({level_desc}) on the theme '{theme}'.\n\n"
        "Pedagogical & Technical Guidelines:\n"
        "1. Selection: Prioritize high-frequency words. For Spanish speakers, include a mix of cognates and 'valse vrienden' (false friends) to sharpen acquisition.\n"
        "2. TTS Consistency: In 'example_nl', avoid all abbreviations (e.g., use 'en dergelijke' instead of 'e.d.'). Ensure sentences have clear punctuation to help the TTS model manage natural pauses and intonation.\n"
        "3. Grammar Precision: Ensure the 'article' (de/het) and 'plural' are 100% accurate, as these are critical pain points for learners.\n"
        "4. Natural Translation: 'example_es' should be a natural, idiomatic Spanish translation, not a literal word-for-word copy, to help the learner understand context.\n\n"
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


def _build_story_prompt(
    level: str,
    theme: str,
    title_nl: str | None,
    title_es: str | None,
) -> str:
    """Build the story generation prompt (mirrors content_generator.generate_story)."""
    from app.services.content_generator import LEVEL_DESCRIPTIONS, _STORY_WORD_COUNTS
    level_desc = LEVEL_DESCRIPTIONS.get(level.lower(), level)
    title_hint = f"Título sugerido: '{title_nl}' / '{title_es}'." if title_nl else ""
    word_count = _STORY_WORD_COUNTS.get(level.lower(), "100-150")
    return (
        f"Act as a Dutch language expert specializing in teaching Spanish speakers. "
        f"Create an engaging story for level {level.upper()} ({level_desc}) on the theme '{theme}'. {title_hint}\n"
        f"Target word count: {word_count} words.\n\n"
        "Instructional & Technical Constraints:\n"
        "1. For Spanish Speakers: Focus on vocabulary that helps distinguish Dutch-Spanish false cognates or emphasizes common Dutch particles (e.g., 'er', 'toch', 'even') in context.\n"
        "2. TTS Optimization: Write in natural, rhythmic Dutch. Avoid complex abbreviations (write out 'bijvoorbeeld' instead of 'bijv.'). Use standard punctuation to ensure correct prosody and pausing in speech synthesis.\n"
        "3. Gamification: Ensure the narrative has a clear beginning, middle, and end to facilitate 'streak-style' learning modules.\n"
        "4. Sentence Structure: For lower levels, use shorter sentences to prevent TTS models from sounding robotic or losing intonation.\n\n"
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


def _extract_text_from_response(response) -> str:
    """Extract plain text from a GenerateContentResponse."""
    return response.candidates[0].content.parts[0].text


def _submit_text_batch(client, gt, model: str, requests: list[dict]):
    """
    Submit text generation requests to the Gemini Batch API.

    Each item in *requests* must have:
      - ``prompt``   : the text prompt
      - ``metadata`` : dict[str, str] for correlation (all values must be strings)
    """
    inlined_requests = [
        gt.InlinedRequest(
            contents=req["prompt"],
            metadata=req["metadata"],
        )
        for req in requests
    ]
    logger.info("BATCH submitting %d request(s) …", len(inlined_requests))
    job = client.batches.create(model=model, src=inlined_requests)
    logger.info("BATCH job created: %s  state=%s", job.name, job.state.name)
    return job


def _poll_batch(client, job_name: str, poll_interval: int):
    """Poll *job_name* until terminal state, then return the final BatchJob."""
    job = client.batches.get(name=job_name)
    while job.state.name not in _TERMINAL_JOB_STATES:
        logger.info(
            "BATCH %s — state=%s (checking again in %ds …)",
            job_name, job.state.name, poll_interval,
        )
        time.sleep(poll_interval)
        job = client.batches.get(name=job_name)
    logger.info("BATCH %s finished — state=%s", job_name, job.state.name)
    return job


def _ingest_batch_results(
    job,
    dry_run: bool,
    no_seed: bool,
    db,
) -> dict[str, dict[str, dict[str, int]]]:
    """
    Parse and save all inlined_responses from a completed batch job.

    Responses are correlated by the ``type``, ``level``, and ``theme`` metadata
    fields attached at submission time. Returns a nested summary:
      summary[level]["vocab" | "stories"] = {generated, invalid, skipped, saved}
    """
    responses = (job.dest.inlined_responses or []) if job.dest else []
    if not responses:
        logger.warning(
            "BATCH no inlined_responses in completed job %s (state=%s)",
            job.name, job.state.name,
        )
        return {}

    # Group valid responses by level and content type.
    grouped: dict[str, dict[str, list[tuple[dict, str]]]] = {}
    for ir in responses:
        meta = ir.metadata or {}
        level = meta.get("level", "")
        ctype = meta.get("type", "")

        if ir.error:
            logger.warning(
                "FAIL  [%s/%s/%s] batch error: %s",
                ctype, level, meta.get("theme"), ir.error,
            )
            continue

        try:
            text = _extract_text_from_response(ir.response)
        except Exception as exc:
            logger.warning(
                "FAIL  [%s/%s/%s] extract text: %s",
                ctype, level, meta.get("theme"), exc,
            )
            continue

        grouped.setdefault(level, {"vocab": [], "story": []})
        if ctype in ("vocab", "story"):
            grouped[level][ctype].append((meta, text))

    summary: dict[str, dict[str, dict[str, int]]] = {}

    for level, types in sorted(grouped.items()):
        summary[level] = {}

        # ── vocabulary ────────────────────────────────────────────────────
        if types["vocab"]:
            json_path = settings.DATA_DIR / "vocabulary" / f"{level}_words.json"
            existing = _load_json_file(json_path)
            existing_keys = {
                (w["dutch_word"], w["level"])
                for w in existing
                if "dutch_word" in w and "level" in w
            }
            gen = inv = skip = saved = 0

            for meta, text in types["vocab"]:
                items = content_generator._parse_json_list(text)
                gen += len(items)
                valid_items: list[dict[str, Any]] = []
                for item in items:
                    missing = _validate_vocabulary(item)
                    if missing:
                        logger.warning(
                            "  [vocab] Skipping (missing: %s): %s",
                            missing, str(item)[:80],
                        )
                        inv += 1
                    else:
                        valid_items.append(item)

                new_items: list[dict[str, Any]] = []
                for item in valid_items:
                    key = (item["dutch_word"], item["level"])
                    if key in existing_keys:
                        skip += 1
                    else:
                        new_items.append(item)
                        existing_keys.add(key)

                if new_items and not dry_run:
                    existing.extend(new_items)
                    _save_json_file(json_path, existing)
                    if not no_seed:
                        saved += _upsert_vocabulary(new_items, db)

            summary[level]["vocab"] = {"generated": gen, "invalid": inv, "skipped": skip, "saved": saved}

        # ── stories ───────────────────────────────────────────────────────
        if types["story"]:
            json_path = settings.DATA_DIR / "stories" / f"{level}_stories.json"
            existing = _load_json_file(json_path)
            existing_slugs = {s["slug"] for s in existing if "slug" in s}
            gen = inv = skip = saved = 0

            for meta, text in types["story"]:
                story = content_generator._parse_json_object(text)
                if not story:
                    logger.warning(
                        "  [stories] Empty response for %s/%s",
                        level, meta.get("theme"),
                    )
                    inv += 1
                    continue

                # Slug in metadata is authoritative (assigned at submission time).
                slug = meta.get("slug", "")
                if slug:
                    story["slug"] = slug

                missing = _validate_story(story)
                if missing:
                    logger.warning(
                        "  [stories] Skipping slug=%s (missing: %s)", slug, missing,
                    )
                    inv += 1
                    continue

                gen += 1
                if story["slug"] in existing_slugs:
                    skip += 1
                    continue

                if not dry_run:
                    existing.append(story)
                    _save_json_file(json_path, existing)
                    existing_slugs.add(story["slug"])
                    if not no_seed:
                        if _upsert_story(story, db):
                            saved += 1

            summary[level]["stories"] = {"generated": gen, "invalid": inv, "skipped": skip, "saved": saved}

    return summary


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config(path: Path) -> dict[str, Any]:
    """Load populate_config.json, returning an empty dict if the file is absent."""
    if not path.exists():
        logger.warning("Config file not found: %s — using built-in defaults", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_story_titles(path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """Load data/story_titles.json and convert to a (level, theme) keyed lookup."""
    if not path.exists():
        logger.warning("Story titles file not found: %s — generic titles will be used", path)
        return {}
    with open(path, encoding="utf-8") as f:
        raw: dict[str, dict[str, dict[str, str]]] = json.load(f)
    result: dict[tuple[str, str], tuple[str, str]] = {}
    for level, themes in raw.items():
        for theme, titles in themes.items():
            result[(level, theme)] = (titles["title_nl"], titles["title_es"])
    return result


def _load_grammar_topics(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load grammar_topics.json, returning a dict keyed by level."""
    if not path.exists():
        logger.warning("Grammar topics file not found: %s — grammar generation skipped", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Required-field validators
# ---------------------------------------------------------------------------

_VOCAB_REQUIRED = {"dutch_word", "english", "spanish", "word_type", "level", "theme", "example_nl", "example_es"}
_STORY_REQUIRED = {"slug", "title_nl", "title_es", "level", "theme", "content_nl", "content_es", "questions_json"}


def _validate_vocabulary(item: dict[str, Any]) -> list[str]:
    """Return a list of missing required fields for a vocabulary item."""
    return [f for f in _VOCAB_REQUIRED if not item.get(f)]


def item_has(obj: dict[str, Any], field: str) -> bool:
    """True when the field exists and is not None / empty string / empty list."""
    val = obj.get(field)
    if val is None:
        return False
    if isinstance(val, (str, list)) and not val:
        return False
    return True


def _validate_story(story: dict[str, Any]) -> list[str]:
    """Return a list of missing required fields for a story."""
    return [f for f in _STORY_REQUIRED if not item_has(story, f)]


_GRAMMAR_REQUIRED = {"slug", "name_nl", "name_es", "level", "description_es", "examples_json"}


def _validate_grammar_topic(topic: dict[str, Any]) -> list[str]:
    """Return a list of missing required fields for a grammar topic."""
    return [f for f in _GRAMMAR_REQUIRED if not item_has(topic, f)]


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def _load_json_file(path: Path) -> list[dict[str, Any]]:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    return []


def _save_json_file(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def _dedupe_json(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Return a deduplicated list keyed on (dutch_word, level), keeping first occurrence."""
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    removed = 0
    for item in items:
        key = (item.get("dutch_word", ""), item.get("level", ""))
        if key in seen:
            removed += 1
        else:
            seen.add(key)
            result.append(item)
    return result, removed


def _dedupe_db_vocabulary(db) -> int:
    """Delete duplicate VocabularyItem rows, keeping the one with the lowest id."""
    from sqlalchemy import text
    # Find ids to keep: lowest id per (dutch_word, level) pair.
    rows = db.execute(
        text(
            "SELECT MIN(id) AS keep_id "
            "FROM vocabulary_items "
            "GROUP BY dutch_word, level "
            "HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if not rows:
        return 0
    keep_ids = [r[0] for r in rows]
    # Delete all rows that share a (dutch_word, level) with a duplicate but are NOT the keeper.
    deleted = 0
    for keep_id in keep_ids:
        item = db.query(models.VocabularyItem).filter_by(id=keep_id).first()
        if item is None:
            continue
        dupes = (
            db.query(models.VocabularyItem)
            .filter(
                models.VocabularyItem.dutch_word == item.dutch_word,
                models.VocabularyItem.level == item.level,
                models.VocabularyItem.id != keep_id,
            )
            .all()
        )
        for dupe in dupes:
            db.delete(dupe)
            deleted += 1
    db.commit()
    return deleted


# ---------------------------------------------------------------------------
# DB upsert helpers
# ---------------------------------------------------------------------------

def _upsert_vocabulary(items: list[dict[str, Any]], db) -> int:
    saved = 0
    for w in items:
        exists = db.query(models.VocabularyItem).filter_by(
            dutch_word=w.get("dutch_word"), level=w.get("level")
        ).first()
        if not exists:
            db.add(models.VocabularyItem(**{
                k: v for k, v in w.items() if hasattr(models.VocabularyItem, k)
            }))
            saved += 1
    db.commit()
    return saved


def _upsert_story(story: dict[str, Any], db) -> bool:
    exists = db.query(models.Story).filter_by(slug=story.get("slug")).first()
    if exists:
        return False
    db.add(models.Story(**{
        k: v for k, v in story.items() if hasattr(models.Story, k)
    }))
    db.commit()
    return True


def _upsert_grammar_topic(topic: dict[str, Any], db) -> bool:
    exists = db.query(models.GrammarTopic).filter_by(slug=topic.get("slug")).first()
    if exists:
        return False
    db.add(models.GrammarTopic(**{
        k: v for k, v in topic.items() if hasattr(models.GrammarTopic, k)
    }))
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Async populate functions
# ---------------------------------------------------------------------------

async def populate_vocabulary(
    level: str,
    count: int,
    dry_run: bool,
    no_seed: bool,
    db,
    api_delay: float = 1.0,
    themes: list[str] | None = None,
) -> dict[str, int]:
    if themes is None:
        themes = THEMES_BY_LEVEL.get(level, [])
    json_path = settings.DATA_DIR / "vocabulary" / f"{level}_words.json"
    existing = _load_json_file(json_path)
    existing_keys = {(w["dutch_word"], w["level"]) for w in existing if "dutch_word" in w and "level" in w}

    generated = invalid = skipped = saved = 0

    for theme in themes:
        logger.info("  [vocab] level=%s theme=%s — generating %d words …", level, theme, count)
        try:
            items = await content_generator.generate_vocabulary(level, theme, count)
        except Exception as exc:
            logger.error("  [vocab] level=%s theme=%s — generation failed: %s", level, theme, exc)
            await asyncio.sleep(1.0)
            continue

        generated += len(items)

        valid_items: list[dict[str, Any]] = []
        for item in items:
            missing = _validate_vocabulary(item)
            if missing:
                logger.warning(
                    "  [vocab] Skipping item (missing fields: %s): %s",
                    missing,
                    str(item)[:120],
                )
                invalid += 1
            else:
                valid_items.append(item)

        new_items: list[dict[str, Any]] = []
        for item in valid_items:
            key = (item["dutch_word"], item["level"])
            if key in existing_keys:
                skipped += 1
            else:
                new_items.append(item)
                existing_keys.add(key)

        if new_items and not dry_run:
            existing.extend(new_items)
            _save_json_file(json_path, existing)
            if not no_seed:
                saved += _upsert_vocabulary(new_items, db)

        await asyncio.sleep(api_delay)

    return {"generated": generated, "invalid": invalid, "skipped": skipped, "saved": saved}


async def populate_stories(
    level: str,
    dry_run: bool,
    no_seed: bool,
    db,
    api_delay: float = 1.0,
    story_titles: dict[tuple[str, str], tuple[str, str]] | None = None,
    story_count: int = 1,
) -> dict[str, int]:
    titles_map = story_titles or {}
    themes = [theme for (lvl, theme) in titles_map if lvl == level] or THEMES_BY_LEVEL.get(level, [])
    json_path = settings.DATA_DIR / "stories" / f"{level}_stories.json"
    existing = _load_json_file(json_path)
    existing_slugs = {s["slug"] for s in existing if "slug" in s}

    generated = invalid = skipped = saved = 0

    # Count existing stories per theme to produce unique slugs on repeated runs.
    theme_counts: dict[str, int] = {}
    for s in existing:
        t = s.get("theme", "")
        theme_counts[t] = theme_counts.get(t, 0) + 1

    titles_lookup = titles_map
    for theme in themes:
        for _story_n in range(story_count):
            # First story keeps the plain slug; subsequent ones get a numeric suffix.
            base_slug = f"{level}-{theme}"
            count = theme_counts.get(theme, 0)
            slug = base_slug if count == 0 else f"{base_slug}-{count + 1}"
            # Use the title hint only for the first story to encourage variety.
            if count == 0:
                title_nl, title_es = titles_lookup.get(
                    (level, theme),
                    (f"Verhaal: {theme}", f"Historia: {theme}"),
                )
            else:
                title_nl, title_es = None, None
            logger.info("  [stories] level=%s theme=%s (slug=%s) — generating …", level, theme, slug)
            try:
                story = await content_generator.generate_story(level, theme, title_nl, title_es, slug)
            except Exception as exc:
                logger.error("  [stories] level=%s theme=%s — generation failed: %s", level, theme, exc)
                await asyncio.sleep(1.0)
                continue

            generated += 1

            missing = _validate_story(story)
            if missing:
                logger.warning(
                    "  [stories] Skipping story slug=%s (missing fields: %s)",
                    slug,
                    missing,
                )
                invalid += 1
                await asyncio.sleep(1.0)
                continue

            if story["slug"] in existing_slugs:
                skipped += 1
                await asyncio.sleep(1.0)
                continue

            if not dry_run:
                existing.append(story)
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
                _save_json_file(json_path, existing)
                existing_slugs.add(story["slug"])
                if not no_seed:
                    if _upsert_story(story, db):
                        saved += 1

            await asyncio.sleep(api_delay)

    return {"generated": generated, "invalid": invalid, "skipped": skipped, "saved": saved}


# ---------------------------------------------------------------------------
# Batch populate functions (Gemini Batch API)
# ---------------------------------------------------------------------------

async def populate_vocabulary_batch(
    level: str,
    count: int,
    dry_run: bool,
    no_seed: bool,
    db,
    poll_interval: int = 60,
    themes: list[str] | None = None,
) -> dict[str, int]:
    """
    Batch-mode vocabulary generation: submit one Gemini Batch API job covering
    all themes for this level, poll until done, then ingest results.

    Returns the same {generated, invalid, skipped, saved} summary as
    populate_vocabulary.
    """
    if themes is None:
        themes = THEMES_BY_LEVEL.get(level, [])

    requests: list[dict] = [
        {
            "prompt": _build_vocab_prompt(level, theme, count),
            "metadata": {"type": "vocab", "level": level, "theme": theme},
        }
        for theme in themes
    ]

    if dry_run:
        for r in requests:
            logger.info(
                "DRY   [vocab] level=%s theme=%s — would submit to batch",
                level, r["metadata"]["theme"],
            )
        logger.info("DRY   Would submit %d vocab request(s) as a batch job", len(requests))
        return {"generated": len(requests) * count, "invalid": 0, "skipped": 0, "saved": 0}

    if not requests:
        logger.info("[vocab] No themes to process for level=%s", level)
        return {"generated": 0, "invalid": 0, "skipped": 0, "saved": 0}

    client, gt, model = _build_gemini_client()
    job = _submit_text_batch(client, gt, model, requests)
    job = _poll_batch(client, job.name, poll_interval)
    results = _ingest_batch_results(job, dry_run, no_seed, db)
    return results.get(level, {}).get("vocab", {"generated": 0, "invalid": 0, "skipped": 0, "saved": 0})


async def populate_stories_batch(
    level: str,
    dry_run: bool,
    no_seed: bool,
    db,
    poll_interval: int = 60,
    story_titles: dict[tuple[str, str], tuple[str, str]] | None = None,
    story_count: int = 1,
) -> dict[str, int]:
    """
    Batch-mode story generation: submit one Gemini Batch API job covering all
    themes for this level, poll until done, then ingest results.

    Returns the same {generated, invalid, skipped, saved} summary as
    populate_stories.
    """
    titles_map = story_titles or {}
    themes = [theme for (lvl, theme) in titles_map if lvl == level] or THEMES_BY_LEVEL.get(level, [])
    json_path = settings.DATA_DIR / "stories" / f"{level}_stories.json"
    existing = _load_json_file(json_path)
    existing_slugs = {s["slug"] for s in existing if "slug" in s}

    # Mirror the slug/title logic from populate_stories so metadata is accurate.
    theme_counts: dict[str, int] = {}
    for s in existing:
        t = s.get("theme", "")
        theme_counts[t] = theme_counts.get(t, 0) + 1

    requests: list[dict] = []
    for theme in themes:
        for _ in range(story_count):
            base_slug = f"{level}-{theme}"
            count = theme_counts.get(theme, 0)
            slug = base_slug if count == 0 else f"{base_slug}-{count + 1}"

            if slug in existing_slugs:
                logger.info("SKIP  [stories] level=%s slug=%s (already exists)", level, slug)
                continue

            if count == 0:
                title_nl, title_es = titles_map.get(
                    (level, theme),
                    (f"Verhaal: {theme}", f"Historia: {theme}"),
                )
            else:
                title_nl, title_es = None, None

            requests.append({
                "prompt": _build_story_prompt(level, theme, title_nl, title_es),
                "metadata": {
                    "type": "story",
                    "level": level,
                    "theme": theme,
                    "slug": slug,
                    "title_nl": title_nl or "",
                    "title_es": title_es or "",
                },
            })
            # Reserve slug so repeated story_count iterations get unique slugs.
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
            existing_slugs.add(slug)

    if dry_run:
        for r in requests:
            logger.info(
                "DRY   [stories] level=%s slug=%s — would submit to batch",
                level, r["metadata"]["slug"],
            )
        logger.info("DRY   Would submit %d story request(s) as a batch job", len(requests))
        return {"generated": len(requests), "invalid": 0, "skipped": 0, "saved": 0}

    if not requests:
        logger.info("[stories] No new stories to generate for level=%s", level)
        return {"generated": 0, "invalid": 0, "skipped": 0, "saved": 0}

    client, gt, model = _build_gemini_client()
    job = _submit_text_batch(client, gt, model, requests)
    job = _poll_batch(client, job.name, poll_interval)
    results = _ingest_batch_results(job, dry_run, no_seed, db)
    return results.get(level, {}).get("stories", {"generated": 0, "invalid": 0, "skipped": 0, "saved": 0})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    # Two-pass: extract --config first so its values can seed argparse defaults.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=_DEFAULT_CONFIG_PATH)
    pre_args, _ = pre.parse_known_args()
    cfg = _load_config(pre_args.config)

    parser = argparse.ArgumentParser(
        description="Populate Dutch learning content using LLM and seed the database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  .venv/bin/python scripts/populate_content.py --levels a0 --types vocab\n"
            "  .venv/bin/python scripts/populate_content.py --levels a0 a1 --types vocab --vocab-count 10\n"
            "  .venv/bin/python scripts/populate_content.py --levels a0 a1 --types vocab --dry-run\n"
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG_PATH,
        metavar="PATH",
        help=f"Path to populate_config.json (default: {_DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--levels",
        required=True,
        nargs="+",
        choices=VALID_LEVELS,
        metavar="LEVEL",
        help=f"One or more CEFR levels to process: {VALID_LEVELS}",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["vocab", "stories", "grammar"],
        metavar="TYPE",
        help="Content types to generate: vocab, stories, grammar (required unless --dedupe is set)",
    )
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help=(
            "Remove duplicate vocabulary from JSON files (and DB unless --no-seed). "
            "Skips content generation. Use --dry-run to preview without writing."
        ),
    )
    parser.add_argument(
        "--count",
        type=int,
        metavar="N",
        help="Number of items to generate per theme (words for vocab, stories for stories)",
    )
    parser.add_argument(
        "--grammar-topics",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to grammar_topics.json (default: DATA_DIR/grammar_topics.json)",
    )
    parser.add_argument(
        "--api-delay",
        type=float,
        metavar="SECONDS",
        help="Seconds to wait between API calls",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and validate content but do not write files or update the database",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Write JSON files but skip database upsert",
    )
    parser.add_argument(
        "--story-titles",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to story_titles.json (default: DATA_DIR/story_titles.json)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Submit all requests for each level as a Gemini Batch API job (requires Gemini provider)",
    )
    parser.add_argument(
        "--job-name",
        default=None,
        metavar="NAME",
        help=(
            "Resume polling an already-submitted batch job and ingest its results. "
            "Example: batches/abc123. --levels is still required."
        ),
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Seconds between batch job status polls (default: 60)",
    )

    # Apply config file values as defaults (CLI args override these).
    parser.set_defaults(
        count=cfg.get("count", cfg.get("vocab_count", 10)),
        api_delay=cfg.get("api_delay_seconds", 1.0),
    )

    args = parser.parse_args()
    if not args.dedupe and not args.job_name and not args.types:
        parser.error("--types is required unless --dedupe or --job-name is set")
    args._cfg = cfg
    return args


async def main() -> None:
    args = _parse_args()
    cfg: dict[str, Any] = args._cfg
    api_delay: float = args.api_delay

    story_titles_path: Path = args.story_titles or (settings.DATA_DIR / "story_titles.json")
    story_titles = _load_story_titles(story_titles_path)

    grammar_topics_path: Path = args.grammar_topics or (settings.DATA_DIR / "grammar_topics.json")
    grammar_topics = _load_grammar_topics(grammar_topics_path)

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # ------------------------------------------------------------------
    # Job-resume mode: poll an existing batch and ingest results
    # ------------------------------------------------------------------
    if args.job_name:
        client, gt, _model = _build_gemini_client()
        try:
            job = _poll_batch(client, args.job_name, args.poll_interval)
            summary = _ingest_batch_results(job, args.dry_run, args.no_seed, db)
        finally:
            db.close()
        print("\n" + "=" * 70)
        print(f"{'Level':<6} {'Type':<10} {'Generated':>10} {'Invalid':>8} {'Skipped':>8} {'Saved':>7}")
        print("-" * 70)
        for level, types in summary.items():
            for content_type, counts in types.items():
                print(
                    f"{level:<6} {content_type:<10} "
                    f"{counts['generated']:>10} "
                    f"{counts['invalid']:>8} "
                    f"{counts['skipped']:>8} "
                    f"{counts['saved']:>7}"
                )
        print("=" * 70)
        return

    # ------------------------------------------------------------------
    # Dedupe-only mode
    # ------------------------------------------------------------------
    if args.dedupe:
        print("\n" + "=" * 60)
        print(f"{'Level':<6} {'Before':>8} {'Removed':>8} {'After':>8}")
        print("-" * 60)
        try:
            for level in args.levels:
                json_path = settings.DATA_DIR / "vocabulary" / f"{level}_words.json"
                items = _load_json_file(json_path)
                before = len(items)
                deduped, removed = _dedupe_json(items)
                after = len(deduped)
                if removed and not args.dry_run:
                    _save_json_file(json_path, deduped)
                logger.info(
                    "[dedupe] %s JSON: %d → %d (%d removed)",
                    level, before, after, removed,
                )
                print(f"{level:<6} {before:>8} {removed:>8} {after:>8}")

            if not args.no_seed and not args.dry_run:
                db_removed = _dedupe_db_vocabulary(db)
                logger.info("[dedupe] DB: %d duplicate rows deleted", db_removed)
                print(f"{'DB':<6} {'':>8} {db_removed:>8} {'':>8}")
        finally:
            db.close()
        print("=" * 60)
        if args.dry_run:
            print("(dry-run: no files written, no database changes)")
        elif args.no_seed:
            print("(no-seed: JSON files updated, database not changed)")
        return

    # ------------------------------------------------------------------
    # Normal generation mode
    # ------------------------------------------------------------------

    # summary[level][type] = {generated, invalid, skipped, saved}
    summary: dict[str, dict[str, dict[str, int]]] = {}

    try:
        for level in args.levels:
            logger.info("=== Level: %s ===", level.upper())
            summary[level] = {}

            if "vocab" in args.types:
                # story_titles and grammar_topics complement each other:
                # story themes cover communicative topics, grammar slugs cover
                # structural/linguistic themes — vocab should span both.
                story_theme_list = [theme for (lvl, theme) in story_titles if lvl == level]
                grammar_slug_list = [t["slug"] for t in grammar_topics.get(level, [])]
                # Merge without duplicates, preserving order.
                seen_themes: set[str] = set()
                vocab_themes: list[str] = []
                for t in story_theme_list + grammar_slug_list:
                    if t not in seen_themes:
                        seen_themes.add(t)
                        vocab_themes.append(t)
                if not vocab_themes:
                    vocab_themes = THEMES_BY_LEVEL.get(level, [])
                if args.batch:
                    summary[level]["vocab"] = await populate_vocabulary_batch(
                        level, args.count, args.dry_run, args.no_seed, db,
                        poll_interval=args.poll_interval,
                        themes=vocab_themes,
                    )
                else:
                    summary[level]["vocab"] = await populate_vocabulary(
                        level, args.count, args.dry_run, args.no_seed, db,
                        api_delay=api_delay,
                        themes=vocab_themes,
                    )

            if "stories" in args.types:
                if args.batch:
                    summary[level]["stories"] = await populate_stories_batch(
                        level, args.dry_run, args.no_seed, db,
                        poll_interval=args.poll_interval,
                        story_titles=story_titles,
                        story_count=args.count,
                    )
                else:
                    summary[level]["stories"] = await populate_stories(
                        level, args.dry_run, args.no_seed, db,
                        api_delay=api_delay,
                        story_titles=story_titles,
                        story_count=args.count,
                    )
    finally:
        db.close()

    # Print summary table
    print("\n" + "=" * 70)
    print(f"{'Level':<6} {'Type':<10} {'Generated':>10} {'Invalid':>8} {'Skipped':>8} {'Saved':>7}")
    print("-" * 70)
    for level, types in summary.items():
        for content_type, counts in types.items():
            print(
                f"{level:<6} {content_type:<10} "
                f"{counts['generated']:>10} "
                f"{counts['invalid']:>8} "
                f"{counts['skipped']:>8} "
                f"{counts['saved']:>7}"
            )
    print("=" * 70)
    if args.dry_run:
        print("(dry-run: no files written, no database changes)")
    elif args.no_seed:
        print("(no-seed: JSON files updated, database not changed)")


if __name__ == "__main__":
    asyncio.run(main())
