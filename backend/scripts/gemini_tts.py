#!/usr/bin/env python3
"""
Generate Dutch audio for stories and vocabulary using Gemini 2.5 Flash TTS.

Run from backend/ with venv activated:
    .venv/bin/python scripts/gemini_tts.py --help

Examples:
    # Dry-run: see what would be generated without calling the API
    .venv/bin/python scripts/gemini_tts.py --type vocabulary --level a0 --dry-run

    # Generate vocabulary audio for level a0, limit to 5 items for smoke testing
    .venv/bin/python scripts/gemini_tts.py --type vocabulary --level a0 --max-items 5

    # Generate story audio for ALL levels (reads every data/stories/*_stories.json)
    .venv/bin/python scripts/gemini_tts.py --type stories

    # File-only mode (skip DB updates)
    .venv/bin/python scripts/gemini_tts.py --type vocabulary --level a0 --no-db

    # Force-regenerate even if audio already exists
    .venv/bin/python scripts/gemini_tts.py --type stories --level a1 --force
"""
import argparse
import base64
import json
import logging
import sys
import time
import wave
from io import BytesIO
from pathlib import Path

# ── bootstrap path so app.* imports work ────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.models import AudioFile, Story, VocabularyItem
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Gemini TTS model name ────────────────────────────────────────────────────
# Reads GEMINI_TTS_MODEL from the project .env (loaded by pydantic-settings
# inside config.py). If missing, fall back to the known preview model name.
# Normalize the model ID to what the google-genai client expects:
#   "gemini-2.5-flash-preview-tts"  (bare kebab-case)
# Handles two common mis-formats from .env:
#   "gemini/gemini-2.5-flash-preview-tts"  → strip litellm prefix
#   "gemini/Gemini 2.5 Flash Preview TTS"  → strip prefix + lowercase + spaces→dashes
_raw_model: str = getattr(settings, "GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
_bare: str = _raw_model.split("/", 1)[-1] if "/" in _raw_model else _raw_model
TTS_MODEL: str = _bare.lower().replace(" ", "-") if " " in _bare else _bare

# ── PCM audio parameters returned by the Gemini TTS API ─────────────────────
PCM_SAMPLE_RATE = 24_000  # Hz
PCM_CHANNELS = 1           # mono
PCM_SAMPLE_WIDTH = 2       # bytes (16-bit signed)

# ── TTS system instructions ───────────────────────────────────────────────────
VOCAB_SYSTEM_PROMPT = (
    "Role: Helpful language instructor. "
    "Accent: Northern Dutch (Groningen). "
    "Pronunciation Focus: Articulate vowels clearly with slight regional elongation. "
    "Pronounce 'g' and 'ch' as distinct, hard guttural sounds. "
    "Enunciate all word endings sharply; do not drop the final 'n', 'en', or 't', ensuring maximum clarity for beginners. "
    "Delivery: Pace at 0.85x speed. Tone is friendly and encouraging. "
    "Structure: Read [Word with article] followed by a 0.5-second pause, then [Plural form] "
    "followed by a 0.5-second pause, and finally the [Example sentence]. "
    "Insert a 1.5-second pause between completely new vocabulary entries."
)

STORY_SYSTEM_PROMPT = (
    "Role: Expressive Dutch storyteller. "
    "Accent: Northern Dutch (Groningen). "
    "Pronunciation Focus: Maintain crisp consonants, hard 'g'/'ch' sounds, and distinct regional vowel clarity. "
    "Crucially, do not slur, muffle, or drop word endings during emotional shifts; final syllables must remain fully intact for language learners. "
    "Delivery: Base pace at 0.85x speed. Use variable pacing (rubato) for narrative flow. "
    "Adapt tone to the mood (e.g., warmth for domestic scenes, tension for suspense). "
    "Prosody: Incorporate natural breathing. Pause 0.5 seconds at commas and 1.2 seconds at paragraph breaks. "
    "Use expressive intonation for character shifts while strictly maintaining regional phonetic accuracy."
)

VOICE_VOCAB = "Charon"
VOICE_STORY = "Aoede"

# ── output filename prefixes ──────────────────────────────────────────────────
# Prefixes encode content type so files can be globbed and identified without
# parsing the full name. Used for fast pre-scan skip sets.
VOCAB_FILE_PREFIX = "gemini_vocab_"
STORY_FILE_PREFIX = "gemini_story_"


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_client():
    """Return a configured google-genai client. Fails fast if key is missing."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        log.error(
            "GEMINI_API_KEY is not set. Add it to your .env file and retry."
        )
        sys.exit(1)
    if not TTS_MODEL:
        log.error(
            "GEMINI_TTS_MODEL is not set. Add it to your .env file and retry."
        )
        sys.exit(1)
    try:
        from google import genai
        from google.genai import types as genai_types  # noqa: F401 – validate import
    except ImportError:
        log.error(
            "google-genai is not installed. Run: pip install google-genai>=1.10.0"
        )
        sys.exit(1)

    return genai.Client(api_key=api_key), genai_types


def pcm_to_wav_bytes(pcm_bytes: bytes) -> bytes:
    """Wrap raw 16-bit LE PCM bytes in a WAV container."""
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(PCM_CHANNELS)
        wf.setsampwidth(PCM_SAMPLE_WIDTH)
        wf.setframerate(PCM_SAMPLE_RATE)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def synthesize(
    client,
    genai_types,
    text: str,
    voice: str,
    system_prompt: str,
) -> bytes:
    """
    Call Gemini TTS and return raw WAV bytes.

    The API returns base64-encoded 16-bit PCM at 24 kHz. This function decodes
    that payload and wraps it in a WAV container before returning.

    Note: Gemini TTS models reject system_instruction. Style/accent directives
    are prepended directly to the user-turn text instead.
    """
    from google.genai import types as gt

    prompted_text = f"{system_prompt}\n\n{text}"

    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=prompted_text,
        config=gt.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=gt.SpeechConfig(
                voice_config=gt.VoiceConfig(
                    prebuilt_voice_config=gt.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )

    try:
        part = response.candidates[0].content.parts[0]
        raw = part.inline_data.data
        # The google-genai SDK may return the audio as:
        #   - a base64-encoded str  (older SDK / REST passthrough)
        #   - already-decoded bytes (newer SDK, most common)
        # Calling base64.b64decode() on raw bytes silently produces
        # a tiny garbage output, so we check the type first.
        if isinstance(raw, str):
            audio_bytes = base64.b64decode(raw)
        else:
            audio_bytes = bytes(raw)
        # The payload may be raw PCM *or* a complete WAV file.
        # If RIFF header is present, write as-is; otherwise wrap in WAV.
        if audio_bytes[:4] == b"RIFF":
            return audio_bytes
        return pcm_to_wav_bytes(audio_bytes)
    except (IndexError, AttributeError) as exc:
        raise RuntimeError(
            f"Unexpected TTS response structure: {exc}. "
            f"Finish reason: {response.candidates[0].finish_reason!r}"
        ) from exc

    return pcm_to_wav_bytes(pcm_bytes)


def wav_to_mp3_bytes(wav_bytes: bytes) -> bytes:
    """Convert WAV bytes to MP3 bytes using lameenc (no ffmpeg required)."""
    import lameenc
    buf = BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        pcm_bytes = wf.readframes(wf.getnframes())
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(128)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(n_channels)
    encoder.set_quality(2)  # 2 = highest quality
    mp3_data = encoder.encode(pcm_bytes)
    mp3_data += encoder.flush()
    return mp3_data


def save_audio(audio_bytes: bytes, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_bytes)


def _existing_mp3s(output_dir: Path, prefix: str) -> set[str]:
    """Glob output_dir once for .mp3 files matching prefix and return their names."""
    return {p.name for p in output_dir.glob(f"{prefix}*.mp3")}


# ── JSON loaders ──────────────────────────────────────────────────────────────

def load_vocabulary(path: Path, level_filter: str | None):
    """
    Yield (dutch_word, article, plural, example_nl, level) from a vocabulary JSON file.
    Skips items missing dutch_word or level.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data:
        dutch_word = item.get("dutch_word", "").strip()
        level = (item.get("level") or "").strip().lower()
        if not dutch_word or not level:
            continue
        if level_filter and level != level_filter.lower():
            continue
        yield (
            dutch_word,
            item.get("article", ""),
            item.get("plural", ""),
            item.get("example_nl", ""),
            level,
        )


def load_stories(path: Path, level_filter: str | None):
    """
    Yield (slug, content_nl, level) from a stories JSON file.
    Skips items missing slug, content_nl, or level.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data:
        slug = (item.get("slug") or "").strip()
        content_nl = (item.get("content_nl") or "").strip()
        level = (item.get("level") or "").strip().lower()
        if not slug or not content_nl or not level:
            continue
        if level_filter and level != level_filter.lower():
            continue
        yield slug, content_nl, level


# ── input file resolution ────────────────────────────────────────────────────

def resolve_input_files(content_type: str, level: str | None) -> list[Path]:
    """
    Return the JSON data file(s) matching content_type and optional level.

    With a level:   data/{type}/{level}_{suffix}.json   (single file)
    Without level:  data/{type}/*_{suffix}.json          (all files sorted)
    """
    suffix = "words" if content_type == "vocabulary" else "stories"
    base = settings.DATA_DIR / ("vocabulary" if content_type == "vocabulary" else "stories")
    if level:
        target = base / f"{level.lower()}_{suffix}.json"
        return [target] if target.is_file() else []
    return sorted(base.glob(f"*_{suffix}.json"))


# ── DB skip helpers ───────────────────────────────────────────────────────────

def _has_gemini_audio_vocab(db, dutch_word: str, level: str) -> bool:
    """Return True if this vocab item already has a gemini AudioFile in the DB."""
    item = (
        db.query(VocabularyItem)
        .filter(VocabularyItem.dutch_word == dutch_word, VocabularyItem.level == level)
        .first()
    )
    if not item:
        return False
    return (
        db.query(AudioFile)
        .filter(AudioFile.vocab_item_id == item.id, AudioFile.source == "gemini")
        .first()
    ) is not None


def _has_gemini_audio_story(db, slug: str) -> bool:
    """Return True if this story already has a gemini audio_path set in the DB."""
    story = db.query(Story).filter(Story.slug == slug).first()
    return bool(story and story.audio_path and story.audio_path.startswith(STORY_FILE_PREFIX))


# ── output filename helpers ───────────────────────────────────────────────────

def _safe(s: str) -> str:
    """Strip characters unsafe for filenames."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)


def vocab_filename(dutch_word: str, level: str) -> str:
    return f"{VOCAB_FILE_PREFIX}{_safe(dutch_word)}_{_safe(level)}.mp3"


def story_filename(slug: str) -> str:
    return f"{STORY_FILE_PREFIX}{_safe(slug)}.mp3"


# ── DB upsert helpers ─────────────────────────────────────────────────────────

def upsert_vocab_audio(db, dutch_word: str, level: str, filename: str, voice: str) -> None:
    """Replace existing AudioFile rows for this vocab item with the new Gemini file."""
    item = (
        db.query(VocabularyItem)
        .filter(VocabularyItem.dutch_word == dutch_word, VocabularyItem.level == level)
        .first()
    )
    if not item:
        log.warning("  DB: VocabularyItem not found for '%s' (level=%s) — skipping DB update", dutch_word, level)
        return

    # Remove stale audio rows (gtts or previous gemini runs)
    db.query(AudioFile).filter(
        AudioFile.vocab_item_id == item.id,
        AudioFile.source.in_(["gtts", "gemini"]),
    ).delete(synchronize_session=False)

    word_with_article = f"{item.article} {dutch_word}".strip() if item.article else dutch_word
    sentence_text = f"{word_with_article}, {item.plural}" if item.plural else word_with_article
    db.add(AudioFile(
        vocab_item_id=item.id,
        sentence_text_nl=sentence_text,
        file_path=filename,
        source="gemini",
        license="Gemini API",
        speaker=voice,
    ))
    db.commit()


def upsert_story_audio(db, slug: str, filename: str) -> None:
    """Update Story.audio_path for the given slug."""
    story = db.query(Story).filter(Story.slug == slug).first()
    if not story:
        log.warning("  DB: Story not found for slug '%s' — skipping DB update", slug)
        return
    story.audio_path = filename
    db.commit()


# ── main processing loops ─────────────────────────────────────────────────────

def process_vocabulary(args, client, genai_types, db) -> tuple[int, int, int]:
    """Returns (generated, skipped, failed) counts."""
    generated = skipped = failed = 0
    output_dir = Path(args.output_dir)
    existing_mp3s = _existing_mp3s(output_dir, VOCAB_FILE_PREFIX)

    items: list[tuple[str, str, str, str, str]] = []
    for input_path in args.input_files:
        items.extend(load_vocabulary(input_path, args.level))
    log.info("Vocabulary items to process: %d", len(items))

    for dutch_word, article, plural, example_nl, level in items:
        if args.max_items and generated >= args.max_items:
            break
        # Compose text: "de kat, katten. De kat slaapt op de bank."
        word_with_article = f"{article} {dutch_word}".strip() if article else dutch_word
        word_part = f"{word_with_article}, {plural}" if plural else word_with_article
        text = f"{word_part}. {example_nl}" if example_nl else word_part

        filename = vocab_filename(dutch_word, level)
        output_path = output_dir / filename

        if not args.force:
            if db and _has_gemini_audio_vocab(db, dutch_word, level):
                log.info("SKIP  %s (gemini audio already in DB)", filename)
                skipped += 1
                continue
            if filename in existing_mp3s:
                log.info("SKIP  %s (file exists)", filename)
                skipped += 1
                continue

        if args.dry_run:
            log.info("DRY   %s  ← %r", filename, text[:60])
            generated += 1
            continue

        try:
            log.info("GEN   %s", filename)
            wav_bytes = synthesize(client, genai_types, text, VOICE_VOCAB, VOCAB_SYSTEM_PROMPT)
            save_audio(wav_to_mp3_bytes(wav_bytes), output_path)
            existing_mp3s.add(filename)
            if not args.no_db and db:
                upsert_vocab_audio(db, dutch_word, level, filename, VOICE_VOCAB)
            generated += 1
        except Exception as exc:
            log.warning("FAIL  %s — %s: %s", filename, type(exc).__name__, exc)
            failed += 1

        time.sleep(args.delay)

    return generated, skipped, failed


def process_stories(args, client, genai_types, db) -> tuple[int, int, int]:
    """Returns (generated, skipped, failed) counts."""
    generated = skipped = failed = 0
    output_dir = Path(args.output_dir)
    existing_mp3s = _existing_mp3s(output_dir, STORY_FILE_PREFIX)

    items: list[tuple[str, str, str]] = []
    for input_path in args.input_files:
        items.extend(load_stories(input_path, args.level))
    log.info("Stories to process: %d", len(items))

    for slug, content_nl, level in items:
        if args.max_items and generated >= args.max_items:
            break
        filename = story_filename(slug)
        output_path = output_dir / filename

        if not args.force:
            if db and _has_gemini_audio_story(db, slug):
                log.info("SKIP  %s (gemini audio already in DB)", filename)
                skipped += 1
                continue
            if filename in existing_mp3s:
                log.info("SKIP  %s (file exists)", filename)
                skipped += 1
                continue

        if args.dry_run:
            log.info("DRY   %s  ← slug=%r (%d chars)", filename, slug, len(content_nl))
            generated += 1
            continue

        try:
            log.info("GEN   %s", filename)
            wav_bytes = synthesize(client, genai_types, content_nl, VOICE_STORY, STORY_SYSTEM_PROMPT)
            save_audio(wav_to_mp3_bytes(wav_bytes), output_path)
            existing_mp3s.add(filename)
            if not args.no_db and db:
                upsert_story_audio(db, slug, filename)
            generated += 1
        except Exception as exc:
            log.warning("FAIL  %s — %s: %s", filename, type(exc).__name__, exc)
            failed += 1

        time.sleep(args.delay)

    return generated, skipped, failed


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Dutch TTS audio via Gemini and update the DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["stories", "vocabulary"],
        dest="content_type",
        help="Content type to process",
    )
    parser.add_argument(
        "--level",
        default=None,
        help="Filter by level (e.g. a0, a1, b1). Omit to process all levels.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(settings.AUDIO_DIR),
        help=f"Directory to write audio files (default: {settings.AUDIO_DIR})",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N items (useful for smoke testing)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Seconds to sleep between API calls (default: 1.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log planned actions without calling the API or modifying the DB",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip all DB reads/writes (file output only)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-generate even if the output file already exists",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    args.input_files = resolve_input_files(args.content_type, args.level)
    if not args.input_files:
        log.error(
            "No input files found for --type %s --level %s. "
            "Expected files under: %s",
            args.content_type,
            args.level or "(all)",
            settings.DATA_DIR / ("vocabulary" if args.content_type == "vocabulary" else "stories"),
        )
        sys.exit(1)
    log.info("Input files: %s", [p.name for p in args.input_files])

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Build API client (validates key/model, imports google-genai)
    if args.dry_run:
        client = genai_types = None
    else:
        client, genai_types = _build_client()

    # Open DB session once for the whole run
    db = None if args.no_db else SessionLocal()

    try:
        if args.content_type == "vocabulary":
            gen, skip, fail = process_vocabulary(args, client, genai_types, db)
        else:
            gen, skip, fail = process_stories(args, client, genai_types, db)
    finally:
        if db:
            db.close()

    log.info(
        "Done. generated=%d  skipped=%d  failed=%d",
        gen, skip, fail,
    )
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
