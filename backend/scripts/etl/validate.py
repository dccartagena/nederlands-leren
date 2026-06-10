#!/usr/bin/env python3
"""C5 — The validation gate. Every content artifact passes or goes to review.

Checks, in order:
  1. Schema (pydantic)
  2. LanguageTool (nl) zero grammar/spelling matches — skipped when not installed
  3. Lexicon cross-check: a noun's article/plural must match nl_canonical
     (kills the LLM's signature de/het errors deterministically) — hard fail
  4. Story level check: ≥95% of content tokens within the known set; the
     new-word budget (≤5) must be respected

Failures land in data/review_queue/<name>.failures.json. With --stamp,
passing items get "validated": true written back into the JSON files.

Usage:
    python scripts/etl/validate.py [--stamp]
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.etl.common import (  # noqa: E402
    DATA_DIR,
    REVIEW_QUEUE_DIR,
    content_tokens,
    load_json_array,
    load_lexicon,
)

MIN_STORY_COVERAGE = 0.95
MAX_NEW_WORDS = 5


class VocabSchema(BaseModel):
    dutch_word: str
    spanish: str
    level: str
    theme: str
    article: str | None = None
    plural: str | None = None
    word_type: str | None = None
    example_nl: str | None = None
    example_es: str | None = None


class StorySchema(BaseModel):
    slug: str
    title_nl: str
    title_es: str
    level: str
    content_nl: str
    content_es: str
    questions_json: list[dict[str, Any]] | None = None


# ── Individual checks ────────────────────────────────────────────────────────

def check_article_plural(item: dict[str, Any], lexicon: dict[str, dict[str, Any]]) -> list[str]:
    """Hard fail when a noun's article or plural contradicts the lexicon."""
    errors = []
    entry = lexicon.get(item["dutch_word"].lower())
    if not entry or entry.get("pos") != "noun":
        return errors
    if entry.get("article") and item.get("article") and item["article"] != entry["article"]:
        errors.append(
            f"article mismatch: content says '{item['article']}', "
            f"lexicon (Wiktionary) says '{entry['article']}'"
        )
    if entry.get("plural") and item.get("plural") and item["plural"] != entry["plural"]:
        errors.append(
            f"plural mismatch: content says '{item['plural']}', "
            f"lexicon says '{entry['plural']}'"
        )
    return errors


def check_story_coverage(
    content_nl: str,
    known_words: set[str],
    declared_new: list[str] | None = None,
) -> list[str]:
    """i+1 gate: ≥95% of content tokens known; ≤5 new words."""
    errors = []
    tokens = content_tokens(content_nl)
    if not tokens:
        return ["story has no content tokens"]
    unknown = [t for t in tokens if t not in known_words]
    unique_unknown = sorted(set(unknown))
    coverage = 1 - (len(unknown) / len(tokens))
    if coverage < MIN_STORY_COVERAGE:
        errors.append(
            f"coverage {coverage:.0%} < {MIN_STORY_COVERAGE:.0%} "
            f"(unknown: {', '.join(unique_unknown[:10])})"
        )
    if len(unique_unknown) > MAX_NEW_WORDS:
        errors.append(f"{len(unique_unknown)} new words exceeds the budget of {MAX_NEW_WORDS}")
    if declared_new is not None:
        undeclared = set(unique_unknown) - {w.lower() for w in declared_new}
        if undeclared:
            errors.append(f"undeclared new words: {', '.join(sorted(undeclared))}")
    return errors


def check_languagetool(texts: list[str]) -> list[list[str]]:
    try:
        import language_tool_python
    except ImportError:
        return [[] for _ in texts]
    tool = language_tool_python.LanguageTool("nl")
    try:
        return [
            [f"{m.ruleId}: {m.message}" for m in tool.check(t)]
            for t in texts
        ]
    finally:
        tool.close()


# ── File-level validation ────────────────────────────────────────────────────

def validate_vocab_file(path: Path, lexicon: dict[str, dict[str, Any]], stamp: bool) -> list[dict]:
    items = load_json_array(path)
    failures = []
    for item in items:
        errors: list[str] = []
        try:
            VocabSchema(**item)
        except ValidationError as exc:
            errors.append(f"schema: {exc.errors()[0]['msg']}")
        errors += check_article_plural(item, lexicon)
        if errors:
            failures.append({"item": item.get("dutch_word"), "errors": errors})
        elif stamp:
            item["validated"] = True
    if stamp:
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2))
    return failures


def validate_story_file(path: Path, known_words: set[str], stamp: bool) -> list[dict]:
    stories = load_json_array(path)
    failures = []
    lt_results = check_languagetool([s.get("content_nl", "") for s in stories])
    for story, lt_errors in zip(stories, lt_results):
        errors: list[str] = []
        try:
            StorySchema(**story)
        except ValidationError as exc:
            errors.append(f"schema: {exc.errors()[0]['msg']}")
        errors += [f"languagetool: {e}" for e in lt_errors]
        if known_words:
            errors += check_story_coverage(
                story.get("content_nl", ""), known_words, story.get("new_words_json")
            )
        if errors:
            failures.append({"item": story.get("slug"), "errors": errors})
        elif stamp:
            story["validated"] = True
    if stamp:
        path.write_text(json.dumps(stories, ensure_ascii=False, indent=2))
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stamp", action="store_true", help="write validated=true on passing items")
    args = parser.parse_args()

    lexicon = load_lexicon()
    if not lexicon:
        print("  warning: no lexicon found — article/plural cross-check skipped")

    # The known-word set for story coverage: all seeded vocabulary per level
    known_by_level: dict[str, set[str]] = {}
    for vocab_file in (DATA_DIR / "vocabulary").glob("*.json"):
        for item in load_json_array(vocab_file):
            known_by_level.setdefault(item["level"], set()).add(item["dutch_word"].lower())
    # A story at level X may use vocabulary from all levels up to X
    cumulative: set[str] = set()
    for lvl in ("a0", "a1", "a2"):
        cumulative |= known_by_level.get(lvl, set())
        known_by_level[lvl] = set(cumulative)

    total_failures = 0
    REVIEW_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    for path in sorted((DATA_DIR / "vocabulary").glob("*.json")):
        failures = validate_vocab_file(path, lexicon, args.stamp)
        if failures:
            out = REVIEW_QUEUE_DIR / f"{path.stem}.failures.json"
            out.write_text(json.dumps(failures, ensure_ascii=False, indent=2))
            print(f"  {path.name}: {len(failures)} failures → {out}")
            total_failures += len(failures)
        else:
            print(f"  {path.name}: ok")

    for path in sorted((DATA_DIR / "stories").glob("*.json")):
        level = path.stem.split("_")[0]
        failures = validate_story_file(path, known_by_level.get(level, set()), args.stamp)
        if failures:
            out = REVIEW_QUEUE_DIR / f"{path.stem}.failures.json"
            out.write_text(json.dumps(failures, ensure_ascii=False, indent=2))
            print(f"  {path.name}: {len(failures)} failures → {out}")
            total_failures += len(failures)
        else:
            print(f"  {path.name}: ok")

    sys.exit(1 if total_failures else 0)


if __name__ == "__main__":
    main()
