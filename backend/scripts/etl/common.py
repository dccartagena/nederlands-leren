"""Shared helpers for the ETL pipeline."""
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

# Allow running scripts directly from backend/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

BACKEND_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BACKEND_DIR.parent / "data"
SOURCES_DIR = DATA_DIR / "sources"        # gitignored, re-downloadable
LEXICON_DIR = DATA_DIR / "lexicon"
SENTENCES_DIR = DATA_DIR / "sentences"
REVIEW_QUEUE_DIR = DATA_DIR / "review_queue"

_WORD_RE = re.compile(r"[a-zA-ZáéíóúüñàèìòùäëïöüĳÁÉÍÓÚÜÑ'’\-]+")

# Function words that shouldn't drive a sentence's CEFR grade
NL_STOPWORDS = frozenset(
    "de het een en of maar ik je jij u hij zij ze we wij jullie dit dat deze die "
    "er hier daar niet geen wel ook al nog naar van in op aan met voor bij uit "
    "om te ben bent is zijn was waren heb hebt heeft hebben had hadden word wordt "
    "worden werd werden kan kunt kunnen kon konden zal zult zullen zou zouden "
    "moet moeten mag mogen wil wilt willen ga gaat gaan ging gingen doe doet doen "
    "deed deden als dan toen dus want omdat dat wie wat waar hoe waarom wanneer "
    "welke mijn jouw uw zijn haar ons onze hun me mij jou hem haar hen hun zich".split()
)


def tokenize_nl(text: str) -> list[str]:
    """Lowercased word tokens (naive; spaCy nl_core_news_lg refines this when installed)."""
    return [t.lower() for t in _WORD_RE.findall(text)]


def content_tokens(text: str) -> list[str]:
    return [t for t in tokenize_nl(text) if t not in NL_STOPWORDS]


def load_json_array(path: Path) -> list[dict[str, Any]]:
    """Read a JSON array file, treating empty files as empty arrays."""
    if path.stat().st_size == 0:
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_lexicon(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Canonical lexicon keyed by lemma (first entry wins per lemma)."""
    path = path or (LEXICON_DIR / "nl_canonical.jsonl")
    if not path.exists():
        return {}
    lexicon: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        lexicon.setdefault(row["lemma"], row)
    return lexicon
