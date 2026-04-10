"""Integration tests for exercise endpoints."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from app.db.models import VocabularyItem


def _seed_vocabulary(db, level="a0", count=10):
    items = []
    for i in range(count):
        item = VocabularyItem(
            dutch_word=f"woord{i}",
            spanish=f"palabra{i}",
            article="de",
            level=level,
            theme="animales",
            example_nl=f"De woord{i} is een woord met meer dan drie woorden.",
            example_es=f"La palabra{i} es una palabra.",
        )
        db.add(item)
        items.append(item)
    db.commit()
    return items


class TestListenChooseExercise:
    def test_returns_four_options(self, client, db):
        _seed_vocabulary(db)
        resp = client.get("/api/v1/exercises/listen-choose?level=a0")
        assert resp.status_code == 200
        data = resp.json()
        assert "options" in data
        assert len(data["options"]) == 4

    def test_correct_id_is_among_options(self, client, db):
        _seed_vocabulary(db)
        resp = client.get("/api/v1/exercises/listen-choose?level=a0")
        assert resp.status_code == 200
        data = resp.json()
        option_ids = [o["id"] for o in data["options"]]
        assert data["correct_id"] in option_ids

    def test_invalid_level_returns_422(self, client, db):
        resp = client.get("/api/v1/exercises/listen-choose?level=z9")
        assert resp.status_code == 422

    def test_insufficient_items_returns_error(self, client, db):
        # Only 2 items — not enough for 4 options
        _seed_vocabulary(db, level="b2", count=2)
        resp = client.get("/api/v1/exercises/listen-choose?level=b2")
        assert resp.status_code == 200
        assert "error" in resp.json()


class TestWordMatchExercise:
    def test_returns_pairs(self, client, db):
        _seed_vocabulary(db)
        resp = client.get("/api/v1/exercises/word-match?level=a0&count=6")
        assert resp.status_code == 200
        data = resp.json()
        assert "pairs" in data
        assert len(data["pairs"]) <= 6

    def test_pair_has_required_fields(self, client, db):
        _seed_vocabulary(db)
        resp = client.get("/api/v1/exercises/word-match?level=a0&count=3")
        assert resp.status_code == 200
        for pair in resp.json()["pairs"]:
            assert "dutch" in pair
            assert "spanish" in pair

    def test_invalid_level_returns_422(self, client, db):
        resp = client.get("/api/v1/exercises/word-match?level=invalid")
        assert resp.status_code == 422


class TestFillBlankExercise:
    def test_returns_sentence_with_blank(self, client, db):
        _seed_vocabulary(db)
        resp = client.get("/api/v1/exercises/fill-blank?level=a0")
        assert resp.status_code == 200
        data = resp.json()
        if "error" not in data:
            assert "___" in data["sentence_with_blank"]
            assert "correct_id" in data
            assert len(data["options"]) >= 1

    def test_invalid_level_returns_422(self, client, db):
        resp = client.get("/api/v1/exercises/fill-blank?level=xx")
        assert resp.status_code == 422


class TestUnscrambleExercise:
    def test_returns_shuffled_words(self, client, db):
        _seed_vocabulary(db)
        resp = client.get("/api/v1/exercises/unscramble?level=a0")
        assert resp.status_code == 200
        data = resp.json()
        if "error" not in data:
            assert "shuffled_words" in data
            assert "correct_sentence" in data
            assert isinstance(data["shuffled_words"], list)

    def test_shuffled_words_contain_same_tokens(self, client, db):
        _seed_vocabulary(db)
        resp = client.get("/api/v1/exercises/unscramble?level=a0")
        assert resp.status_code == 200
        data = resp.json()
        if "error" not in data:
            correct_words = set(data["correct_sentence"].rstrip(".").split())
            shuffled_words = set(data["shuffled_words"])
            assert correct_words == shuffled_words

    def test_invalid_level_returns_422(self, client, db):
        resp = client.get("/api/v1/exercises/unscramble?level=zz")
        assert resp.status_code == 422
