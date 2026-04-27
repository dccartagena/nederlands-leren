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

    # Submit all pending items as a single Gemini Batch API job (Tier 1+)
    .venv/bin/python scripts/gemini_tts.py --type vocabulary --level a0 --batch

    # Resume polling a previously submitted batch job (if session was lost)
    .venv/bin/python scripts/gemini_tts.py --type vocabulary --job-name batches/abc123
"""
import argparse
import base64
import json
import logging
import sys
import time
import wave
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

# ── bootstrap path so app.* imports work ────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.models import AudioFile, Story, VocabularyItem
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

@dataclass
class TtsConfig:
    pcm_sample_rate: int
    pcm_channels: int
    pcm_sample_width: int
    voice_vocab: str
    voice_story: str
    vocab_file_prefix: str
    story_file_prefix: str
    vocab_system_prompt: str
    story_system_prompt: str
    terminal_job_states: frozenset


def _load_tts_config(config_path: Path) -> TtsConfig:
    raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    tts = raw.get("tts", {})
    return TtsConfig(
        pcm_sample_rate=tts.get("pcm_sample_rate", 24000),
        pcm_channels=tts.get("pcm_channels", 1),
        pcm_sample_width=tts.get("pcm_sample_width", 2),
        voice_vocab=tts.get("voice_vocab", "Charon"),
        voice_story=tts.get("voice_story", "Aoede"),
        vocab_file_prefix=tts.get("vocab_file_prefix", "gemini_vocab_"),
        story_file_prefix=tts.get("story_file_prefix", "gemini_story_"),
        vocab_system_prompt=tts.get("vocab_system_prompt", ""),
        story_system_prompt=tts.get("story_system_prompt", ""),
        terminal_job_states=frozenset(raw.get("terminal_job_states", [])),
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_client() -> tuple:
    """Return (client, genai_types, tts_model). Fails fast if key or model missing."""
    raw_model: str = getattr(settings, "GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    bare: str = raw_model.split("/", 1)[-1] if "/" in raw_model else raw_model
    tts_model: str = bare.lower().replace(" ", "-") if " " in bare else bare

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        log.error("GEMINI_API_KEY is not set. Add it to your .env file and retry.")
        sys.exit(1)
    if not tts_model:
        log.error("GEMINI_TTS_MODEL is not set. Add it to your .env file and retry.")
        sys.exit(1)
    try:
        from google import genai
        from google.genai import types as genai_types  # noqa: F401
    except ImportError:
        log.error("google-genai is not installed. Run: pip install google-genai>=1.10.0")
        sys.exit(1)

    return genai.Client(api_key=api_key), genai_types, tts_model


def pcm_to_wav_bytes(pcm_bytes: bytes, cfg: TtsConfig) -> bytes:
    """Wrap raw 16-bit LE PCM bytes in a WAV container."""
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(cfg.pcm_channels)
        wf.setsampwidth(cfg.pcm_sample_width)
        wf.setframerate(cfg.pcm_sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def synthesize(
    client,
    genai_types,
    text: str,
    voice: str,
    system_prompt: str,
    tts_model: str,
    cfg: TtsConfig,
) -> bytes:
    """
    Call Gemini TTS and return raw WAV bytes.

    The API returns base64-encoded 16-bit PCM at 24 kHz. This function decodes
    that payload and wraps it in a WAV container before returning.

    Note: Gemini TTS models reject system_instruction. Style/accent directives
    are prepended directly to the user-turn text instead.
    """
    from google.genai import types as gt

    response = client.models.generate_content(
        model=tts_model,
        contents=f"{system_prompt}\n\n{text}",
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
        if isinstance(raw, str):
            audio_bytes = base64.b64decode(raw)
        else:
            audio_bytes = bytes(raw)
        if audio_bytes[:4] == b"RIFF":
            return audio_bytes
        return pcm_to_wav_bytes(audio_bytes, cfg)
    except (IndexError, AttributeError) as exc:
        raise RuntimeError(
            f"Unexpected TTS response structure: {exc}. "
            f"Finish reason: {response.candidates[0].finish_reason!r}"
        ) from exc


def _extract_audio_from_response(response, cfg: TtsConfig) -> bytes:
    """Extract WAV bytes from a GenerateContentResponse (reusable for batch results)."""
    part = response.candidates[0].content.parts[0]
    raw = part.inline_data.data
    if isinstance(raw, str):
        audio_bytes = base64.b64decode(raw)
    else:
        audio_bytes = bytes(raw)
    if audio_bytes[:4] == b"RIFF":
        return audio_bytes
    return pcm_to_wav_bytes(audio_bytes, cfg)


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

def _has_gemini_audio_vocab(db, dutch_word: str, level: str, vocab_prefix: str) -> bool:
    """Return True if this vocab item already has a gemini AudioFile in the DB."""
    item = (
        db.query(VocabularyItem)
        .filter(VocabularyItem.dutch_word == dutch_word, VocabularyItem.level == level)
        .first()
    )
    if not item:
        return False
    row = (
        db.query(AudioFile)
        .filter(AudioFile.vocab_item_id == item.id, AudioFile.source == "gemini")
        .first()
    )
    return row is not None and row.file_path.startswith(vocab_prefix)


def _has_gemini_audio_story(db, slug: str, story_prefix: str) -> bool:
    """Return True if this story already has a gemini audio_path set in the DB."""
    story = db.query(Story).filter(Story.slug == slug).first()
    return bool(story and story.audio_path and story.audio_path.startswith(story_prefix))


# ── output filename helpers ───────────────────────────────────────────────────

def _safe(s: str) -> str:
    """Strip characters unsafe for filenames."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)


def vocab_filename(dutch_word: str, level: str, prefix: str) -> str:
    return f"{prefix}{_safe(dutch_word)}_{_safe(level)}.mp3"


def story_filename(slug: str, prefix: str) -> str:
    return f"{prefix}{_safe(slug)}.mp3"


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

def process_vocabulary(args, client, genai_types, db, cfg: TtsConfig, tts_model: str) -> tuple[int, int, int]:
    """Returns (generated, skipped, failed) counts."""
    generated = skipped = failed = 0
    output_dir = Path(args.output_dir)
    existing_mp3s = _existing_mp3s(output_dir, cfg.vocab_file_prefix)

    items: list[tuple[str, str, str, str, str]] = []
    for input_path in args.input_files:
        items.extend(load_vocabulary(input_path, args.level))
    log.info("Vocabulary items to process: %d", len(items))

    for dutch_word, article, plural, example_nl, level in items:
        if args.max_items and generated >= args.max_items:
            break
        word_with_article = f"{article} {dutch_word}".strip() if article else dutch_word
        word_part = f"{word_with_article}, {plural}" if plural else word_with_article
        text = f"{word_part}. {example_nl}" if example_nl else word_part

        filename = vocab_filename(dutch_word, level, cfg.vocab_file_prefix)
        output_path = output_dir / filename

        if not args.force:
            if db and _has_gemini_audio_vocab(db, dutch_word, level, cfg.vocab_file_prefix):
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
            wav_bytes = synthesize(client, genai_types, text, cfg.voice_vocab, cfg.vocab_system_prompt, tts_model, cfg)
            save_audio(wav_to_mp3_bytes(wav_bytes), output_path)
            existing_mp3s.add(filename)
            if not args.no_db and db:
                upsert_vocab_audio(db, dutch_word, level, filename, cfg.voice_vocab)
            generated += 1
        except Exception as exc:
            log.warning("FAIL  %s — %s: %s", filename, type(exc).__name__, exc)
            failed += 1

        time.sleep(args.delay)

    return generated, skipped, failed


def process_stories(args, client, genai_types, db, cfg: TtsConfig, tts_model: str) -> tuple[int, int, int]:
    """Returns (generated, skipped, failed) counts."""
    generated = skipped = failed = 0
    output_dir = Path(args.output_dir)
    existing_mp3s = _existing_mp3s(output_dir, cfg.story_file_prefix)

    items: list[tuple[str, str, str]] = []
    for input_path in args.input_files:
        items.extend(load_stories(input_path, args.level))
    log.info("Stories to process: %d", len(items))

    for slug, content_nl, level in items:
        if args.max_items and generated >= args.max_items:
            break
        filename = story_filename(slug, cfg.story_file_prefix)
        output_path = output_dir / filename

        if not args.force:
            if db and _has_gemini_audio_story(db, slug, cfg.story_file_prefix):
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
            wav_bytes = synthesize(client, genai_types, content_nl, cfg.voice_story, cfg.story_system_prompt, tts_model, cfg)
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


# ── batch API helpers ─────────────────────────────────────────────────────────

def _submit_batch(client, genai_types, pending: list[dict], tts_model: str):
    """
    Submit a list of pending TTS requests to the Gemini Batch API.

    Each item in *pending* must contain:
      - ``text``     : fully-prompted text (system_prompt + content)
      - ``voice``    : voice name for SpeechConfig
      - ``filename`` : output filename – stored in metadata for correlation
      - additional keys (e.g. ``dutch_word``, ``level``, ``slug``) also
        stored in metadata so results can be written to DB without rebuilding
        the original pending list.

    Returns the submitted BatchJob.
    """
    gt = genai_types
    inlined_requests = []
    for item in pending:
        # Store all fields except 'text' as string metadata
        meta = {k: str(v) for k, v in item.items() if k != "text"}
        inlined_requests.append(
            gt.InlinedRequest(
                contents=item["text"],
                metadata=meta,
                config=gt.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=gt.SpeechConfig(
                        voice_config=gt.VoiceConfig(
                            prebuilt_voice_config=gt.PrebuiltVoiceConfig(
                                voice_name=item["voice"]
                            )
                        )
                    ),
                ),
            )
        )

    log.info("BATCH submitting %d request(s) …", len(inlined_requests))
    job = client.batches.create(model=tts_model, src=inlined_requests)
    log.info("BATCH job created: %s  state=%s", job.name, job.state.name)
    return job


def _poll_batch(client, job_name: str, poll_interval: int, terminal_states: frozenset):
    """Poll *job_name* until terminal state, then return the final BatchJob."""
    job = client.batches.get(name=job_name)
    while job.state.name not in terminal_states:
        log.info(
            "BATCH %s — state=%s (checking again in %ds …)",
            job_name, job.state.name, poll_interval,
        )
        time.sleep(poll_interval)
        job = client.batches.get(name=job_name)
    log.info("BATCH %s finished — state=%s", job_name, job.state.name)
    return job


def _ingest_batch_results(job, args, db, output_dir: Path, cfg: TtsConfig) -> tuple[int, int]:
    """
    Save audio files and update the DB from a completed batch job.

    Results are correlated back to individual items via the ``metadata`` dict
    that was attached to each InlinedRequest at submission time.  The metadata
    contains at minimum ``filename`` and ``voice``; vocabulary items also carry
    ``dutch_word`` and ``level``; story items carry ``slug``.

    Returns (generated, failed).
    """
    generated = failed = 0

    responses = (job.dest.inlined_responses or []) if job.dest else []
    if not responses:
        log.warning(
            "BATCH no inlined_responses in completed job %s (state=%s)",
            job.name, job.state.name,
        )
        return 0, 0

    for ir in responses:
        meta = ir.metadata or {}
        filename = meta.get("filename", "<unknown>")

        if ir.error:
            log.warning("FAIL  %s — batch error: %s", filename, ir.error)
            failed += 1
            continue

        try:
            wav_bytes = _extract_audio_from_response(ir.response, cfg)
            mp3_bytes = wav_to_mp3_bytes(wav_bytes)
            save_audio(mp3_bytes, output_dir / filename)
            log.info("SAVED %s", filename)

            if not args.no_db and db:
                if "dutch_word" in meta:
                    upsert_vocab_audio(
                        db,
                        meta["dutch_word"],
                        meta["level"],
                        filename,
                        meta["voice"],
                    )
                elif "slug" in meta:
                    upsert_story_audio(db, meta["slug"], filename)

            generated += 1
        except Exception as exc:
            log.warning("FAIL  %s — %s: %s", filename, type(exc).__name__, exc)
            failed += 1

    return generated, failed


# ── batch processing loops ────────────────────────────────────────────────────

def process_vocabulary_batch(args, client, genai_types, db, cfg: TtsConfig, tts_model: str) -> tuple[int, int, int]:
    """Batch-mode vocabulary TTS. Returns (generated, skipped, failed)."""
    output_dir = Path(args.output_dir)
    existing_mp3s = _existing_mp3s(output_dir, cfg.vocab_file_prefix)

    items: list[tuple] = []
    for input_path in args.input_files:
        items.extend(load_vocabulary(input_path, args.level))
    log.info("Vocabulary items to process: %d", len(items))

    pending: list[dict] = []
    skipped = 0
    for dutch_word, article, plural, example_nl, level in items:
        if args.max_items and len(pending) >= args.max_items:
            break
        filename = vocab_filename(dutch_word, level, cfg.vocab_file_prefix)
        if not args.force:
            if db and _has_gemini_audio_vocab(db, dutch_word, level, cfg.vocab_file_prefix):
                log.info("SKIP  %s (gemini audio already in DB)", filename)
                skipped += 1
                continue
            if filename in existing_mp3s:
                log.info("SKIP  %s (file exists)", filename)
                skipped += 1
                continue

        word_with_article = f"{article} {dutch_word}".strip() if article else dutch_word
        word_part = f"{word_with_article}, {plural}" if plural else word_with_article
        text = f"{word_part}. {example_nl}" if example_nl else word_part
        pending.append({
            "text": f"{cfg.vocab_system_prompt}\n\n{text}",
            "voice": cfg.voice_vocab,
            "filename": filename,
            "dutch_word": dutch_word,
            "level": level,
        })

    if args.dry_run:
        for p in pending:
            log.info("DRY   %s", p["filename"])
        log.info("DRY   Would submit %d item(s) as a single batch job", len(pending))
        return len(pending), skipped, 0

    if not pending:
        log.info("Nothing to submit — all items already generated.")
        return 0, skipped, 0

    job = _submit_batch(client, genai_types, pending, tts_model)
    job = _poll_batch(client, job.name, args.poll_interval, cfg.terminal_job_states)
    gen, fail = _ingest_batch_results(job, args, db, output_dir, cfg)
    return gen, skipped, fail


def process_stories_batch(args, client, genai_types, db, cfg: TtsConfig, tts_model: str) -> tuple[int, int, int]:
    """Batch-mode story TTS. Returns (generated, skipped, failed)."""
    output_dir = Path(args.output_dir)
    existing_mp3s = _existing_mp3s(output_dir, cfg.story_file_prefix)

    items: list[tuple] = []
    for input_path in args.input_files:
        items.extend(load_stories(input_path, args.level))
    log.info("Stories to process: %d", len(items))

    pending: list[dict] = []
    skipped = 0
    for slug, content_nl, level in items:
        if args.max_items and len(pending) >= args.max_items:
            break
        filename = story_filename(slug, cfg.story_file_prefix)
        if not args.force:
            if db and _has_gemini_audio_story(db, slug, cfg.story_file_prefix):
                log.info("SKIP  %s (gemini audio already in DB)", filename)
                skipped += 1
                continue
            if filename in existing_mp3s:
                log.info("SKIP  %s (file exists)", filename)
                skipped += 1
                continue

        pending.append({
            "text": f"{cfg.story_system_prompt}\n\n{content_nl}",
            "voice": cfg.voice_story,
            "filename": filename,
            "slug": slug,
        })

    if args.dry_run:
        for p in pending:
            log.info("DRY   %s  ← slug=%r", p["filename"], p.get("slug"))
        log.info("DRY   Would submit %d item(s) as a single batch job", len(pending))
        return len(pending), skipped, 0

    if not pending:
        log.info("Nothing to submit — all items already generated.")
        return 0, skipped, 0

    job = _submit_batch(client, genai_types, pending, tts_model)
    job = _poll_batch(client, job.name, args.poll_interval, cfg.terminal_job_states)
    gen, fail = _ingest_batch_results(job, args, db, output_dir, cfg)
    return gen, skipped, fail


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    default_config_path = Path(__file__).parent / "populate_config.json"
    parser = argparse.ArgumentParser(
        description="Generate Dutch TTS audio via Gemini and update the DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path,
        help=f"Path to populate_config.json (default: {default_config_path})",
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
        default=None,
        help="Directory to write audio files (default: settings.AUDIO_DIR)",
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
        default=10.0,
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
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Submit all pending items as a single Gemini Batch API job (cheaper, async)",
    )
    parser.add_argument(
        "--job-name",
        default=None,
        metavar="NAME",
        help=(
            "Resume polling an already-submitted batch job and ingest its results. "
            "Example: batches/abc123.  --type is still required to locate the output dir."
        ),
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Seconds between batch job status polls (default: 60)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = _load_tts_config(args.config)

    if args.output_dir is None:
        args.output_dir = str(settings.AUDIO_DIR)

    tts_model: str | None = None

    # --job-name: resume polling an already-submitted batch; input files not needed
    if args.job_name:
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        client, genai_types, tts_model = _build_client()
        db = None if args.no_db else SessionLocal()
        try:
            job = _poll_batch(client, args.job_name, args.poll_interval, cfg.terminal_job_states)
            gen, fail = _ingest_batch_results(job, args, db, Path(args.output_dir), cfg)
        finally:
            if db:
                db.close()
        log.info("Done. generated=%d  failed=%d", gen, fail)
        if fail:
            sys.exit(1)
        return

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

    if args.dry_run:
        client = genai_types = None
        tts_model = ""
    else:
        client, genai_types, tts_model = _build_client()

    db = None if args.no_db else SessionLocal()

    try:
        if args.batch:
            if args.content_type == "vocabulary":
                gen, skip, fail = process_vocabulary_batch(args, client, genai_types, db, cfg, tts_model)
            else:
                gen, skip, fail = process_stories_batch(args, client, genai_types, db, cfg, tts_model)
        else:
            if args.content_type == "vocabulary":
                gen, skip, fail = process_vocabulary(args, client, genai_types, db, cfg, tts_model)
            else:
                gen, skip, fail = process_stories(args, client, genai_types, db, cfg, tts_model)
    finally:
        if db:
            db.close()

    log.info("Done. generated=%d  skipped=%d  failed=%d", gen, skip, fail)
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
