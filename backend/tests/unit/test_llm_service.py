"""Unit tests for llm_service — primary/fallback chain, helpers (mocked with respx)."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import json
import pytest
import respx
import httpx
from unittest.mock import AsyncMock, patch

from app.services import llm_service
from app.core.config import settings


OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"
MOCK_REPLY = "De hond is een dier. (El perro es un animal.)"


def _ollama_response(content: str) -> dict:
    return {"message": {"content": content}}


class TestChatCompletionOllamaPrimary:
    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_ollama_content(self):
        respx.post(OLLAMA_URL).mock(
            return_value=httpx.Response(200, json=_ollama_response(MOCK_REPLY))
        )
        result = await llm_service.chat_completion(
            [{"role": "user", "content": "test"}],
            inject_system=False,
        )
        assert result == MOCK_REPLY

    @pytest.mark.asyncio
    @respx.mock
    async def test_system_prompt_injected_by_default(self):
        captured = {}

        async def capture_request(request, route):
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_ollama_response("ok"))

        respx.post(OLLAMA_URL).mock(side_effect=capture_request)
        await llm_service.chat_completion([{"role": "user", "content": "hi"}])
        messages = captured["body"]["messages"]
        assert messages[0]["role"] == "system"
        assert "Dutch" in messages[0]["content"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_system_when_inject_system_false(self):
        captured = {}

        async def capture_request(request, route):
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_ollama_response("ok"))

        respx.post(OLLAMA_URL).mock(side_effect=capture_request)
        await llm_service.chat_completion(
            [{"role": "user", "content": "hi"}], inject_system=False
        )
        messages = captured["body"]["messages"]
        assert messages[0]["role"] == "user"


class TestChatCompletionFallback:
    @pytest.mark.asyncio
    @respx.mock
    async def test_falls_back_to_gemini_when_ollama_fails(self):
        respx.post(OLLAMA_URL).mock(side_effect=httpx.ConnectError("connection refused"))

        with patch("app.services.llm_service._call_gemini", new_callable=AsyncMock) as mock_gemini:
            mock_gemini.return_value = "fallback response"
            result = await llm_service.chat_completion(
                [{"role": "user", "content": "test"}],
                inject_system=False,
            )
            assert result == "fallback response"
            mock_gemini.assert_called_once()

    @pytest.mark.asyncio
    @respx.mock
    async def test_raises_when_both_providers_fail(self):
        respx.post(OLLAMA_URL).mock(side_effect=httpx.ConnectError("connection refused"))

        with patch("app.services.llm_service._call_gemini", new_callable=AsyncMock) as mock_gemini:
            mock_gemini.side_effect = RuntimeError("no API key")
            with pytest.raises(RuntimeError, match="All LLM providers failed"):
                await llm_service.chat_completion(
                    [{"role": "user", "content": "test"}],
                    inject_system=False,
                )


class TestHelpers:
    @pytest.mark.asyncio
    @respx.mock
    async def test_explain_builds_correct_prompt(self):
        captured = {}

        async def capture(request, route):
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_ollama_response("explanation"))

        respx.post(OLLAMA_URL).mock(side_effect=capture)
        await llm_service.explain("hond", context_sentence="De hond rent.")
        user_msg = next(m for m in captured["body"]["messages"] if m["role"] == "user")
        assert "hond" in user_msg["content"]
        assert "De hond rent." in user_msg["content"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_feedback_includes_all_components(self):
        captured = {}

        async def capture(request, route):
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=_ollama_response("feedback"))

        respx.post(OLLAMA_URL).mock(side_effect=capture)
        await llm_service.feedback(
            question="¿Cómo se dice perro?",
            correct_answer="hond",
            user_answer="kat",
        )
        user_msg = next(m for m in captured["body"]["messages"] if m["role"] == "user")
        assert "hond" in user_msg["content"]
        assert "kat" in user_msg["content"]
