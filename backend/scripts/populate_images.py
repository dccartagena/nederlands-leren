#!/usr/bin/env python3
"""
Populate image_url for vocabulary items using the Pixabay API (CC0 images).

Run from the backend/ directory with the venv activated:
    .venv/bin/python scripts/populate_images.py [options]

Options:
    --level a0|a1   Only process items of this level (default: all)
    --overwrite      Update items that already have an image_url
    --dry-run        Print what would be fetched without writing to DB
    --limit N        Stop after N items (useful for testing)

Prerequisites:
    Get a free API key at https://pixabay.com/api/docs/
    then set PIXABAY_API_KEY in your .env file.
"""
import sys
import time
import argparse
from pathlib import Path

import httpx

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.db import models

PIXABAY_URL = "https://pixabay.com/api/"

# Map Spanish theme names → English keyword hints (Pixabay returns more results in English)
THEME_HINTS: dict[str, str] = {
    "animales": "animal",
    "comida": "food",
    "casa": "house",
    "personas": "people",
    "ropa": "clothing",
    "colores": "color",
    "números": "number",
    "tiempo": "weather",
    "naturaleza": "nature",
    "ciudad": "city",
    "transporte": "transport",
    "trabajo": "work",
    "familia": "family",
    "escuela": "school",
    "deporte": "sport",
    "salud": "health",
    "cuerpo": "body",
    "emociones": "emotion",
    "objetos": "object",
    "verbos": "",  # action verbs — skip hint
}


def build_query(item: models.VocabularyItem) -> str:
    """Build an English Pixabay search query from a vocabulary item."""
    word = item.english or item.dutch_word
    hint = THEME_HINTS.get(item.theme or "", "")
    return f"{word} {hint}".strip()


def fetch_image_url(client: httpx.Client, query: str, api_key: str) -> str | None:
    """Call Pixabay API and return the first webformatURL, or None if not found."""
    try:
        resp = client.get(
            PIXABAY_URL,
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "safesearch": "true",
                "per_page": 3,
                "lang": "en",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])
        if hits:
            return hits[0]["webformatURL"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            print("  [rate-limited] waiting 5 s…")
            time.sleep(5)
        else:
            print(f"  [HTTP {e.response.status_code}] {query}")
    except Exception as e:
        print(f"  [error] {query}: {e}")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate vocabulary image_url via Pixabay")
    parser.add_argument("--level", choices=["a0", "a1"], default=None)
    parser.add_argument("--overwrite", action="store_true", help="Replace existing image_url values")
    parser.add_argument("--dry-run", action="store_true", help="Print queries without writing to DB")
    parser.add_argument("--limit", type=int, default=None, help="Max items to process")
    args = parser.parse_args()

    api_key = settings.PIXABAY_API_KEY
    if not api_key and not args.dry_run:
        print(
            "\n[error] PIXABAY_API_KEY is not set.\n"
            "  1. Register for a free key at https://pixabay.com/api/docs/\n"
            "  2. Add PIXABAY_API_KEY=<your_key> to backend/.env\n"
            "  3. Re-run this script.\n"
            "  Tip: use --dry-run to preview queries without a key.\n"
        )
        sys.exit(1)

    db = SessionLocal()
    try:
        query_set = db.query(models.VocabularyItem)
        if args.level:
            query_set = query_set.filter(models.VocabularyItem.level == args.level)
        if not args.overwrite:
            query_set = query_set.filter(models.VocabularyItem.image_url.is_(None))
        items = query_set.all()
    finally:
        pass  # keep db open for updates below

    total = len(items)
    if args.limit:
        items = items[: args.limit]

    print(f"Found {total} items to process (processing {len(items)}).")
    if args.dry_run:
        print("[dry-run] No DB writes will be made.\n")

    updated = 0
    skipped = 0

    with httpx.Client() as client:
        for i, item in enumerate(items, start=1):
            search_query = build_query(item)
            print(f"[{i}/{len(items)}] {item.dutch_word!r} ({item.spanish}) → query: {search_query!r}", end=" ")

            if args.dry_run:
                print()
                continue

            url = fetch_image_url(client, search_query, api_key)
            if url:
                item.image_url = url
                updated += 1
                print(f"✓")
            else:
                skipped += 1
                print(f"✗ (no result)")

            time.sleep(0.5)

    if not args.dry_run:
        try:
            db.commit()
            print(f"\nDone. {updated} updated, {skipped} skipped (no image found).")
        except Exception as e:
            db.rollback()
            print(f"\n[error] DB commit failed: {e}")
            sys.exit(1)
        finally:
            db.close()
    else:
        db.close()
        print(f"\n[dry-run] Would have processed {len(items)} items.")


if __name__ == "__main__":
    main()
