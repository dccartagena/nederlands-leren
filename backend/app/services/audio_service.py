"""
Audio service: serve cached files or synthesize via Voxtral TTS (Ollama).

Primary engine  : mistralai/Voxtral-4B-TTS-2603 community Q4 GGUF via Ollama
                  (OpenAI-compatible /v1/audio/speech endpoint)
Fallback engine : gTTS (Google Text-to-Speech, requires internet access)

Audio files are named deterministically from a SHA-256 hash of the text so
that the same phrase is never synthesised twice.  Voxtral files use the
``voxtral_`` prefix; gTTS fallback files keep the legacy ``gtts_`` prefix so
previously-generated files are still served without re-synthesis.
"""
import hashlib
import logging
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def audio_path_for_text(text: str) -> Path:
    """Deterministic Voxtral output path for a Dutch text snippet."""
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return settings.AUDIO_DIR / f"voxtral_{h}.mp3"


def _gtts_path_for_text(text: str) -> Path:
    """Deterministic gTTS fallback path (kept for backward-compatibility)."""
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return settings.AUDIO_DIR / f"gtts_{h}.mp3"


# ---------------------------------------------------------------------------
# Synthesis engines
# ---------------------------------------------------------------------------


def _synthesize_via_voxtral(text: str, output_path: Path) -> None:
    """Call Ollama's OpenAI-compatible /v1/audio/speech endpoint.

    The Voxtral community Q4 GGUF model (``OLLAMA_TTS_MODEL``) must already
    be pulled in the Ollama instance before this function is invoked.
    """
    url = f"{settings.OLLAMA_BASE_URL}/v1/audio/speech"
    payload = {
        "model": settings.OLLAMA_TTS_MODEL,
        "input": text,
        "response_format": "mp3",
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)
    logger.debug("Voxtral TTS saved to '%s'", output_path)


def _synthesize_via_gtts(text: str, output_path: Path) -> None:
    """Synthesise Dutch text with gTTS (requires internet access)."""
    from gtts import gTTS  # lazy import — optional dependency

    tts = gTTS(text=text, lang="nl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tts.save(str(output_path))
    logger.debug("gTTS saved to '%s'", output_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def synthesize_if_missing(text: str) -> Path:
    """Return a path to a cached audio file for *text*, synthesising if needed.

    Lookup order
    ------------
    1. Existing Voxtral file  (``voxtral_<hash>.mp3``)
    2. Existing gTTS file     (``gtts_<hash>.mp3``) — backward-compatible cache
    3. Synthesise with Voxtral via Ollama
    4. Fall back to gTTS if Voxtral is unavailable

    The ``TTS_PROVIDER`` setting can be set to ``"gtts"`` to skip Voxtral
    entirely (useful in environments without an Ollama instance).
    """
    voxtral_path = audio_path_for_text(text)
    gtts_path = _gtts_path_for_text(text)

    # Return any already-cached file without synthesising
    if voxtral_path.exists():
        return voxtral_path
    if gtts_path.exists():
        return gtts_path

    # --- Voxtral (primary) ---
    if settings.TTS_PROVIDER != "gtts":
        try:
            _synthesize_via_voxtral(text, voxtral_path)
            return voxtral_path
        except Exception as voxtral_err:
            logger.warning(
                "Voxtral TTS failed for '%s', falling back to gTTS: %s",
                text,
                voxtral_err,
            )

    # --- gTTS (fallback) ---
    try:
        _synthesize_via_gtts(text, gtts_path)
        return gtts_path
    except Exception as gtts_err:
        logger.error("gTTS fallback also failed for '%s': %s", text, gtts_err)
        raise
