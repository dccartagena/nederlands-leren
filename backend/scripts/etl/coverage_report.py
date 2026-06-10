#!/usr/bin/env python3
"""C7 — Coverage report: level × theme × content/asset completeness.

Targets (handoff): A0 300 words / A1 800 / A2 1,500; ≥3 example sentences
per word; ≥12 stories per level.

Usage:
    python scripts/etl/coverage_report.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.etl.common import DATA_DIR, SENTENCES_DIR, load_json_array  # noqa: E402

WORD_TARGETS = {"a0": 300, "a1": 800, "a2": 1500}
STORY_TARGET = 12


def main() -> None:
    examples_path = SENTENCES_DIR / "examples_by_lemma.json"
    examples = json.loads(examples_path.read_text()) if examples_path.exists() else {}

    vocab_stats: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"words": 0, "examples": 0, "images": 0, "validated": 0, "contrast": 0})
    )
    for path in (DATA_DIR / "vocabulary").glob("*.json"):
        for item in load_json_array(path):
            cell = vocab_stats[item["level"]][item.get("theme", "?")]
            cell["words"] += 1
            if item.get("example_nl") or examples.get(item["dutch_word"].lower()):
                cell["examples"] += 1
            if item.get("image_url"):
                cell["images"] += 1
            if item.get("validated"):
                cell["validated"] += 1
            if item.get("contrast_note_es"):
                cell["contrast"] += 1

    stories_by_level: dict[str, int] = defaultdict(int)
    for path in (DATA_DIR / "stories").glob("*.json"):
        for story in load_json_array(path):
            stories_by_level[story["level"]] += 1

    report: dict = {"levels": {}}
    print(f"{'level':6} {'theme':14} {'words':>6} {'w/ex':>6} {'w/img':>6} {'valid':>6}")
    for level in sorted(vocab_stats):
        level_words = 0
        for theme in sorted(vocab_stats[level]):
            c = vocab_stats[level][theme]
            level_words += c["words"]
            print(f"{level:6} {theme:14} {c['words']:>6} {c['examples']:>6} "
                  f"{c['images']:>6} {c['validated']:>6}")
        target = WORD_TARGETS.get(level)
        stories = stories_by_level.get(level, 0)
        status = f"{level_words}/{target}" if target else str(level_words)
        print(f"{level:6} {'TOTAL':14} {status:>6}   stories: {stories}/{STORY_TARGET}")
        report["levels"][level] = {
            "words": level_words,
            "word_target": target,
            "stories": stories,
            "story_target": STORY_TARGET,
            "themes": {t: dict(c) for t, c in vocab_stats[level].items()},
        }

    out = DATA_DIR / "coverage_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nwritten → {out}")


if __name__ == "__main__":
    main()
