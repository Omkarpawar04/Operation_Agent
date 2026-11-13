"""Unit tests for _clean_gemini_schema in the Gemini adapter.

Gemini's response_schema field accepts only a subset of OpenAPI 3.0 keywords.
These tests verify that the cleaner strips all rejected keywords and resolves
$ref references inline without mutating the original schema.
"""
from __future__ import annotations

import copy

from app.adapters.llm.gemini import _clean_gemini_schema
from app.ports.llm import AnswerAnalysis, GeneratedQuestion

_REJECTED_KEYS = {"additionalProperties", "$schema", "title", "$defs", "$ref", "default"}


def _all_keys_recursive(obj: object) -> set[str]:
    """Return every dict key found anywhere in a nested structure."""
    keys: set[str] = set()
    if isinstance(obj, dict):
        keys.update(obj.keys())
        for v in obj.values():
            keys.update(_all_keys_recursive(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(_all_keys_recursive(item))
    return keys


class TestCleanGeminiSchema:
    def test_strips_additional_properties(self) -> None:
        raw: dict = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "additionalProperties": False,
        }
        cleaned = _clean_gemini_schema(raw)
        assert "additionalProperties" not in cleaned

    def test_strips_title(self) -> None:
        raw = {"title": "MyModel", "type": "object", "properties": {}}
        cleaned = _clean_gemini_schema(raw)
        assert "title" not in cleaned

    def test_strips_schema_meta(self) -> None:
        raw: dict = {
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "object",
            "properties": {},
        }
        cleaned = _clean_gemini_schema(raw)
        assert "$schema" not in cleaned

    def test_strips_default(self) -> None:
        raw = {"type": "string", "default": "hello"}
        cleaned = _clean_gemini_schema(raw)
        assert "default" not in cleaned

    def test_resolves_ref_in_properties(self) -> None:
        raw = {
            "type": "object",
            "$defs": {
                "Inner": {"type": "object", "properties": {"val": {"type": "integer"}}}
            },
            "properties": {
                "inner": {"$ref": "#/$defs/Inner"},
            },
        }
        cleaned = _clean_gemini_schema(raw)
        assert "$defs" not in cleaned
        assert "$ref" not in _all_keys_recursive(cleaned)
        assert cleaned["properties"]["inner"]["properties"]["val"]["type"] == "integer"

    def test_resolves_ref_in_array_items(self) -> None:
        raw = {
            "type": "object",
            "$defs": {
                "Item": {"type": "object", "properties": {"name": {"type": "string"}}}
            },
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Item"},
                }
            },
        }
        cleaned = _clean_gemini_schema(raw)
        assert "$ref" not in _all_keys_recursive(cleaned)
        assert (
            cleaned["properties"]["items"]["items"]["properties"]["name"]["type"] == "string"
        )

    def test_preserves_plain_types(self) -> None:
        raw = {"type": "object", "properties": {"age": {"type": "integer", "minimum": 0}}}
        cleaned = _clean_gemini_schema(raw)
        assert cleaned["properties"]["age"]["type"] == "integer"
        assert cleaned["properties"]["age"]["minimum"] == 0

    def test_does_not_mutate_original(self) -> None:
        raw: dict = {"type": "object", "additionalProperties": False, "properties": {}}
        original = copy.deepcopy(raw)
        _clean_gemini_schema(raw)
        assert raw == original

    def test_generated_question_schema_has_no_rejected_keys(self) -> None:
        schema = GeneratedQuestion.model_json_schema()
        cleaned = _clean_gemini_schema(schema)
        found = _all_keys_recursive(cleaned) & _REJECTED_KEYS
        assert not found, f"Rejected keys still present: {found}"

    def test_answer_analysis_schema_has_no_rejected_keys(self) -> None:
        schema = AnswerAnalysis.model_json_schema()
        cleaned = _clean_gemini_schema(schema)
        found = _all_keys_recursive(cleaned) & _REJECTED_KEYS
        assert not found, f"Rejected keys still present: {found}"

    def test_answer_analysis_schema_preserves_findings_structure(self) -> None:
        schema = AnswerAnalysis.model_json_schema()
        cleaned = _clean_gemini_schema(schema)
        # findings should be an array with item properties intact
        findings_schema = cleaned["properties"]["findings"]
        assert findings_schema["type"] == "array"
        item_props = findings_schema["items"]["properties"]
        assert "dimension_key" in item_props
        assert "relevance" in item_props
