#!/usr/bin/env python3
"""C3 — Build the graded NL↔ES sentence bank: data/sentences/nl_es_graded.jsonl.

- Joins Tatoeba's per-language exports through links.csv
- Grades each sentence: level = max CEFR level of its content lemmas
  (unknown lemmas push a sentence to "unk" so it never reaches a learner)
- Optionally drops sentences flagged by LanguageTool (nl), if installed
- Indexes sentences by contained lemma → per-vocab example + cloze material
  in data/sentences/examples_by_lemma.json

Per-sentence attribution is kept (Tatoeba is CC BY 2.0 FR).

Usage:
    python scripts/etl/build_sentences.py [--max-sentences N]
"""
import argparse
import bz2
import csv
import io
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.etl.common import (  # noqa: E402
    SENTENCES_DIR,
    SOURCES_DIR,
    content_tokens,
    load_lexicon,
    tokenize_nl,
    write_jsonl,
)

CEFR_ORDER = ["a1", "a2", "b1", "b2", "c1", "c2"]
MAX_EXAMPLES_PER_LEMMA = 3
MAX_SENTENCE_TOKENS = 14  # keep examples short for A-level learners


def grade_sentence(text: str, lexicon: dict[str, dict[str, Any]]) -> tuple[str, float]:
    """(level, coverage) where level = max CEFR band of content lemmas.

    coverage = share of content tokens found in the lexicon. A sentence with
    any unknown content token is graded 'unk'.
    """
    tokens = content_tokens(text)
    if not tokens:
        return "a1", 1.0
    levels = []
    known = 0
    for tok in tokens:
        entry = lexicon.get(tok)
        if entry:
            known += 1
            levels.append(entry.get("cefr_level") or "b1")
        else:
            levels.append(None)
    coverage = known / len(tokens)
    if coverage < 1.0:
        return "unk", coverage
    return max(levels, key=CEFR_ORDER.index), coverage


def make_cloze(sentence: str, lemma: str) -> str | None:
    """Blank the target lemma in the sentence (whole-token match only)."""
    out = []
    found = False
    for tok in sentence.split():
        core = "".join(tokenize_nl(tok))
        if not found and core == lemma:
            out.append(tok.replace(tok.strip(".,!?;:"), "___"))
            found = True
        else:
            out.append(tok)
    return " ".join(out) if found else None


def languagetool_ok(texts: list[str]) -> list[bool]:
    """True per sentence when LanguageTool (nl) finds no grammar/spell match.

    LanguageTool needs Java; when unavailable every sentence passes and the
    LLM-free gate falls back to lexicon checks only.
    """
    try:
        import language_tool_python
    except ImportError:
        return [True] * len(texts)
    tool = language_tool_python.LanguageTool("nl")
    try:
        return [len(tool.check(t)) == 0 for t in texts]
    finally:
        tool.close()


# ── Tatoeba readers ──────────────────────────────────────────────────────────

def read_sentences_tsv(path: Path) -> dict[int, str]:
    """Tatoeba detailed export: id, lang, text, owner, ... per line."""
    sentences: dict[int, str] = {}
    opener = bz2.open if path.suffix == ".bz2" else open
    with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[operator]
        for row in csv.reader(f, delimiter="\t"):
            if len(row) >= 3:
                sentences[int(row[0])] = row[2]
    return sentences


def read_links(path: Path) -> list[tuple[int, int]]:
    links: list[tuple[int, int]] = []
    if path.suffix == ".bz2" and path.name.endswith(".tar.bz2"):
        with tarfile.open(path, "r:bz2") as tar:
            member = next(m for m in tar.getmembers() if m.name.endswith(".csv"))
            f = io.TextIOWrapper(tar.extractfile(member), encoding="utf-8")  # type: ignore[arg-type]
            for row in csv.reader(f, delimiter="\t"):
                links.append((int(row[0]), int(row[1])))
    else:
        with open(path, encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                links.append((int(row[0]), int(row[1])))
    return links


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-sentences", type=int, default=50000)
    args = parser.parse_args()

    tatoeba = SOURCES_DIR / "tatoeba"
    nl_path = tatoeba / "nld_sentences_detailed.tsv.bz2"
    es_path = tatoeba / "spa_sentences_detailed.tsv.bz2"
    links_path = tatoeba / "links.tar.bz2"
    for p in (nl_path, es_path, links_path):
        if not p.exists():
            print(f"Missing {p} — run scripts/etl/fetch_sources.py first")
            sys.exit(1)

    lexicon = load_lexicon()
    if not lexicon:
        print("Missing lexicon — run scripts/etl/build_lexicon.py first")
        sys.exit(1)

    nl_sentences = read_sentences_tsv(nl_path)
    es_sentences = read_sentences_tsv(es_path)
    print(f"  tatoeba: {len(nl_sentences)} NL / {len(es_sentences)} ES sentences")

    pairs: list[dict[str, Any]] = []
    for src, dst in read_links(links_path):
        nl, es = nl_sentences.get(src), es_sentences.get(dst)
        if not nl or not es or len(tokenize_nl(nl)) > MAX_SENTENCE_TOKENS:
            continue
        level, coverage = grade_sentence(nl, lexicon)
        if level == "unk":
            continue
        pairs.append(
            {
                "nl": nl,
                "es": es,
                "level": level,
                "coverage": round(coverage, 3),
                "source": f"tatoeba#{src}",
                "source_license": "CC BY 2.0 FR",
                "attribution": f"https://tatoeba.org/en/sentences/show/{src}",
            }
        )
        if len(pairs) >= args.max_sentences:
            break

    ok = languagetool_ok([p["nl"] for p in pairs])
    pairs = [p for p, keep in zip(pairs, ok) if keep]
    write_jsonl(SENTENCES_DIR / "nl_es_graded.jsonl", pairs)
    print(f"  graded sentences: {len(pairs)}")

    # Per-lemma example + cloze index (3 shortest level-appropriate sentences)
    by_lemma: dict[str, list[dict[str, Any]]] = {}
    for pair in sorted(pairs, key=lambda p: len(p["nl"])):
        for tok in set(content_tokens(pair["nl"])):
            bucket = by_lemma.setdefault(tok, [])
            if len(bucket) < MAX_EXAMPLES_PER_LEMMA:
                cloze = make_cloze(pair["nl"], tok)
                bucket.append({**pair, "cloze": cloze})

    out = SENTENCES_DIR / "examples_by_lemma.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(by_lemma, ensure_ascii=False))
    print(f"  example index: {len(by_lemma)} lemmas → {out}")


if __name__ == "__main__":
    main()
