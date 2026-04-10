"""Unit tests for content_generator JSON parsing helpers and metadata."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from app.services.content_generator import (
    LEVEL_DESCRIPTIONS,
    THEMES_BY_LEVEL,
    _parse_json_list,
    _parse_json_object,
)


class TestParseJsonList:
    def test_plain_json_array(self):
        raw = '[{"dutch_word": "hond", "spanish": "perro"}]'
        result = _parse_json_list(raw)
        assert result == [{"dutch_word": "hond", "spanish": "perro"}]

    def test_markdown_fenced_json(self):
        raw = "```json\n[{\"dutch_word\": \"kat\"}]\n```"
        result = _parse_json_list(raw)
        assert result == [{"dutch_word": "kat"}]

    def test_wrapped_in_object(self):
        raw = '{"items": [{"dutch_word": "vis"}]}'
        result = _parse_json_list(raw)
        assert result == [{"dutch_word": "vis"}]

    def test_json_embedded_in_prose(self):
        raw = 'Here are the words:\n[{"dutch_word": "boom"}]\nDone.'
        result = _parse_json_list(raw)
        assert result == [{"dutch_word": "boom"}]

    def test_completely_invalid_returns_empty_list(self):
        result = _parse_json_list("I cannot generate that right now.")
        assert result == []

    def test_empty_string_returns_empty_list(self):
        assert _parse_json_list("") == []

    def test_multiple_items(self):
        raw = '[{"a": 1}, {"a": 2}, {"a": 3}]'
        result = _parse_json_list(raw)
        assert len(result) == 3


class TestParseJsonObject:
    def test_plain_json_object(self):
        raw = '{"slug": "comparativos", "level": "a1"}'
        result = _parse_json_object(raw)
        assert result["slug"] == "comparativos"
        assert result["level"] == "a1"

    def test_markdown_fenced_object(self):
        raw = "```json\n{\"slug\": \"articles\"}\n```"
        result = _parse_json_object(raw)
        assert result == {"slug": "articles"}

    def test_embedded_in_prose(self):
        raw = 'Here is the grammar topic:\n{"slug": "de-het"}\nEnjoy!'
        result = _parse_json_object(raw)
        assert result == {"slug": "de-het"}

    def test_completely_invalid_returns_empty_dict(self):
        result = _parse_json_object("Sorry, I cannot help with that.")
        assert result == {}

    def test_empty_string_returns_empty_dict(self):
        assert _parse_json_object("") == {}

    def test_nested_objects(self):
        raw = '{"examples": [{"nl": "de hond", "es": "el perro"}]}'
        result = _parse_json_object(raw)
        assert result["examples"][0]["nl"] == "de hond"


class TestLevelMetadata:
    def test_all_levels_have_descriptions(self):
        expected = {"a0", "a1", "a2", "b1", "b2", "c1"}
        assert set(LEVEL_DESCRIPTIONS.keys()) == expected

    def test_all_levels_have_themes(self):
        expected = {"a0", "a1", "a2", "b1", "b2", "c1"}
        assert set(THEMES_BY_LEVEL.keys()) == expected

    def test_each_level_has_at_least_three_themes(self):
        for level, themes in THEMES_BY_LEVEL.items():
            assert len(themes) >= 3, f"Level {level} has too few themes"

    def test_descriptions_are_non_empty_strings(self):
        for level, desc in LEVEL_DESCRIPTIONS.items():
            assert isinstance(desc, str) and len(desc) > 0, f"Empty description for {level}"
