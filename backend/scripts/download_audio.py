#!/usr/bin/env python3
"""
Generate Dutch audio for seeded vocabulary items using Voxtral TTS via Ollama.

The Voxtral community Q4 GGUF model is used as the primary TTS engine.
gTTS (Google Text-to-Speech) is used as a fallback when Ollama is unavailable.

Run from backend/ with venv activated:
    .venv/bin/python scripts/download_audio.py
"""
import sys
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models import VocabularyItem, AudioFile
from app.services.audio_service import synthesize_if_missing

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

AUDIO_DIR = settings.AUDIO_DIR
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def generate_audio_for_all():
    """Generate TTS audio for every vocabulary item that has no audio file.

    Uses Voxtral (Ollama) as the primary engine with gTTS as a fallback.
    Previously-generated files are skipped regardless of which engine created them.
    """
    db = SessionLocal()
    try:
        items = db.query(VocabularyItem).all()
        generated = 0
        for item in items:
            if item.audio_files:
                continue  # already has audio

            text = f"{item.article} {item.dutch_word}" if item.article else item.dutch_word
            try:
                path = synthesize_if_missing(text)
                # Derive the source label from the filename prefix
                source = "voxtral" if path.name.startswith("voxtral_") else "gtts"
                af = AudioFile(
                    vocab_item_id=item.id,
                    sentence_text_nl=text,
                    file_path=str(path.relative_to(AUDIO_DIR)),
                    source=source,
                    license="CC0",
                )
                db.add(af)
                generated += 1
                logger.info("Generated %s audio for '%s'", source, text)
                time.sleep(0.1)  # small pause between requests
            except Exception as e:
                logger.warning("Failed for '%s': %s", text, e)

        db.commit()
        logger.info("Generated %d audio files", generated)
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Generating TTS audio (Voxtral/Ollama) for vocabulary without audio…")
    generate_audio_for_all()
