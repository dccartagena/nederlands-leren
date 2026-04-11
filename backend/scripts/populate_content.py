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
        --levels a0 a1 --types vocab --vocab-count 10

    # Populate everything for all levels (write JSON only, skip DB upsert)
    .venv/bin/python scripts/populate_content.py \\
        --levels a0 a1 a2 b1 b2 --types vocab stories --no-seed
"""
import argparse
import asyncio
import json
import logging
import sys
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

_VOCAB_REQUIRED = {"dutch_word", "spanish", "level", "theme", "word_type"}
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


async def populate_grammar(
    level: str,
    topics: list[dict[str, Any]],
    dry_run: bool,
    no_seed: bool,
    db,
    api_delay: float = 1.0,
) -> dict[str, int]:
    json_path = settings.DATA_DIR / "grammar" / f"{level}_grammar.json"
    existing = _load_json_file(json_path)
    existing_slugs = {t["slug"] for t in existing if "slug" in t}

    generated = invalid = skipped = saved = 0

    for topic in topics:
        slug = topic.get("slug", "")
        if slug in existing_slugs:
            skipped += 1
            continue

        logger.info("  [grammar] level=%s slug=%s — generating …", level, slug)
        try:
            result = await content_generator.generate_grammar_topic(
                level, topic["name_es"], topic["name_nl"], slug
            )
        except Exception as exc:
            logger.error("  [grammar] level=%s slug=%s — generation failed: %s", level, slug, exc)
            await asyncio.sleep(1.0)
            continue

        generated += 1
        result["level"] = level  # ensure level is set

        missing = _validate_grammar_topic(result)
        if missing:
            logger.warning(
                "  [grammar] Skipping slug=%s (missing fields: %s)",
                slug,
                missing,
            )
            invalid += 1
            await asyncio.sleep(1.0)
            continue

        if not dry_run:
            existing.append(result)
            _save_json_file(json_path, existing)
            existing_slugs.add(slug)
            if not no_seed:
                if _upsert_grammar_topic(result, db):
                    saved += 1

        await asyncio.sleep(api_delay)

    return {"generated": generated, "invalid": invalid, "skipped": skipped, "saved": saved}


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
        "--vocab-count",
        type=int,
        metavar="N",
        help="Number of vocabulary words to generate per theme",
    )
    parser.add_argument(
        "--story-count",
        type=int,
        metavar="N",
        help="Number of stories to generate per theme (default: 1)",
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

    # Apply config file values as defaults (CLI args override these).
    parser.set_defaults(
        vocab_count=cfg.get("vocab_count", 10),
        story_count=cfg.get("story_count", 1),
        api_delay=cfg.get("api_delay_seconds", 1.0),
    )

    args = parser.parse_args()
    if not args.dedupe and not args.types:
        parser.error("--types is required unless --dedupe is set")
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
                summary[level]["vocab"] = await populate_vocabulary(
                    level, args.vocab_count, args.dry_run, args.no_seed, db,
                    api_delay=api_delay,
                    themes=vocab_themes,
                )

            if "stories" in args.types:
                summary[level]["stories"] = await populate_stories(
                    level, args.dry_run, args.no_seed, db,
                    api_delay=api_delay,
                    story_titles=story_titles,
                    story_count=args.story_count,
                )

            if "grammar" in args.types:
                topics = grammar_topics.get(level, [])
                summary[level]["grammar"] = await populate_grammar(
                    level, topics, args.dry_run, args.no_seed, db,
                    api_delay=api_delay,
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
