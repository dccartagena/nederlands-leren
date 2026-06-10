#!/usr/bin/env python3
"""C2 — Build the canonical Dutch lexicon: data/lexicon/nl_canonical.jsonl.

Join key = (lemma, pos):
    NT2Lex        → cefr_level (first CEFR band where the lemma appears)
    wiktextract   → article (de/het via gender), plural, IPA, ES translation
                    candidates, separable-verb flag
    wordfreq      → Zipf frequency (MIT-licensed SUBTLEX substitute)

Grammar facts (article, plural, IPA) come from Wiktionary, never the LLM.
Level/Zipf conflicts go to data/lexicon/conflicts.jsonl for human review.

Usage:
    python scripts/etl/build_lexicon.py
"""
import csv
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.etl.common import LEXICON_DIR, SOURCES_DIR, read_jsonl, write_jsonl  # noqa: E402

CEFR_ORDER = ["a1", "a2", "b1", "b2", "c1", "c2"]

# A lemma graded A1 by NT2Lex but with Zipf < 3 (or C-level with Zipf > 5.5)
# is suspicious enough for the conflicts file.
ZIPF_FLOOR_FOR_A = 3.0
ZIPF_CEIL_FOR_C = 5.5


# ── Source parsers ───────────────────────────────────────────────────────────

def parse_nt2lex(path: Path) -> dict[tuple[str, str], str]:
    """(lemma, pos) → first CEFR level where the lemma has frequency > 0.

    Tolerant of column naming: finds the lemma/POS columns and the per-level
    frequency columns by header inspection.
    """
    levels: dict[tuple[str, str], str] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames:
            return levels
        headers = {h.lower(): h for h in reader.fieldnames}
        lemma_col = next((headers[h] for h in headers if "lemma" in h or h == "word"), None)
        pos_col = next((headers[h] for h in headers if h in ("pos", "tag", "upos")), None)
        level_cols = {
            lvl: headers[h]
            for lvl in CEFR_ORDER
            for h in headers
            if h.startswith(lvl)
        }
        if not lemma_col or not level_cols:
            print(f"  nt2lex: unrecognized columns {reader.fieldnames}")
            return levels
        for row in reader:
            lemma = (row.get(lemma_col) or "").strip().lower()
            pos = (row.get(pos_col) or "").strip().lower() if pos_col else ""
            if not lemma:
                continue
            for lvl in CEFR_ORDER:
                col = level_cols.get(lvl)
                raw = (row.get(col) or "0") if col else "0"
                try:
                    if float(raw or 0) > 0:
                        levels[(lemma, pos)] = lvl
                        break
                except ValueError:
                    continue
    return levels


def gender_to_article(entry: dict[str, Any]) -> str | None:
    """Map a wiktextract noun entry's gender to de/het via its categories/tags."""
    categories = {
        c["name"] if isinstance(c, dict) else c
        for c in entry.get("categories", [])
    }
    text = " ".join(categories).lower()
    if "neuter" in text:
        return "het"
    if any(g in text for g in ("masculine", "feminine", "common-gender", "common gender")):
        return "de"
    # Fallback: head template arg g=n / g=m / g=f / g=c
    for tpl in entry.get("head_templates", []):
        g = str(tpl.get("args", {}).get("g", ""))
        if g.startswith("n"):
            return "het"
        if g and g[0] in "mfc":
            return "de"
    return None


def extract_wikt_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize one kaikki.org line to the fields the lexicon needs."""
    lemma = (entry.get("word") or "").strip().lower()
    pos = entry.get("pos") or ""
    if not lemma or entry.get("lang_code") != "nl":
        return None

    plural = None
    for form in entry.get("forms", []):
        if "plural" in form.get("tags", []):
            plural = form.get("form")
            break

    ipa = None
    for sound in entry.get("sounds", []):
        if sound.get("ipa"):
            ipa = sound["ipa"]
            break

    es_candidates = []
    for sense in entry.get("senses", []):
        for tr in sense.get("translations", []):
            if tr.get("lang_code") == "es" and tr.get("word"):
                es_candidates.append(tr["word"])
    for tr in entry.get("translations", []):
        if tr.get("lang_code") == "es" and tr.get("word"):
            es_candidates.append(tr["word"])

    separable = any(
        "separable" in (c["name"] if isinstance(c, dict) else c).lower()
        for c in entry.get("categories", [])
    )

    return {
        "lemma": lemma,
        "pos": pos,
        "article": gender_to_article(entry) if pos == "noun" else None,
        "plural": plural,
        "ipa": ipa,
        "es_candidates": list(dict.fromkeys(es_candidates))[:5],
        "separable": separable,
    }


def get_zipf(lemma: str) -> float | None:
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        return None
    z = zipf_frequency(lemma, "nl")
    return round(z, 2) if z > 0 else None


# ── Merge ────────────────────────────────────────────────────────────────────

def merge_entry(
    wikt: dict[str, Any],
    nt2lex_levels: dict[tuple[str, str], str],
) -> tuple[dict[str, Any], str | None]:
    """Combine one Wiktionary entry with NT2Lex level + wordfreq Zipf.

    Returns (row, conflict_reason_or_None).
    """
    key = (wikt["lemma"], wikt["pos"])
    cefr = nt2lex_levels.get(key) or nt2lex_levels.get((wikt["lemma"], ""))
    # Also accept a level assigned under any POS for this lemma
    if cefr is None:
        for (lemma, _pos), lvl in nt2lex_levels.items():
            if lemma == wikt["lemma"]:
                cefr = lvl
                break
    zipf = get_zipf(wikt["lemma"])

    row = {
        **wikt,
        "cefr_level": cefr,
        "zipf": zipf,
        "source": "wiktionary+nt2lex+wordfreq",
        "source_license": "CC BY-SA 3.0 / CC BY-NC-SA 4.0 / MIT",
        "attribution": "Wiktionary (kaikki.org), NT2Lex (Tack et al. 2018), wordfreq",
    }

    conflict = None
    if cefr and zipf is not None:
        if cefr.startswith("a") and zipf < ZIPF_FLOOR_FOR_A:
            conflict = f"NT2Lex says {cefr} but Zipf {zipf} is very rare"
        elif cefr.startswith("c") and zipf > ZIPF_CEIL_FOR_C:
            conflict = f"NT2Lex says {cefr} but Zipf {zipf} is very common"
    return row, conflict


def main() -> None:
    nt2lex_path = SOURCES_DIR / "nt2lex" / "NT2Lex.tsv"
    wikt_path = SOURCES_DIR / "wiktextract" / "kaikki-dutch.jsonl"

    if not wikt_path.exists():
        print(f"Missing {wikt_path} — run scripts/etl/fetch_sources.py first")
        sys.exit(1)

    nt2lex_levels = parse_nt2lex(nt2lex_path) if nt2lex_path.exists() else {}
    if not nt2lex_levels:
        print("  warning: NT2Lex unavailable — cefr_level will be empty (Zipf bands only)")

    rows: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in read_jsonl(wikt_path):
        wikt = extract_wikt_entry(entry)
        if not wikt or (wikt["lemma"], wikt["pos"]) in seen:
            continue
        seen.add((wikt["lemma"], wikt["pos"]))
        row, conflict = merge_entry(wikt, nt2lex_levels)
        rows.append(row)
        if conflict:
            conflicts.append({**row, "conflict": conflict})

    write_jsonl(LEXICON_DIR / "nl_canonical.jsonl", rows)
    write_jsonl(LEXICON_DIR / "conflicts.jsonl", conflicts)
    graded = sum(1 for r in rows if r["cefr_level"])
    print(f"  lexicon: {len(rows)} entries ({graded} CEFR-graded), "
          f"{len(conflicts)} conflicts ({len(conflicts) / max(len(rows), 1):.1%})")


if __name__ == "__main__":
    main()
