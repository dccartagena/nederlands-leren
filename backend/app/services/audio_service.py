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
