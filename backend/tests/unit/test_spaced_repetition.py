"""Unit tests for the FSRS spaced-repetition service."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, SRCard, User, VocabularyItem
from app.services import spaced_repetition

_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_ENGINE)


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    Base.metadata.create_all(bind=_ENGINE)
    yield
    Base.metadata.drop_all(bind=_ENGINE)


@pytest.fixture()
def session():
    conn = _ENGINE.connect()
    tx = conn.begin()
    s = _Session(bind=conn)
    yield s
    s.close()
    tx.rollback()
    conn.close()


@pytest.fixture()
def user_and_vocab(session):
    user = User(username="tester", xp_total=0, streak_days=0)
    vocab = VocabularyItem(
        dutch_word="hond",
        spanish="perro",
        level="a0",
        theme="animales",
    )
    session.add_all([user, vocab])
    session.commit()
    session.refresh(user)
    session.refresh(vocab)
    return user, vocab


class TestGetOrCreateCard:
    def test_creates_new_card(self, session, user_and_vocab):
        user, vocab = user_and_vocab
        card = spaced_repetition.get_or_create_card(session, user.id, vocab.id)
        assert card.id is not None
        assert card.user_id == user.id
        assert card.vocab_item_id == vocab.id

    def test_idempotent_second_call(self, session, user_and_vocab):
        user, vocab = user_and_vocab
        card1 = spaced_repetition.get_or_create_card(session, user.id, vocab.id)
        card2 = spaced_repetition.get_or_create_card(session, user.id, vocab.id)
        assert card1.id == card2.id


class TestReviewCard:
    @pytest.mark.parametrize("rating, expected_xp", [(1, 2), (2, 5), (3, 10), (4, 15)])
    def test_xp_awarded_per_rating(self, session, user_and_vocab, rating, expected_xp):
        user, vocab = user_and_vocab
        card = spaced_repetition.get_or_create_card(session, user.id, vocab.id)
        _, xp = spaced_repetition.review_card(session, card.id, rating, user.id)
        assert xp == expected_xp

    def test_reps_incremented(self, session, user_and_vocab):
        user, vocab = user_and_vocab
        card = spaced_repetition.get_or_create_card(session, user.id, vocab.id)
        spaced_repetition.review_card(session, card.id, 3, user.id)
        session.refresh(card)
        assert card.reps == 1

    def test_raises_for_missing_card(self, session, user_and_vocab):
        user, _ = user_and_vocab
        with pytest.raises(ValueError, match="not found"):
            spaced_repetition.review_card(session, card_id=99999, rating_int=3, user_id=user.id)

    def test_xp_accumulates_on_user(self, session, user_and_vocab):
        user, vocab = user_and_vocab
        card = spaced_repetition.get_or_create_card(session, user.id, vocab.id)
        spaced_repetition.review_card(session, card.id, 4, user.id)  # +15 XP
        session.refresh(user)
        assert user.xp_total == 15


class TestGetDueCards:
    def test_returns_overdue_cards(self, session, user_and_vocab):
        user, vocab = user_and_vocab
        past = datetime.now(timezone.utc) - timedelta(days=1)
        card = SRCard(
            user_id=user.id,
            vocab_item_id=vocab.id,
            stability=1.0,
            difficulty=5.0,
            state=0,
            due_date=past,
        )
        session.add(card)
        session.commit()
        due = spaced_repetition.get_due_cards(session, user.id)
        assert any(c.id == card.id for c in due)

    def test_does_not_return_future_cards(self, session, user_and_vocab):
        user, vocab = user_and_vocab
        future = datetime.now(timezone.utc) + timedelta(days=10)
        card = SRCard(
            user_id=user.id,
            vocab_item_id=vocab.id,
            stability=1.0,
            difficulty=5.0,
            state=0,
            due_date=future,
        )
        session.add(card)
        session.commit()
        due = spaced_repetition.get_due_cards(session, user.id)
        assert not any(c.id == card.id for c in due)


class TestOrmToCardZeroDivision:
    """Regression test for FSRS ZeroDivisionError when stability=0 and state>0."""

    def test_stability_zero_reviewed_card_does_not_crash(self, session, user_and_vocab):
        user, vocab = user_and_vocab
        # Simulate a reviewed card that somehow has stability=0
        card = SRCard(
            user_id=user.id,
            vocab_item_id=vocab.id,
            stability=0.0,
            difficulty=5.0,
            state=2,  # Review state (> New)
            due_date=datetime.now(timezone.utc) - timedelta(hours=1),
            reps=1,
        )
        session.add(card)
        session.commit()

        # Should not raise ZeroDivisionError
        updated, _ = spaced_repetition.review_card(session, card.id, 3, user.id)
        assert updated.stability > 0
