#!/usr/bin/env python3
"""
CLI script to generate Dutch learning content using a configured LLM
and optionally seed the results directly into the database.

Run from the backend/ directory with the venv activated:

    # Generate 10 A1 vocabulary items for the "ciudad" theme (print only)
    .venv/bin/python scripts/generate_content.py vocab --level a1 --theme ciudad

    # Generate and save to the database
    .venv/bin/python scripts/generate_content.py vocab --level a1 --theme ciudad --save

    # Generate a story
    .venv/bin/python scripts/generate_content.py story --level a1 --theme trabajo

    # Generate a grammar topic
    .venv/bin/python scripts/generate_content.py grammar --level a1 \\
        --slug comparativos --name-nl "Vergrotende en overtreffende trap" \\
        --name-es "Comparativos y superlativos"

    # Generate a complete lesson (vocab + grammar tip + story)
    .venv/bin/python scripts/generate_content.py lesson --level a1 --theme ciudad

    # Generate a game exercise
    .venv/bin/python scripts/generate_content.py exercise --level a1 --theme ciudad \\
        --game-type fill_blank

    # Scrape Tatoeba examples for a list of words
    .venv/bin/python scripts/generate_content.py scrape-tatoeba \\
        --words hond kat vis --level a0 --theme animales

    # Look up a word across Wiktionary + Tatoeba
    .venv/bin/python scripts/generate_content.py scrape-word --word fiets

All generated content is printed as formatted JSON.
Pass --save to persist vocabulary, grammar, and story results to the database.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402  (after sys.path patch)
from app.db.session import SessionLocal, engine  # noqa: E402
from app.db import models  # noqa: E402
from app.services import content_generator, content_scraper  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _save_vocabulary(items: list, db) -> int:
    """Persist generated vocabulary items, skipping duplicates."""
    saved = 0
    for w in items:
        existing = db.query(models.VocabularyItem).filter_by(
            dutch_word=w.get("dutch_word"), level=w.get("level")
        ).first()
        if not existing:
            db.add(models.VocabularyItem(**{
                k: v for k, v in w.items() if hasattr(models.VocabularyItem, k)
            }))
            saved += 1
    db.commit()
    return saved


def _save_grammar(topic: dict, db) -> bool:
    """Persist a generated grammar topic, skipping duplicates."""
    existing = db.query(models.GrammarTopic).filter_by(slug=topic.get("slug")).first()
    if existing:
        return False
    db.add(models.GrammarTopic(**{
        k: v for k, v in topic.items() if hasattr(models.GrammarTopic, k)
    }))
    db.commit()
    return True


def _save_story(story: dict, db) -> bool:
    """Persist a generated story, skipping duplicates."""
    existing = db.query(models.Story).filter_by(slug=story.get("slug")).first()
    if existing:
        return False
    db.add(models.Story(**{
        k: v for k, v in story.items() if hasattr(models.Story, k)
    }))
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def cmd_vocab(args: argparse.Namespace) -> None:
    items = await content_generator.generate_vocabulary(args.level, args.theme, args.count)
    _print_json(items)
    if args.save and items:
        models.Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            saved = _save_vocabulary(items, db)
            print(f"\n✓ Saved {saved}/{len(items)} vocabulary items to database.", file=sys.stderr)
        finally:
            db.close()


async def cmd_grammar(args: argparse.Namespace) -> None:
    topic = await content_generator.generate_grammar_topic(
        args.level, args.name_es, args.name_nl, args.slug
    )
    _print_json(topic)
    if args.save and topic:
        models.Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            saved = _save_grammar(topic, db)
            msg = "✓ Saved grammar topic." if saved else "⚠ Grammar topic already exists (slug conflict)."
            print(f"\n{msg}", file=sys.stderr)
        finally:
            db.close()


async def cmd_story(args: argparse.Namespace) -> None:
    story = await content_generator.generate_story(
        args.level, args.theme,
        getattr(args, "title_nl", None),
        getattr(args, "title_es", None),
        getattr(args, "slug", None),
    )
    _print_json(story)
    if args.save and story:
        models.Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            saved = _save_story(story, db)
            msg = "✓ Saved story." if saved else "⚠ Story already exists (slug conflict)."
            print(f"\n{msg}", file=sys.stderr)
        finally:
            db.close()


async def cmd_lesson(args: argparse.Namespace) -> None:
    lesson = await content_generator.generate_lesson(args.level, args.theme, args.vocab_count)
    _print_json(lesson)
    if args.save:
        models.Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            vocab_saved = _save_vocabulary(lesson.get("vocabulary", []), db)
            story_saved = _save_story(lesson.get("story", {}), db)
            print(
                f"\n✓ Saved {vocab_saved} vocabulary items and "
                f"{'1 story' if story_saved else '0 stories (duplicate)'} to database.",
                file=sys.stderr,
            )
        finally:
            db.close()


async def cmd_exercise(args: argparse.Namespace) -> None:
    vocabulary = getattr(args, "vocabulary", None) or None
    exercise = await content_generator.generate_game_exercise(
        args.level, args.theme, args.game_type, vocabulary
    )
    _print_json(exercise)


async def cmd_scrape_tatoeba(args: argparse.Namespace) -> None:
    items = await content_scraper.scrape_vocabulary_from_tatoeba(
        args.words, args.level, args.theme
    )
    _print_json(items)
    if args.save and items:
        models.Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            saved = _save_vocabulary(items, db)
            print(f"\n✓ Saved {saved}/{len(items)} items to database.", file=sys.stderr)
        finally:
            db.close()


async def cmd_scrape_word(args: argparse.Namespace) -> None:
    data = await content_scraper.scrape_word(
        args.word,
        getattr(args, "level", "a1"),
        getattr(args, "theme", "general"),
        getattr(args, "sentence_limit", 3),
    )
    _print_json(data)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or scrape Dutch learning content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- vocab ---------------------------------------------------------------
    p_vocab = sub.add_parser("vocab", help="Generate vocabulary items with LLM")
    p_vocab.add_argument("--level", default="a1", help="CEFR level (a0, a1, …)")
    p_vocab.add_argument("--theme", default="ciudad", help="Thematic category")
    p_vocab.add_argument("--count", type=int, default=10, help="Number of words")
    p_vocab.add_argument("--save", action="store_true", help="Persist to database")

    # -- grammar -------------------------------------------------------------
    p_gram = sub.add_parser("grammar", help="Generate a grammar topic with LLM")
    p_gram.add_argument("--level", default="a1")
    p_gram.add_argument("--slug", required=True, help="URL-friendly identifier")
    p_gram.add_argument("--name-nl", dest="name_nl", required=True)
    p_gram.add_argument("--name-es", dest="name_es", required=True)
    p_gram.add_argument("--save", action="store_true")

    # -- story ---------------------------------------------------------------
    p_story = sub.add_parser("story", help="Generate a reading story with LLM")
    p_story.add_argument("--level", default="a1")
    p_story.add_argument("--theme", default="ciudad")
    p_story.add_argument("--title-nl", dest="title_nl", default=None)
    p_story.add_argument("--title-es", dest="title_es", default=None)
    p_story.add_argument("--slug", default=None)
    p_story.add_argument("--save", action="store_true")

    # -- lesson --------------------------------------------------------------
    p_lesson = sub.add_parser("lesson", help="Generate a complete lesson with LLM")
    p_lesson.add_argument("--level", default="a1")
    p_lesson.add_argument("--theme", default="ciudad")
    p_lesson.add_argument("--vocab-count", dest="vocab_count", type=int, default=5)
    p_lesson.add_argument("--save", action="store_true")

    # -- exercise ------------------------------------------------------------
    p_ex = sub.add_parser("exercise", help="Generate a game exercise with LLM")
    p_ex.add_argument("--level", default="a1")
    p_ex.add_argument("--theme", default="ciudad")
    p_ex.add_argument(
        "--game-type",
        dest="game_type",
        default="fill_blank",
        choices=["fill_blank", "multiple_choice", "unscramble", "word_match"],
    )
    p_ex.add_argument(
        "--vocabulary",
        nargs="*",
        help="Optional Dutch words to use as hints",
    )

    # -- scrape-tatoeba ------------------------------------------------------
    p_tat = sub.add_parser(
        "scrape-tatoeba", help="Enrich a word list with Tatoeba examples (CC BY 2.0)"
    )
    p_tat.add_argument("--words", nargs="+", required=True)
    p_tat.add_argument("--level", default="a1")
    p_tat.add_argument("--theme", default="general")
    p_tat.add_argument("--save", action="store_true")

    # -- scrape-word ---------------------------------------------------------
    p_word = sub.add_parser(
        "scrape-word", help="Fetch Wiktionary + Tatoeba data for one Dutch word"
    )
    p_word.add_argument("--word", required=True)
    p_word.add_argument("--level", default="a1")
    p_word.add_argument("--theme", default="general")
    p_word.add_argument("--sentence-limit", dest="sentence_limit", type=int, default=3)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_COMMAND_MAP = {
    "vocab": cmd_vocab,
    "grammar": cmd_grammar,
    "story": cmd_story,
    "lesson": cmd_lesson,
    "exercise": cmd_exercise,
    "scrape-tatoeba": cmd_scrape_tatoeba,
    "scrape-word": cmd_scrape_word,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler = _COMMAND_MAP.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    asyncio.run(handler(args))


if __name__ == "__main__":
    main()
