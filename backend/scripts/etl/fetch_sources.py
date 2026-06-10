#!/usr/bin/env python3
"""C1 — Download/refresh the open resource stack into data/sources/.

Sources (handoff Part A):
  nt2lex        NT2Lex CEFR-graded lexicon          (CC BY-NC-SA 4.0)
  wiktextract   kaikki.org Dutch dictionary JSONL   (CC BY-SA 3.0 + GFDL) ~ large
  tatoeba       NL + ES sentences and links          (CC BY 2.0 FR)       ~ large
  opendutchwordnet (referenced, manual)

SUBTLEX-NL is "research purposes" licensed; the pipeline uses the MIT-licensed
`wordfreq` package as the frequency authority instead (handoff R3 fallback).
Open KNM and Common Voice need manual/account download — printed as TODOs.

Usage:
    python scripts/etl/fetch_sources.py [--refresh] [--only nt2lex,tatoeba]
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.etl.common import SOURCES_DIR  # noqa: E402

SOURCES: dict[str, list[tuple[str, str]]] = {
    # (url, target filename)
    "nt2lex": [
        (
            "https://raw.githubusercontent.com/anaistack/NT2Lex/master/lexicon/NT2Lex.tsv",
            "NT2Lex.tsv",
        ),
    ],
    "wiktextract": [
        (
            "https://kaikki.org/dictionary/Dutch/kaikki.org-dictionary-Dutch.jsonl",
            "kaikki-dutch.jsonl",
        ),
    ],
    "tatoeba": [
        (
            "https://downloads.tatoeba.org/exports/per_language/nld/nld_sentences_detailed.tsv.bz2",
            "nld_sentences_detailed.tsv.bz2",
        ),
        (
            "https://downloads.tatoeba.org/exports/per_language/spa/spa_sentences_detailed.tsv.bz2",
            "spa_sentences_detailed.tsv.bz2",
        ),
        (
            "https://downloads.tatoeba.org/exports/links.tar.bz2",
            "links.tar.bz2",
        ),
    ],
}

MANUAL_SOURCES = {
    "open-knm": "https://open-knm.org/en/vocabulary (community export; place under data/sources/open-knm/)",
    "common-voice": "https://commonvoice.mozilla.org/en/datasets (requires account; place nl clips+TSV under data/sources/common-voice/)",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(name: str, refresh: bool) -> None:
    target_dir = SOURCES_DIR / name
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    for url, filename in SOURCES[name]:
        dest = target_dir / filename
        if dest.exists() and not refresh:
            print(f"  [{name}] {filename} present, skipping (use --refresh to re-download)")
            continue
        print(f"  [{name}] downloading {url} …")
        try:
            urllib.request.urlretrieve(url, dest)  # noqa: S310
        except Exception as exc:  # noqa: BLE001
            print(f"  [{name}] FAILED: {exc} — download manually to {dest}")
            continue
        manifest[filename] = {"url": url, "sha256": _sha256(dest), "bytes": dest.stat().st_size}
        print(f"  [{name}] ok ({manifest[filename]['bytes'] / 1e6:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-download existing files")
    parser.add_argument("--only", help="comma-separated subset of sources")
    args = parser.parse_args()

    names = args.only.split(",") if args.only else list(SOURCES)
    for name in names:
        if name not in SOURCES:
            print(f"Unknown source '{name}' (choose from {', '.join(SOURCES)})")
            continue
        fetch(name, args.refresh)

    print("\nManual sources (not auto-downloadable):")
    for name, hint in MANUAL_SOURCES.items():
        print(f"  [{name}] {hint}")


if __name__ == "__main__":
    main()
