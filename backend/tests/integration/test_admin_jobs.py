"""Integration tests for the background scheduler, jobs, and admin endpoints."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import json
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.db.models import JobRun, User, VocabularyItem
from app.services import scheduler
from app.services.scheduler import JOB_REGISTRY, is_due, run_job


def _make_data_dir(tmp_path):
    """Minimal data/ layout the seed and backup jobs can work against."""
    (tmp_path / "vocabulary").mkdir()
    (tmp_path / "grammar").mkdir()
    (tmp_path / "stories").mkdir()
    (tmp_path / "vocabulary" / "a0_words.json").write_text(
        json.dumps([
            {"dutch_word": "hond", "spanish": "perro", "level": "a0", "theme": "animales"},
            {"dutch_word": "kat", "spanish": "gato", "level": "a0", "theme": "animales"},
        ])
    )
    return tmp_path


class TestScheduler:
    def test_registry_has_all_jobs(self):
        assert set(JOB_REGISTRY) == {
            "seed_content",
            "backup_progress",
            "audio_gapfill",
            "fsrs_optimize",
            "content_refresh",
        }

    def test_job_due_when_never_run(self, db):
        assert is_due(db, JOB_REGISTRY["backup_progress"]) is True

    def test_job_not_due_within_interval(self, db):
        db.add(JobRun(job_name="backup_progress", last_run_at=datetime.now(UTC)))
        db.commit()
        assert is_due(db, JOB_REGISTRY["backup_progress"]) is False

    def test_job_due_again_after_interval(self, db):
        db.add(
            JobRun(
                job_name="backup_progress",
                last_run_at=datetime.now(UTC) - timedelta(hours=25),
            )
        )
        db.commit()
        assert is_due(db, JOB_REGISTRY["backup_progress"]) is True

    def test_run_job_records_error_without_killing_caller(self, db, monkeypatch):
        monkeypatch.setitem(
            scheduler.JOB_REGISTRY,
            "backup_progress",
            scheduler.JobSpec(
                "backup_progress",
                lambda _db: (_ for _ in ()).throw(RuntimeError("boom")),
                timedelta(hours=24),
                lambda: True,
                "test",
            ),
        )
        row = run_job(db, "backup_progress", force=True)
        assert row.last_status == "error"
        assert "boom" in row.detail


class TestSeedJob:
    def test_seed_is_idempotent(self, db, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "DATA_DIR", _make_data_dir(tmp_path))
        first = run_job(db, "seed_content", force=True)
        assert first.last_status == "ok"
        assert "2 vocab" in first.detail
        second = run_job(db, "seed_content", force=True)
        assert "0 vocab" in second.detail
        assert db.query(VocabularyItem).count() == 2


class TestBackupJob:
    def test_backup_writes_dated_file(self, db, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
        db.add(User(id=1, username="learner", xp_total=50))
        db.commit()
        row = run_job(db, "backup_progress", force=True)
        assert row.last_status == "ok"
        backups = list((tmp_path / "backups").glob("progress-*.json"))
        assert len(backups) == 1
        payload = json.loads(backups[0].read_text())
        assert payload["user"]["xp_total"] == 50

    def test_backup_prunes_old_files(self, db, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
        monkeypatch.setattr(settings, "BACKUP_RETENTION", 2)
        db.add(User(id=1, username="learner"))
        db.commit()
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()
        for day in ("2026-01-01", "2026-01-02", "2026-01-03"):
            (backups_dir / f"progress-{day}.json").write_text("{}")
        run_job(db, "backup_progress", force=True)
        remaining = sorted(p.name for p in backups_dir.glob("progress-*.json"))
        assert len(remaining) == 2
        assert "progress-2026-01-01.json" not in remaining

    def test_backup_skipped_without_user(self, db, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
        row = run_job(db, "backup_progress", force=True)
        assert row.last_status == "skipped"


class TestAudioGapfillJob:
    def test_generates_only_missing(self, db, monkeypatch):
        from app.services import audio_service, jobs

        db.add_all([
            VocabularyItem(dutch_word="hond", spanish="perro", level="a0", theme="t"),
            VocabularyItem(dutch_word="kat", spanish="gato", level="a0", theme="t"),
        ])
        db.commit()

        monkeypatch.setattr(
            audio_service,
            "resolve_vocab_audio",
            lambda word, level, article=None: "exists" if word == "hond" else None,
        )
        generated = []
        monkeypatch.setattr(
            audio_service,
            "ensure_vocab_audio",
            lambda word, level, article=None: generated.append(word),
        )
        detail = jobs.audio_gapfill(db)
        assert generated == ["kat"]
        assert "1 generated" in detail


class TestOptimizerJob:
    def test_skipped_below_threshold(self, db):
        row = run_job(db, "fsrs_optimize", force=True)
        assert row.last_status == "skipped"
        assert "/1000" in row.detail


class TestAdminEndpoints:
    def test_list_jobs(self, client, db):
        resp = client.get("/api/v1/admin/jobs")
        assert resp.status_code == 200
        jobs_list = resp.json()
        assert len(jobs_list) == 5
        names = {j["name"] for j in jobs_list}
        assert "backup_progress" in names
        assert all("description" in j for j in jobs_list)

    def test_trigger_unknown_job_404(self, client, db):
        resp = client.post("/api/v1/admin/jobs/nope/run")
        assert resp.status_code == 404

    def test_trigger_job_runs_and_reports(self, client, db, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
        client.get("/api/v1/progress/user")  # ensure user
        resp = client.post("/api/v1/admin/jobs/backup_progress/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "backup written" in data["detail"]


class TestVocabAudioEndpoint:
    def test_serves_resolved_audio(self, client, db, tmp_path, monkeypatch):
        from app.services import audio_service

        item = VocabularyItem(dutch_word="hond", spanish="perro", level="a0", theme="t")
        db.add(item)
        db.commit()
        fake = tmp_path / "hond.mp3"
        fake.write_bytes(b"ID3fakeaudio")
        monkeypatch.setattr(
            audio_service, "ensure_vocab_audio", lambda word, level, article=None: fake
        )
        resp = client.get(f"/api/v1/vocabulary/{item.id}/audio")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("audio/")

    def test_missing_item_404(self, client, db):
        resp = client.get("/api/v1/vocabulary/99999/audio")
        assert resp.status_code == 404

    def test_synthesis_failure_returns_503(self, client, db, monkeypatch):
        from app.services import audio_service

        item = VocabularyItem(dutch_word="kat", spanish="gato", level="a0", theme="t")
        db.add(item)
        db.commit()

        def _fail(word, level, article=None):
            raise RuntimeError("offline")

        monkeypatch.setattr(audio_service, "ensure_vocab_audio", _fail)
        resp = client.get(f"/api/v1/vocabulary/{item.id}/audio")
        assert resp.status_code == 503
