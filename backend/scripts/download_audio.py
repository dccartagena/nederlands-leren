#!/usr/bin/env python3
"""
Download Dutch audio from Tatoeba for seeded vocabulary items.
Respects CC BY 2.0 licensing — only downloads sentences tagged as Dutch from Tatoeba.

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

def generate_gtts_for_all(audio_dir: Path) -> None:
    """Fallback: generate gTTS audio for every vocab item that has no audio."""
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
                af = AudioFile(
                    vocab_item_id=item.id,
                    sentence_text_nl=text,
                    file_path=str(path.relative_to(audio_dir)),
                    source="gtts",
                    license="CC0",
                )
                db.add(af)
                generated += 1
                logger.info("Generated audio for '%s'", text)
                time.sleep(0.3)  # polite rate limit
            except Exception as e:
                logger.warning("Failed for '%s': %s", text, e)

        db.commit()
        logger.info("Generated %d gTTS audio files", generated)
    finally:
        db.close()


def main() -> None:
    audio_dir = settings.AUDIO_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Generating gTTS audio for vocabulary without audio…")
    generate_gtts_for_all(audio_dir)


if __name__ == "__main__":
    main()
