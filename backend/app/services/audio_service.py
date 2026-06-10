"""
Audio service: serve cached files or synthesize via gTTS fallback.
"""
import hashlib
import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def audio_path_for_text(text: str) -> Path:
    """Deterministic file path for a Dutch text snippet."""
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return settings.AUDIO_DIR / f"gtts_{h}.mp3"


def synthesize_if_missing(text: str) -> Path:
    """Return path to audio file, generating via gTTS if not cached."""
    path = audio_path_for_text(text)
    if not path.exists():
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="nl")
            path.parent.mkdir(parents=True, exist_ok=True)
            tts.save(str(path))
        except Exception as e:
            logger.error("gTTS synthesis failed for '%s': %s", text, e)
            raise
    return path


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)


def _vocab_text(dutch_word: str, article: str | None) -> str:
    return f"{article} {dutch_word}" if article else dutch_word


def resolve_vocab_audio(dutch_word: str, level: str, article: str | None = None) -> Path | None:
    """Find an existing audio file for a vocab item under any historical
    naming convention (Gemini TTS, legacy per-word gTTS, hash-based gTTS)."""
    candidates = [
        settings.AUDIO_DIR / f"gemini_vocab_{_safe(dutch_word)}_{_safe(level)}.mp3",
        settings.AUDIO_DIR / f"gtts_{dutch_word}_{level}.wav",
        audio_path_for_text(_vocab_text(dutch_word, article)),
        audio_path_for_text(dutch_word),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def ensure_vocab_audio(dutch_word: str, level: str, article: str | None = None) -> Path:
    """Resolve a vocab item's audio, synthesizing via gTTS when none exists."""
    existing = resolve_vocab_audio(dutch_word, level, article)
    if existing:
        return existing
    return synthesize_if_missing(_vocab_text(dutch_word, article))
