"""Integration tests for progress / FSRS endpoints."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from datetime import datetime, timedelta, timezone
import pytest
from app.db.models import VocabularyItem, SRCard, User


def _seed_vocab(db, level="a0"):
    item = VocabularyItem(
        dutch_word="hond",
        spanish="perro",
        level=level,
        theme="animales",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


class TestGetUser:
    def test_creates_user_on_first_call(self, client, db):
        resp = client.get("/api/v1/progress/user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["username"] == "learner"
        assert data["xp_total"] == 0

    def test_idempotent(self, client, db):
        resp1 = client.get("/api/v1/progress/user")
        resp2 = client.get("/api/v1/progress/user")
        assert resp1.json()["id"] == resp2.json()["id"]


class TestEnrollCard:
    def test_enroll_creates_sr_card(self, client, db):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")  # ensure user exists
        resp = client.post(f"/api/v1/progress/enroll/{item.id}")
        assert resp.status_code == 200
        assert resp.json()["card_id"] is not None

    def test_enroll_unknown_item_returns_404(self, client, db):
        client.get("/api/v1/progress/user")
        resp = client.post("/api/v1/progress/enroll/99999")
        assert resp.status_code == 404


class TestDueCards:
    def test_due_cards_returns_overdue(self, client, db):
        item = _seed_vocab(db)
        # Ensure user exists
        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        past = datetime.now(timezone.utc) - timedelta(days=1)
        card = SRCard(
            user_id=user.id,
            vocab_item_id=item.id,
            stability=1.0,
            difficulty=5.0,
            state=0,
            due_date=past,
        )
        db.add(card)
        db.commit()
        resp = client.get("/api/v1/progress/due")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert card.id in ids

    def test_due_cards_excludes_future(self, client, db):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        future = datetime.now(timezone.utc) + timedelta(days=10)
        card = SRCard(
            user_id=user.id,
            vocab_item_id=item.id,
            stability=1.0,
            difficulty=5.0,
            state=0,
            due_date=future,
        )
        db.add(card)
        db.commit()
        resp = client.get("/api/v1/progress/due")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert card.id not in ids


class TestReview:
    @pytest.mark.parametrize("rating", [1, 2, 3, 4])
    def test_review_all_valid_ratings(self, client, db, rating):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        enroll_resp = client.post(f"/api/v1/progress/enroll/{item.id}")
        card_id = enroll_resp.json()["card_id"]
        resp = client.post("/api/v1/progress/review", json={"card_id": card_id, "rating": rating})
        assert resp.status_code == 200
        data = resp.json()
        assert data["card_id"] == card_id
        assert data["xp_earned"] > 0

    def test_review_invalid_rating_returns_422(self, client, db):
        resp = client.post("/api/v1/progress/review", json={"card_id": 1, "rating": 5})
        assert resp.status_code == 422

    def test_review_missing_card_returns_error(self, client, db):
        client.get("/api/v1/progress/user")
        resp = client.post("/api/v1/progress/review", json={"card_id": 99999, "rating": 3})
        assert resp.status_code in (400, 404, 422, 500)
