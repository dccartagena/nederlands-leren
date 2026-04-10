"""Integration tests for vocabulary, grammar, and stories endpoints."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from app.db.models import VocabularyItem, GrammarTopic, Story


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed_vocab(db, level="a0", theme="animales", count=3):
    items = []
    for i in range(count):
        item = VocabularyItem(
            dutch_word=f"woord{i}",
            spanish=f"palabra{i}",
            level=level,
            theme=theme,
        )
        db.add(item)
        items.append(item)
    db.commit()
    return items


def _seed_grammar(db, level="a0", slug="de-het"):
    topic = GrammarTopic(
        slug=slug,
        name_nl="De en het",
        name_es="Los artículos",
        level=level,
        description_es="Los sustantivos en neerlandés llevan 'de' o 'het'.",
    )
    db.add(topic)
    db.commit()
    return topic


def _seed_story(db, level="a0", slug="first-story"):
    story = Story(
        slug=slug,
        title_nl="Het huis",
        title_es="La casa",
        level=level,
        content_nl="Er was een huis.",
        content_es="Había una casa.",
    )
    db.add(story)
    db.commit()
    return story


# ── Vocabulary ────────────────────────────────────────────────────────────────

class TestVocabularyList:
    def test_returns_all_items(self, client, db):
        _seed_vocab(db, count=3)
        resp = client.get("/api/v1/vocabulary/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    def test_filter_by_level(self, client, db):
        _seed_vocab(db, level="a0")
        _seed_vocab(db, level="a1")
        resp = client.get("/api/v1/vocabulary/?level=a0")
        assert resp.status_code == 200
        for item in resp.json():
            assert item["level"] == "a0"

    def test_filter_by_theme(self, client, db):
        _seed_vocab(db, theme="animales")
        _seed_vocab(db, theme="ciudad")
        resp = client.get("/api/v1/vocabulary/?theme=animales")
        assert resp.status_code == 200
        for item in resp.json():
            assert item["theme"] == "animales"

    def test_limit_parameter(self, client, db):
        _seed_vocab(db, count=5)
        resp = client.get("/api/v1/vocabulary/?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    def test_offset_parameter(self, client, db):
        items = _seed_vocab(db, count=4)
        resp_full = client.get("/api/v1/vocabulary/?limit=4")
        resp_offset = client.get("/api/v1/vocabulary/?limit=4&offset=2")
        full_ids = [i["id"] for i in resp_full.json()]
        offset_ids = [i["id"] for i in resp_offset.json()]
        assert offset_ids == full_ids[2:]

    def test_invalid_level_returns_422(self, client, db):
        resp = client.get("/api/v1/vocabulary/?level=zz")
        assert resp.status_code == 422


class TestVocabularyGet:
    def test_get_existing_item(self, client, db):
        items = _seed_vocab(db, count=1)
        resp = client.get(f"/api/v1/vocabulary/{items[0].id}")
        assert resp.status_code == 200
        assert resp.json()["dutch_word"] == items[0].dutch_word

    def test_get_nonexistent_returns_404(self, client, db):
        resp = client.get("/api/v1/vocabulary/99999")
        assert resp.status_code == 404


# ── Grammar ──────────────────────────────────────────────────────────────────

class TestGrammarList:
    def test_returns_all_topics(self, client, db):
        _seed_grammar(db, slug="de-het")
        _seed_grammar(db, slug="werkwoorden", level="a1")
        resp = client.get("/api/v1/grammar/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_filter_by_level(self, client, db):
        _seed_grammar(db, level="a0", slug="articles-a0")
        _seed_grammar(db, level="a1", slug="verbs-a1")
        resp = client.get("/api/v1/grammar/?level=a0")
        assert resp.status_code == 200
        for t in resp.json():
            assert t["level"] == "a0"


class TestGrammarGet:
    def test_get_by_slug(self, client, db):
        _seed_grammar(db, slug="my-slug")
        resp = client.get("/api/v1/grammar/my-slug")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "my-slug"

    def test_unknown_slug_returns_404(self, client, db):
        resp = client.get("/api/v1/grammar/does-not-exist")
        assert resp.status_code == 404


# ── Stories ───────────────────────────────────────────────────────────────────

class TestStoriesList:
    def test_returns_all_stories(self, client, db):
        _seed_story(db, slug="s1")
        _seed_story(db, slug="s2")
        resp = client.get("/api/v1/stories/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_filter_by_level(self, client, db):
        _seed_story(db, level="a0", slug="s-a0")
        _seed_story(db, level="a1", slug="s-a1")
        resp = client.get("/api/v1/stories/?level=a0")
        assert resp.status_code == 200
        for s in resp.json():
            assert s["level"] == "a0"


class TestStoryGet:
    def test_get_by_slug(self, client, db):
        _seed_story(db, slug="amazing-story")
        resp = client.get("/api/v1/stories/amazing-story")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "amazing-story"

    def test_unknown_slug_returns_404(self, client, db):
        resp = client.get("/api/v1/stories/no-such-story")
        assert resp.status_code == 404
