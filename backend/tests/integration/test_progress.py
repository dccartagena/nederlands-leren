"""Integration tests for progress / FSRS endpoints."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from datetime import date, datetime, timedelta, timezone
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

    def test_combo_multiplies_xp(self, client, db):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        card_id = client.post(f"/api/v1/progress/enroll/{item.id}").json()["card_id"]
        resp = client.post(
            "/api/v1/progress/review", json={"card_id": card_id, "rating": 3, "combo": True}
        )
        assert resp.status_code == 200
        # Base XP for "Good" is 10; combo applies ×1.5
        assert resp.json()["xp_earned"] == 15


class TestMasteryStats:
    def test_stats_empty_user(self, client, db):
        resp = client.get("/api/v1/progress/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mastered_words"] == 0
        assert data["enrolled_words"] == 0
        assert data["stories_completed"] == 0

    def test_stats_counts_mastered_cards(self, client, db):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        db.add(
            SRCard(
                user_id=user.id,
                vocab_item_id=item.id,
                stability=30.0,  # above the 21-day mastery threshold
                difficulty=5.0,
                state=2,
                due_date=datetime.now(timezone.utc),
            )
        )
        db.commit()
        data = client.get("/api/v1/progress/stats").json()
        assert data["mastered_words"] == 1
        assert data["enrolled_words"] == 1
        assert data["review_words"] == 1


class TestDailyQuests:
    def test_returns_four_quests(self, client, db):
        resp = client.get("/api/v1/progress/quests")
        assert resp.status_code == 200
        quests = resp.json()
        assert len(quests) == 4
        assert all(q["progress"] == 0 and q["done"] is False for q in quests)

    def test_review_advances_review_quest(self, client, db):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        card_id = client.post(f"/api/v1/progress/enroll/{item.id}").json()["card_id"]
        client.post("/api/v1/progress/review", json={"card_id": card_id, "rating": 3})
        quests = client.get("/api/v1/progress/quests").json()
        review_quest = next(q for q in quests if q["id"].startswith("review_"))
        assert review_quest["progress"] == 1


class TestReviewLog:
    def test_review_writes_log_row(self, client, db):
        from app.db.models import ReviewLog

        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        card_id = client.post(f"/api/v1/progress/enroll/{item.id}").json()["card_id"]
        client.post("/api/v1/progress/review", json={"card_id": card_id, "rating": 3})

        logs = db.query(ReviewLog).filter_by(user_id=1, card_id=card_id).all()
        assert len(logs) == 1
        assert logs[0].rating == 3
        assert logs[0].state_after >= 1

    def test_export_includes_review_logs(self, client, db):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        card_id = client.post(f"/api/v1/progress/enroll/{item.id}").json()["card_id"]
        client.post("/api/v1/progress/review", json={"card_id": card_id, "rating": 4})

        payload = client.get("/api/v1/progress/export").json()
        assert len(payload["review_logs"]) == 1
        assert payload["review_logs"][0]["rating"] == 4


class TestNewCardCap:
    def test_due_cards_caps_new_cards_per_day(self, client, db):
        from app.services.spaced_repetition import NEW_CARDS_PER_DAY

        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        for i in range(NEW_CARDS_PER_DAY + 5):
            item = VocabularyItem(
                dutch_word=f"woord{i}", spanish=f"palabra{i}", level="a0", theme="test"
            )
            db.add(item)
            db.flush()
            db.add(
                SRCard(
                    user_id=user.id,
                    vocab_item_id=item.id,
                    stability=0.0,
                    difficulty=5.0,
                    state=1,
                    reps=0,  # never reviewed → counts against the daily cap
                    due_date=past,
                )
            )
        db.commit()
        resp = client.get("/api/v1/progress/due", params={"limit": 50})
        assert resp.status_code == 200
        assert len(resp.json()) == NEW_CARDS_PER_DAY

    def test_learning_cards_not_capped(self, client, db):
        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        for i in range(20):
            item = VocabularyItem(
                dutch_word=f"leer{i}", spanish=f"aprende{i}", level="a0", theme="test"
            )
            db.add(item)
            db.flush()
            db.add(
                SRCard(
                    user_id=user.id,
                    vocab_item_id=item.id,
                    stability=1.0,
                    difficulty=5.0,
                    state=2,
                    reps=3,  # already introduced — never capped
                    due_date=past,
                )
            )
        db.commit()
        resp = client.get("/api/v1/progress/due", params={"limit": 50})
        assert len(resp.json()) == 20


class TestSessionComplete:
    def test_awards_xp_and_logs_session(self, client, db):
        resp = client.post(
            "/api/v1/progress/session-complete",
            json={"game_type": "escribir", "correct_count": 4, "total_count": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["xp_earned"] == 20  # 4 correct × 5 XP, no perfect bonus
        user_data = client.get("/api/v1/progress/user").json()
        assert user_data["xp_total"] == 20

    def test_perfect_round_gets_bonus(self, client, db):
        resp = client.post(
            "/api/v1/progress/session-complete",
            json={"game_type": "hablar", "correct_count": 5, "total_count": 5},
        )
        assert resp.json()["xp_earned"] == 35  # 25 + 10 perfect bonus

    def test_output_session_advances_output_quest(self, client, db):
        client.post(
            "/api/v1/progress/session-complete",
            json={"game_type": "escribir", "correct_count": 3, "total_count": 5},
        )
        quests = client.get("/api/v1/progress/quests").json()
        output_quest = next(q for q in quests if q["id"].startswith("output_"))
        assert output_quest["progress"] == 5  # exercises completed, not correct


class TestStrands:
    def test_strand_balance_buckets_sessions(self, client, db):
        client.post(
            "/api/v1/progress/session-complete",
            json={"game_type": "escribir", "correct_count": 5, "total_count": 5},
        )
        client.post(
            "/api/v1/progress/story-complete",
            json={"story_slug": "het-huis", "correct_count": 3, "total_questions": 3},
        )
        strands = {s["strand"]: s for s in client.get("/api/v1/progress/strands").json()}
        assert set(strands) == {"input", "output", "study", "fluency"}
        assert strands["output"]["sessions"] == 1
        assert strands["input"]["sessions"] == 1
        assert strands["study"]["sessions"] == 0


class TestStreakFreeze:
    def _review(self, client, db):
        item = _seed_vocab(db)
        client.get("/api/v1/progress/user")
        card_id = client.post(f"/api/v1/progress/enroll/{item.id}").json()["card_id"]
        client.post("/api/v1/progress/review", json={"card_id": card_id, "rating": 3})

    def test_freeze_bridges_one_missed_day(self, client, db):
        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        user.streak_days = 7
        user.last_activity_date = (date.today() - timedelta(days=2)).isoformat()
        user.settings_json = {"streak_freezes": 1}
        db.commit()
        self._review(client, db)
        data = client.get("/api/v1/progress/user").json()
        assert data["streak_days"] == 8
        assert data["settings_json"]["streak_freezes"] == 0

    def test_streak_resets_without_freeze(self, client, db):
        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        user.streak_days = 7
        user.last_activity_date = (date.today() - timedelta(days=2)).isoformat()
        user.settings_json = {"streak_freezes": 0}
        db.commit()
        self._review(client, db)
        data = client.get("/api/v1/progress/user").json()
        assert data["streak_days"] == 1

    def test_freeze_earned_at_streak_of_seven(self, client, db):
        client.get("/api/v1/progress/user")
        user = db.query(User).filter_by(id=1).first()
        user.streak_days = 6
        user.last_activity_date = (date.today() - timedelta(days=1)).isoformat()
        db.commit()
        self._review(client, db)
        data = client.get("/api/v1/progress/user").json()
        assert data["streak_days"] == 7
        assert data["settings_json"]["streak_freezes"] == 1
