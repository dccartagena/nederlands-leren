"""
Content scraper service — pulls Dutch language data from open/CC resources.

Sources used:
- Tatoeba     (CC BY 2.0):    Dutch sentences with Spanish translations
- Wiktionary  (CC BY-SA 3.0): Dutch word definitions, articles, inflected forms

Network behaviour:
- Tatoeba: failures are swallowed and return an empty list (best-effort).
- Wiktionary: transport/HTTP errors propagate so callers can return 503;
  only a genuine "page not found" response returns {}.
"""
import asyncio
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TATOEBA_SEARCH_URL = "https://tatoeba.org/api_v0/search"
DUTCH_WIKTIONARY_API_URL = "https://nl.wiktionary.org/w/api.php"


def _format_cc_notes(
    source: str | None,
    license: str | None,
    attribution: str | None,
) -> str:
    """Format CC licence metadata into a human-readable notes string.

    Used consistently wherever licence information is serialised into the
    ``notes`` column of a VocabularyItem (or any similar text field).
    """
    parts = []
    if source:
        parts.append(f"Source: {source}")
    if license:
        parts.append(f"Licence: {license}")
    if attribution:
        parts.append(f"Attribution: {attribution}")
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Tatoeba  (CC BY 2.0)
# ---------------------------------------------------------------------------

async def fetch_tatoeba_sentences(
    word: str,
    source_lang: str = "nld",
    target_lang: str = "spa",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Fetch Dutch example sentences containing *word* from Tatoeba.

    Each result includes the Dutch sentence, the Spanish translation (when
    available), and attribution metadata required by the CC BY 2.0 licence.

    Args:
        word: Dutch word to search for.
        source_lang: BCP-47 / Tatoeba language code for the source (default "nld").
        target_lang: BCP-47 / Tatoeba language code for the translation (default "spa").
        limit: Maximum number of sentences to return.

    Returns:
        List of dicts with keys: nl, es, source, license.
    """
    params: dict[str, Any] = {
        "from": source_lang,
        "to": target_lang,
        "query": word,
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(TATOEBA_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            results: list[dict[str, Any]] = []
            for entry in data.get("results", []):
                nl_text: str = entry.get("text", "")
                if not nl_text:
                    continue
                es_text = _extract_translation(entry.get("translations", []), target_lang)
                results.append(
                    {
                        "nl": nl_text,
                        "es": es_text,
                        "source": "tatoeba",
                        "license": "CC BY 2.0",
                        "attribution": "Tatoeba.org contributors",
                    }
                )
            return results
        except Exception as exc:
            logger.warning("Tatoeba fetch failed for '%s': %s", word, exc)
            return []


def _extract_translation(translations_payload: Any, target_lang: str) -> str:
    """Extract the first translation matching *target_lang* from Tatoeba payload.

    The Tatoeba API returns translations as a list of lists (indirect vs. direct).
    """
    if not isinstance(translations_payload, list):
        return ""
    for group in translations_payload:
        items = group if isinstance(group, list) else [group]
        for item in items:
            if isinstance(item, dict) and item.get("lang") == target_lang:
                return item.get("text", "")
    return ""


# ---------------------------------------------------------------------------
# Dutch Wiktionary  (CC BY-SA 3.0)
# ---------------------------------------------------------------------------


async def fetch_wiktionary_entry(word: str) -> dict[str, Any]:
    """Fetch Dutch word information from the Dutch Wiktionary.

    Returns a dict with keys: dutch_word, article, plural, word_type,
    example_nl, source, license when the word is found.

    Returns {} only when the word genuinely does not exist in Wiktionary
    (page_id == -1 or no revisions).

    Raises httpx.HTTPError / httpx.TimeoutException for transport or HTTP
    failures so that callers can distinguish "not found" from "unavailable"
    and return the appropriate status code (404 vs 503).
    """
    params: dict[str, Any] = {
        "action": "query",
        "titles": word,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Let transport/HTTP errors propagate — callers handle 503
        resp = await client.get(DUTCH_WIKTIONARY_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                return {}
            revisions = page.get("revisions", [])
            if not revisions:
                return {}
            rev = revisions[0]
            # MediaWiki API returns content in different paths depending on version
            content: str = (
                rev.get("slots", {}).get("main", {}).get("*", "")
                or rev.get("*", "")
            )
            return _parse_wiktionary_wikitext(word, content)
        return {}


def _parse_wiktionary_wikitext(word: str, content: str) -> dict[str, Any]:
    """Parse Dutch Wiktionary wikitext to extract basic word information."""
    result: dict[str, Any] = {
        "dutch_word": word,
        "source": "wiktionary",
        "license": "CC BY-SA 3.0",
        "attribution": "Wiktionary contributors",
    }

    # --- Word type from section headers -----------------------------------
    _WORD_TYPE_MAP = {
        "zelfstandig naamwoord": "noun",
        "werkwoord": "verb",
        "bijvoeglijk naamwoord": "adjective",
        "bijwoord": "adverb",
        "voornaamwoord": "pronoun",
        "voorzetsel": "preposition",
        "lidwoord": "article",
        "telwoord": "numeral",
    }
    lower_content = content.lower()
    for nl_type, en_type in _WORD_TYPE_MAP.items():
        if nl_type in lower_content:
            result["word_type"] = en_type
            break

    # --- Article (de / het) -----------------------------------------------
    article_match = re.search(
        r"\b(de|het)\b\s+" + re.escape(word), content, re.IGNORECASE
    )
    if article_match:
        result["article"] = article_match.group(1).lower()

    # --- Plural form (meervoud) -------------------------------------------
    # Handles Wiktionary template syntax (meervoud=honden / meervoud|honden)
    # and plain prose (meervoud: honden).
    plural_match = re.search(
        r"meervoud[^\n|=:]*[|=:]\s*([a-zéëïöüA-Z\-]+)", content
    )
    if plural_match:
        result["plural"] = plural_match.group(1).strip()

    # --- Example sentence (first italicised phrase) -----------------------
    example_matches = re.findall(r"''\s*(.+?)\s*''", content)
    if example_matches:
        result["example_nl"] = example_matches[0]

    return result


# ---------------------------------------------------------------------------
# High-level helper: enrich a word list with Tatoeba examples
# ---------------------------------------------------------------------------


async def scrape_vocabulary_from_tatoeba(
    words: list[str],
    level: str,
    theme: str,
    concurrency: int = 5,
) -> list[dict[str, Any]]:
    """Return vocabulary stubs enriched with Tatoeba example sentences.

    For each word in *words* the function fetches up to two example sentences
    from Tatoeba concurrently (capped at *concurrency* simultaneous requests)
    and returns a list of partial VocabularyItem dicts (without article, plural,
    etc. — those should come from the LLM generator or manual curation).

    Attribution metadata required by the CC BY 2.0 licence is preserved in
    the ``notes`` field so that it survives a round-trip through the DB.
    """
    semaphore = asyncio.Semaphore(concurrency)
    level_norm = level.lower()
    theme_norm = theme.lower()

    async def _fetch(word: str) -> dict[str, Any]:
        async with semaphore:
            sentences = await fetch_tatoeba_sentences(word, limit=2)
        entry: dict[str, Any] = {
            "dutch_word": word,
            "level": level_norm,
            "theme": theme_norm,
        }
        if sentences:
            first = sentences[0]
            entry["example_nl"] = first["nl"]
            entry["example_es"] = first.get("es", "")
            # Carry attribution/licence through; also stored in notes for DB persistence.
            entry["example_source"] = first["source"]
            entry["example_license"] = first["license"]
            entry["attribution"] = first["attribution"]
            entry["notes"] = _format_cc_notes(first["source"], first["license"], first["attribution"])
        return entry

    return list(await asyncio.gather(*[_fetch(w) for w in words]))


# ---------------------------------------------------------------------------
# Combined scrape: Wiktionary + Tatoeba for a single word
# ---------------------------------------------------------------------------


async def scrape_word(
    word: str,
    level: str = "a1",
    theme: str = "general",
    sentence_limit: int = 3,
) -> dict[str, Any]:
    """Fetch all available open-source data for a single Dutch word.

    Combines Wiktionary metadata with Tatoeba example sentences.
    The returned dict is a partial VocabularyItem that can be merged
    with LLM-generated translations before seeding the database.
    """
    wiki_data = await fetch_wiktionary_entry(word)
    sentences = await fetch_tatoeba_sentences(word, limit=sentence_limit)

    entry: dict[str, Any] = {
        "dutch_word": word,
        "level": level.lower(),
        "theme": theme,
    }

    # Merge Wiktionary data
    for key in ("article", "plural", "word_type", "example_nl"):
        if key in wiki_data:
            entry[key] = wiki_data[key]

    # Add Tatoeba sentences (prefer over Wiktionary example if available)
    if sentences:
        entry["example_nl"] = sentences[0]["nl"]
        entry["example_es"] = sentences[0].get("es", "")

    entry["sentences"] = sentences
    entry["wiktionary"] = wiki_data

    return entry
