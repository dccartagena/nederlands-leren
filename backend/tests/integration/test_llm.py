"""Integration tests for LLM endpoints — all LLM calls are mocked."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
import respx
import httpx
from app.core.config import settings

OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"


def _ollama_ok(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"content": content}})


class TestExplainEndpoint:
    @respx.mock
    def test_explain_returns_explanation(self, client, db):
        respx.post(OLLAMA_URL).mock(return_value=_ollama_ok("De hond is een zoogdier."))
        resp = client.post("/api/v1/llm/explain", json={"word_or_phrase": "hond"})
        assert resp.status_code == 200
        assert "explanation" in resp.json()

    def test_explain_missing_body_returns_422(self, client, db):
        resp = client.post("/api/v1/llm/explain", json={})
        assert resp.status_code == 422

    def test_explain_oversized_word_returns_422(self, client, db):
        resp = client.post("/api/v1/llm/explain", json={"word_or_phrase": "x" * 201})
        assert resp.status_code == 422

    @respx.mock
    def test_explain_with_context_sentence(self, client, db):
        respx.post(OLLAMA_URL).mock(return_value=_ollama_ok("Explanation with context."))
        resp = client.post(
            "/api/v1/llm/explain",
            json={"word_or_phrase": "lopen", "context_sentence": "Ik loop naar school."},
        )
        assert resp.status_code == 200


class TestFeedbackEndpoint:
    @respx.mock
    def test_feedback_returns_feedback(self, client, db):
        respx.post(OLLAMA_URL).mock(return_value=_ollama_ok("El correcto es 'hond' porque..."))
        resp = client.post(
            "/api/v1/llm/feedback",
            json={
                "question": "¿Cómo se dice perro?",
                "correct_answer": "hond",
                "user_answer": "kat",
            },
        )
        assert resp.status_code == 200
        assert "feedback" in resp.json()

    def test_feedback_missing_fields_returns_422(self, client, db):
        resp = client.post("/api/v1/llm/feedback", json={"question": "test"})
        assert resp.status_code == 422

    def test_feedback_oversized_answer_returns_422(self, client, db):
        resp = client.post(
            "/api/v1/llm/feedback",
            json={
                "question": "test",
                "correct_answer": "a" * 201,
                "user_answer": "b",
            },
        )
        assert resp.status_code == 422


class TestChatEndpoint:
    @respx.mock
    def test_chat_returns_reply(self, client, db):
        respx.post(OLLAMA_URL).mock(return_value=_ollama_ok("Hallo! Hoe gaat het?"))
        resp = client.post(
            "/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": "Hallo!"}]},
        )
        assert resp.status_code == 200
        assert "reply" in resp.json()

    def test_chat_invalid_role_returns_422(self, client, db):
        resp = client.post(
            "/api/v1/llm/chat",
            json={"messages": [{"role": "hacker", "content": "inject"}]},
        )
        assert resp.status_code == 422

    def test_chat_invalid_provider_returns_422(self, client, db):
        resp = client.post(
            "/api/v1/llm/chat",
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "provider": "unknown_provider",
            },
        )
        assert resp.status_code == 422

    def test_chat_oversized_content_returns_422(self, client, db):
        resp = client.post(
            "/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": "x" * 4001}]},
        )
        assert resp.status_code == 422
